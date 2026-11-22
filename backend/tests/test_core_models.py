from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import UniqueConstraint, create_engine, event, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import (
    AllergyIntolerance,
    Appointment,
    Condition,
    Encounter,
    Hospital,
    HospitalUser,
    MedicationStatement,
    MedicineCatalogueItem,
    Observation,
    Patient,
    PatientIdentifier,
    PatientMatchCandidate,
    ProvenanceRecord,
    User,
)


@pytest.fixture
def engine():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as db:
        yield db


def make_hospital(code: str) -> Hospital:
    return Hospital(name=f"Hospital {code}", code=code)


def make_user(display_name: str) -> User:
    return User(display_name=display_name, status="active")


def make_patient(hospital: Hospital, mrn: str) -> Patient:
    return Patient(
        hospital=hospital,
        synthetic_mrn=mrn,
        given_name="Synthetic",
        family_name="Patient",
        date_of_birth=date(2000, 1, 1),
        identity_status="unverified",
    )


def make_hospital_user(
    hospital: Hospital,
    user: User,
    role_code: str = "doctor",
) -> HospitalUser:
    return HospitalUser(
        hospital=hospital,
        user=user,
        role_code=role_code,
        relationship_scope="hospital",
        status="active",
        valid_from=datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc),
    )


def make_provenance(
    hospital: Hospital,
    patient: Patient | None = None,
) -> ProvenanceRecord:
    return ProvenanceRecord(
        hospital=hospital,
        patient=patient,
        source_type="doctor_entry",
        recorded_at=datetime.now(timezone.utc),
        verification_status="reviewed",
        uncertainty="unknown",
    )


def make_typed_fact(
    model,
    hospital: Hospital,
    patient: Patient,
    provenance: ProvenanceRecord,
    encounter: Encounter | None = None,
):
    values = {
        "hospital": hospital,
        "patient": patient,
        "provenance": provenance,
    }
    if encounter is not None:
        values["encounter"] = encounter
    if model is Condition:
        values.update(
            display_name="Synthetic condition",
            status="active",
            verification_status="verified",
        )
    elif model is AllergyIntolerance:
        values.update(
            substance="Synthetic substance",
            criticality="unknown",
            status="active",
            verification_status="verified",
        )
    elif model is Observation:
        values.update(
            observation_type="laboratory",
            value_text="normal",
        )
    elif model is MedicationStatement:
        values.update(
            medicine_name="Synthetic medicine",
            statement_type="patient_reported",
            status="active",
            verification_status="unverified",
        )
    return model(**values)


def test_models_are_registered_with_metadata():
    assert {
        "hospitals",
        "users",
        "hospital_users",
        "patients",
        "patient_identifiers",
        "patient_match_candidates",
        "appointments",
        "encounters",
        "provenance_records",
        "conditions",
        "allergy_intolerances",
        "observations",
        "medication_statements",
    }.issubset(Base.metadata.tables)

    assert Base.metadata.tables["hospitals"].fullname == "hospitals"
    assert Base.metadata.tables["users"].fullname == "users"
    assert Base.metadata.tables["hospital_users"].fullname == "hospital_users"
    assert Base.metadata.tables["patients"].fullname == "patients"
    assert (
        Base.metadata.tables["patient_identifiers"].fullname
        == "patient_identifiers"
    )
    assert (
        Base.metadata.tables["patient_match_candidates"].fullname
        == "patient_match_candidates"
    )


def test_typed_models_are_registered_with_metadata():
    assert {
        "conditions",
        "allergy_intolerances",
        "observations",
        "medication_statements",
    }.issubset(Base.metadata.tables)


def test_condition_creation_and_same_patient_supersession(session):
    hospital = make_hospital("T1")
    patient = make_patient(hospital, "MRN-T1-001")
    first_provenance = make_provenance(hospital, patient)
    second_provenance = make_provenance(hospital, patient)
    target = make_typed_fact(Condition, hospital, patient, first_provenance)
    session.add(target)
    session.flush()
    source = make_typed_fact(Condition, hospital, patient, second_provenance)
    source.superseded_by = target
    session.add(source)
    session.commit()
    session.expire_all()

    persisted = session.get(Condition, source.id)
    assert persisted is not None
    assert persisted.superseded_by is target
    assert persisted.patient is patient
    assert persisted.provenance is second_provenance
    session.delete(source)
    session.delete(target)
    session.commit()


def test_allergy_intolerance_creation_and_criticality_constraint(session):
    hospital = make_hospital("T2")
    patient = make_patient(hospital, "MRN-T2-001")
    provenance = make_provenance(hospital, patient)
    row = make_typed_fact(
        AllergyIntolerance,
        hospital,
        patient,
        provenance,
    )
    row.substance = "Synthetic substance"
    row.reaction = "Synthetic reaction"
    session.add(row)
    session.commit()
    session.expire_all()

    persisted = session.get(AllergyIntolerance, row.id)
    assert persisted is not None
    assert persisted.patient is patient
    assert persisted.provenance is provenance


def test_allergy_intolerance_rejects_unsupported_criticality(session):
    hospital = make_hospital("T3")
    patient = make_patient(hospital, "MRN-T3-001")
    provenance = make_provenance(hospital, patient)
    row = make_typed_fact(AllergyIntolerance, hospital, patient, provenance)
    row.criticality = "critical"
    session.add(row)

    with pytest.raises(IntegrityError):
        session.commit()


def test_observation_requires_text_or_numeric_value(session):
    hospital = make_hospital("T4")
    patient = make_patient(hospital, "MRN-T4-001")
    provenance = make_provenance(hospital, patient)
    row = make_typed_fact(Observation, hospital, patient, provenance)
    row.value_text = None
    session.add(row)

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize(
    "value_field",
    ["value_text", "value_numeric"],
)
def test_observation_accepts_text_or_numeric_value(session, value_field):
    hospital = make_hospital(f"T5-{value_field}")
    patient = make_patient(hospital, f"MRN-T5-{value_field}")
    provenance = make_provenance(hospital, patient)
    row = make_typed_fact(Observation, hospital, patient, provenance)
    setattr(row, value_field, "12.5" if value_field == "value_numeric" else "normal")
    session.add(row)
    session.commit()

    assert session.get(Observation, row.id) is not None


def test_medication_statement_creation_and_nullable_catalogue_reference(session):
    hospital = make_hospital("T6")
    patient = make_patient(hospital, "MRN-T6-001")
    provenance = make_provenance(hospital, patient)
    catalogue_item = MedicineCatalogueItem(
        catalogue_name="Synthetic Academic Catalogue",
        catalogue_version="2026.11",
        generic_name="Synthetic medicine",
        source_name="Synthetic source",
    )
    session.add(catalogue_item)
    session.flush()
    row = make_typed_fact(MedicationStatement, hospital, patient, provenance)
    row.catalogue_item_id = catalogue_item.id
    session.add(row)
    session.commit()
    session.expire_all()

    persisted = session.get(MedicationStatement, row.id)
    assert persisted is not None
    assert persisted.catalogue_item_id is not None
    assert persisted.patient is patient
    assert persisted.provenance is provenance


def test_medication_statement_rejects_invalid_date_order(session):
    hospital = make_hospital("T7")
    patient = make_patient(hospital, "MRN-T7-001")
    provenance = make_provenance(hospital, patient)
    row = make_typed_fact(MedicationStatement, hospital, patient, provenance)
    row.start_at = datetime(2026, 11, 18, tzinfo=timezone.utc)
    row.end_at = datetime(2026, 11, 17, tzinfo=timezone.utc)
    session.add(row)

    with pytest.raises(IntegrityError):
        session.commit()


def test_medication_statement_same_patient_supersession(session):
    hospital = make_hospital("T8")
    patient = make_patient(hospital, "MRN-T8-001")
    first_provenance = make_provenance(hospital, patient)
    second_provenance = make_provenance(hospital, patient)
    target = make_typed_fact(
        MedicationStatement,
        hospital,
        patient,
        first_provenance,
    )
    session.add(target)
    session.flush()
    source = make_typed_fact(
        MedicationStatement,
        hospital,
        patient,
        second_provenance,
    )
    source.superseded_by = target
    session.add(source)
    session.commit()

    assert session.get(MedicationStatement, source.id).superseded_by is target
    session.delete(source)
    session.delete(target)
    session.commit()


@pytest.mark.parametrize(
    "model",
    [Condition, AllergyIntolerance, Observation, MedicationStatement],
)
def test_typed_models_reject_cross_hospital_patient(session, model):
    first_hospital = make_hospital(f"T9-{model.__name__}-A")
    second_hospital = make_hospital(f"T9-{model.__name__}-B")
    first_patient = make_patient(first_hospital, f"MRN-T9-{model.__name__}-A")
    second_patient = make_patient(second_hospital, f"MRN-T9-{model.__name__}-B")
    provenance = make_provenance(second_hospital, second_patient)
    session.add(first_patient)
    session.flush()
    row = make_typed_fact(
        model,
        second_hospital,
        first_patient,
        provenance,
    )
    session.add(row)

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize(
    "model",
    [Condition, AllergyIntolerance, Observation, MedicationStatement],
)
def test_typed_models_reject_cross_hospital_encounter(session, model):
    first_hospital = make_hospital(f"T10-{model.__name__}-A")
    second_hospital = make_hospital(f"T10-{model.__name__}-B")
    first_patient = make_patient(first_hospital, f"MRN-T10-{model.__name__}-A")
    second_patient = make_patient(second_hospital, f"MRN-T10-{model.__name__}-B")
    doctor = make_hospital_user(first_hospital, make_user(f"Doctor T10 {model.__name__}"))
    encounter = Encounter(
        hospital=first_hospital,
        patient=first_patient,
        doctor_hospital_user=doctor,
    )
    provenance = make_provenance(second_hospital, second_patient)
    session.add(encounter)
    session.flush()
    row = make_typed_fact(
        model,
        second_hospital,
        second_patient,
        provenance,
    )
    row.encounter_id = encounter.id
    session.add(row)

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize(
    "model",
    [Condition, AllergyIntolerance, Observation, MedicationStatement],
)
def test_typed_models_reject_cross_patient_encounter(session, model):
    hospital = make_hospital(f"T11-{model.__name__}")
    encounter_patient = make_patient(hospital, f"MRN-T11-{model.__name__}-A")
    other_patient = make_patient(hospital, f"MRN-T11-{model.__name__}-B")
    doctor = make_hospital_user(hospital, make_user(f"Doctor T11 {model.__name__}"))
    encounter = Encounter(
        hospital=hospital,
        patient=encounter_patient,
        doctor_hospital_user=doctor,
    )
    provenance = make_provenance(hospital, other_patient)
    session.add(encounter)
    session.flush()
    row = make_typed_fact(model, hospital, other_patient, provenance)
    row.encounter_id = encounter.id
    session.add(row)

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize(
    "model",
    [Condition, AllergyIntolerance, Observation, MedicationStatement],
)
def test_typed_models_reject_cross_hospital_provenance(session, model):
    first_hospital = make_hospital(f"T12-{model.__name__}-A")
    second_hospital = make_hospital(f"T12-{model.__name__}-B")
    first_patient = make_patient(first_hospital, f"MRN-T12-{model.__name__}-A")
    second_patient = make_patient(second_hospital, f"MRN-T12-{model.__name__}-B")
    provenance = make_provenance(first_hospital, first_patient)
    session.add(provenance)
    session.flush()
    row = make_typed_fact(
        model,
        second_hospital,
        second_patient,
        provenance,
    )
    session.add(row)

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize(
    "model",
    [Condition, AllergyIntolerance, Observation, MedicationStatement],
)
def test_typed_models_reject_provenance_patient_mismatch(session, model):
    hospital = make_hospital(f"T13-{model.__name__}")
    first_patient = make_patient(hospital, f"MRN-T13-{model.__name__}-A")
    second_patient = make_patient(hospital, f"MRN-T13-{model.__name__}-B")
    provenance = make_provenance(hospital, first_patient)
    session.add(provenance)
    session.flush()
    row = make_typed_fact(model, hospital, second_patient, provenance)
    session.add(row)

    with pytest.raises(IntegrityError):
        session.commit()


def test_typed_models_load_all_relationships(session):
    hospital = make_hospital("T14")
    patient = make_patient(hospital, "MRN-T14-001")
    doctor = make_hospital_user(hospital, make_user("Doctor T14"))
    encounter = Encounter(
        hospital=hospital,
        patient=patient,
        doctor_hospital_user=doctor,
    )
    provenance = make_provenance(hospital, patient)
    condition = make_typed_fact(
        Condition,
        hospital,
        patient,
        provenance,
        encounter,
    )
    allergy = make_typed_fact(
        AllergyIntolerance,
        hospital,
        patient,
        provenance,
        encounter,
    )
    observation = make_typed_fact(
        Observation,
        hospital,
        patient,
        provenance,
        encounter,
    )
    observation.value_text = "normal"
    medication = make_typed_fact(
        MedicationStatement,
        hospital,
        patient,
        provenance,
        encounter,
    )
    session.add_all([condition, allergy, observation, medication])
    session.commit()
    session.expire_all()

    assert session.get(Condition, condition.id).encounter is encounter
    assert session.get(AllergyIntolerance, allergy.id).provenance is provenance
    assert session.get(Observation, observation.id).patient is patient
    assert session.get(MedicationStatement, medication.id).encounter is encounter


def test_appointment_creation_and_relationship_loading(session):
    hospital = make_hospital("H18")
    patient = make_patient(hospital, "MRN-H18-001")
    doctor = make_hospital_user(hospital, make_user("Doctor H18"))
    appointment = Appointment(
        hospital=hospital,
        patient=patient,
        doctor_hospital_user=doctor,
        scheduled_at=datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc),
        status="scheduled",
    )
    session.add(appointment)
    session.commit()
    session.expire_all()

    persisted = session.get(Appointment, appointment.id)
    assert persisted is not None
    assert persisted.hospital is hospital
    assert persisted.patient is patient
    assert persisted.doctor_hospital_user is doctor
    assert appointment in hospital.appointments


def test_provenance_record_supports_nullable_sources_and_polymorphic_reference(
    session,
):
    hospital = make_hospital("P1")
    record = ProvenanceRecord(
        hospital=hospital,
        source_type="import",
        source_record_id=uuid4(),
        recorded_at=datetime.now(timezone.utc),
        verification_status="unverified",
        uncertainty="unknown",
    )
    session.add(record)
    session.commit()
    session.expire_all()

    persisted = session.get(ProvenanceRecord, record.id)
    assert persisted is not None
    assert persisted.patient is None
    assert persisted.encounter is None
    assert persisted.author_hospital_user is None
    assert persisted.source_record_id is not None
    assert record in hospital.provenance_records


def test_provenance_record_loads_patient_and_encounter_relationships(session):
    hospital = make_hospital("P2")
    patient = make_patient(hospital, "MRN-P2-001")
    doctor = make_hospital_user(hospital, make_user("Doctor P2"))
    appointment = Appointment(
        hospital=hospital,
        patient=patient,
        doctor_hospital_user=doctor,
        scheduled_at=datetime.now(timezone.utc),
    )
    encounter = Encounter(
        hospital=hospital,
        patient=patient,
        appointment=appointment,
        doctor_hospital_user=doctor,
        status="completed",
    )
    record = ProvenanceRecord(
        hospital=hospital,
        patient=patient,
        encounter=encounter,
        author_hospital_user=doctor,
        source_type="conversation",
        recorded_at=datetime.now(timezone.utc),
        verification_status="reviewed",
        uncertainty="low",
        confidence=Decimal("0.8750"),
    )
    session.add(record)
    session.commit()
    session.expire_all()

    persisted = session.get(ProvenanceRecord, record.id)
    assert persisted is not None
    assert persisted.patient is patient
    assert persisted.encounter is encounter
    assert persisted.author_hospital_user is doctor
    assert record in patient.provenance_records
    assert record in encounter.provenance_records
    assert record in doctor.provenance_records


def test_provenance_record_rejects_encounter_without_patient(session):
    hospital = make_hospital("P2A")
    patient = make_patient(hospital, "MRN-P2A-001")
    doctor = make_hospital_user(hospital, make_user("Doctor P2A"))
    encounter = Encounter(
        hospital=hospital,
        patient=patient,
        doctor_hospital_user=doctor,
    )
    session.add(encounter)
    session.flush()
    session.add(
        ProvenanceRecord(
            hospital=hospital,
            encounter_id=encounter.id,
            source_type="conversation",
            recorded_at=datetime.now(timezone.utc),
            verification_status="unverified",
            uncertainty="unknown",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_provenance_record_rejects_cross_hospital_patient(session):
    first_hospital = make_hospital("P3")
    second_hospital = make_hospital("P4")
    patient = make_patient(first_hospital, "MRN-P3-001")
    session.add(patient)
    session.flush()
    session.add(
        ProvenanceRecord(
            hospital=second_hospital,
            patient_id=patient.id,
            source_type="doctor_entry",
            recorded_at=datetime.now(timezone.utc),
            verification_status="verified",
            uncertainty="none",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_provenance_record_rejects_cross_hospital_encounter(session):
    first_hospital = make_hospital("P5")
    second_hospital = make_hospital("P6")
    patient = make_patient(first_hospital, "MRN-P5-001")
    doctor = make_hospital_user(first_hospital, make_user("Doctor P5"))
    appointment = Appointment(
        hospital=first_hospital,
        patient=patient,
        doctor_hospital_user=doctor,
        scheduled_at=datetime.now(timezone.utc),
    )
    encounter = Encounter(
        hospital=first_hospital,
        patient=patient,
        appointment=appointment,
        doctor_hospital_user=doctor,
    )
    session.add(encounter)
    session.flush()
    session.add(
        ProvenanceRecord(
            hospital=second_hospital,
            encounter_id=encounter.id,
            source_type="conversation",
            recorded_at=datetime.now(timezone.utc),
            verification_status="unverified",
            uncertainty="unknown",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_provenance_record_rejects_encounter_patient_mismatch(session):
    hospital = make_hospital("P7")
    encounter_patient = make_patient(hospital, "MRN-P7-001")
    other_patient = make_patient(hospital, "MRN-P7-002")
    doctor = make_hospital_user(hospital, make_user("Doctor P7"))
    encounter = Encounter(
        hospital=hospital,
        patient=encounter_patient,
        doctor_hospital_user=doctor,
    )
    session.add(encounter)
    session.flush()
    session.add(
        ProvenanceRecord(
            hospital=hospital,
            patient=other_patient,
            encounter_id=encounter.id,
            source_type="conversation",
            recorded_at=datetime.now(timezone.utc),
            verification_status="unverified",
            uncertainty="unknown",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_provenance_record_rejects_cross_hospital_author(session):
    first_hospital = make_hospital("P8")
    second_hospital = make_hospital("P9")
    author = make_hospital_user(second_hospital, make_user("Doctor P9"))
    session.add(author)
    session.flush()
    session.add(
        ProvenanceRecord(
            hospital=first_hospital,
            author_hospital_user_id=author.id,
            source_type="doctor_entry",
            recorded_at=datetime.now(timezone.utc),
            verification_status="reviewed",
            uncertainty="unknown",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_type", "invalid"),
        ("verification_status", "invalid"),
        ("uncertainty", None),
        ("confidence", Decimal("-0.0001")),
        ("confidence", Decimal("1.0001")),
    ],
)
def test_provenance_record_rejects_invalid_control_values(
    session,
    field,
    value,
):
    hospital = make_hospital(f"P-{field}-{value}")
    values = {
        "hospital": hospital,
        "source_type": "document",
        "recorded_at": datetime.now(timezone.utc),
        "verification_status": "unverified",
        "uncertainty": "unknown",
    }
    values[field] = value
    session.add(ProvenanceRecord(**values))

    with pytest.raises(IntegrityError):
        session.commit()


def test_appointment_rejects_patient_from_another_hospital(session):
    first_hospital = make_hospital("H19")
    second_hospital = make_hospital("H20")
    patient = make_patient(first_hospital, "MRN-H19-001")
    doctor = make_hospital_user(second_hospital, make_user("Doctor H20"))
    session.add(
        Appointment(
            hospital=second_hospital,
            patient_id=patient.id,
            doctor_hospital_user=doctor,
            scheduled_at=datetime.now(timezone.utc),
            status="scheduled",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_appointment_rejects_doctor_from_another_hospital(session):
    first_hospital = make_hospital("H21")
    second_hospital = make_hospital("H22")
    patient = make_patient(first_hospital, "MRN-H21-001")
    doctor = make_hospital_user(second_hospital, make_user("Doctor H22"))
    session.add(
        Appointment(
            hospital=first_hospital,
            patient=patient,
            doctor_hospital_user_id=doctor.id,
            scheduled_at=datetime.now(timezone.utc),
            status="scheduled",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_encounter_without_appointment_and_with_same_patient_appointment(
    session,
):
    hospital = make_hospital("H23")
    patient = make_patient(hospital, "MRN-H23-001")
    doctor = make_hospital_user(hospital, make_user("Doctor H23"))
    appointment = Appointment(
        hospital=hospital,
        patient=patient,
        doctor_hospital_user=doctor,
        scheduled_at=datetime(2026, 12, 2, 10, 0, tzinfo=timezone.utc),
    )
    standalone = Encounter(
        hospital=hospital,
        patient=patient,
        doctor_hospital_user=doctor,
        status="planned",
    )
    linked = Encounter(
        hospital=hospital,
        patient=patient,
        doctor_hospital_user=doctor,
        appointment=appointment,
        status="in_progress",
    )
    session.add_all([standalone, linked])
    session.commit()
    session.expire_all()

    persisted = session.get(Encounter, linked.id)
    assert persisted is not None
    assert persisted.appointment is appointment
    assert persisted.patient is patient
    assert standalone.appointment is None
    assert linked in hospital.encounters
    assert linked in patient.encounters
    assert linked in doctor.encounters


def test_appointment_allows_only_one_linked_encounter(session):
    hospital = make_hospital("H30")
    patient = make_patient(hospital, "MRN-H30-001")
    doctor = make_hospital_user(hospital, make_user("Doctor H30"))
    appointment = Appointment(
        hospital=hospital,
        patient=patient,
        doctor_hospital_user=doctor,
        scheduled_at=datetime(2026, 12, 4, 10, 0, tzinfo=timezone.utc),
    )
    session.add(appointment)
    session.flush()

    first_encounter = Encounter(
        hospital=hospital,
        patient=patient,
        appointment=appointment,
        doctor_hospital_user=doctor,
        status="completed",
    )
    session.add(first_encounter)
    session.commit()

    second_encounter = Encounter(
        hospital=hospital,
        patient=patient,
        appointment=appointment,
        doctor_hospital_user=doctor,
        status="planned",
    )
    session.add(second_encounter)

    with pytest.raises(IntegrityError):
        session.commit()


def test_encounter_rejects_cross_hospital_appointment(session):
    first_hospital = make_hospital("H24")
    second_hospital = make_hospital("H25")
    first_patient = make_patient(first_hospital, "MRN-H24-001")
    second_patient = make_patient(second_hospital, "MRN-H25-001")
    first_doctor = make_hospital_user(first_hospital, make_user("Doctor H24"))
    second_doctor = make_hospital_user(second_hospital, make_user("Doctor H25"))
    appointment = Appointment(
        hospital=first_hospital,
        patient=first_patient,
        doctor_hospital_user=first_doctor,
        scheduled_at=datetime.now(timezone.utc),
    )
    session.add(appointment)
    session.flush()
    session.add(
        Encounter(
            hospital=second_hospital,
            patient=second_patient,
            appointment_id=appointment.id,
            doctor_hospital_user=second_doctor,
            status="planned",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_encounter_rejects_appointment_patient_mismatch(session):
    hospital = make_hospital("H26")
    appointment_patient = make_patient(hospital, "MRN-H26-001")
    encounter_patient = make_patient(hospital, "MRN-H26-002")
    doctor = make_hospital_user(hospital, make_user("Doctor H26"))
    appointment = Appointment(
        hospital=hospital,
        patient=appointment_patient,
        doctor_hospital_user=doctor,
        scheduled_at=datetime.now(timezone.utc),
    )
    session.add(appointment)
    session.flush()
    session.add(
        Encounter(
            hospital=hospital,
            patient=encounter_patient,
            appointment_id=appointment.id,
            doctor_hospital_user=doctor,
            status="planned",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_encounter_rejects_invalid_doctor_assignment(session):
    first_hospital = make_hospital("H27")
    second_hospital = make_hospital("H28")
    patient = make_patient(first_hospital, "MRN-H27-001")
    doctor = make_hospital_user(second_hospital, make_user("Doctor H28"))
    session.add(
        Encounter(
            hospital=first_hospital,
            patient=patient,
            doctor_hospital_user_id=doctor.id,
            status="planned",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize(
    ("model", "status"),
    [(Appointment, "invalid"), (Encounter, "invalid")],
)
def test_scheduling_models_reject_invalid_status(session, model, status):
    hospital = make_hospital(f"H-{model.__name__}")
    patient = make_patient(hospital, f"MRN-{model.__name__}")
    doctor = make_hospital_user(hospital, make_user(f"Doctor {model.__name__}"))
    values = {
        "hospital": hospital,
        "patient": patient,
        "doctor_hospital_user": doctor,
        "status": status,
    }
    if model is Appointment:
        values["scheduled_at"] = datetime.now(timezone.utc)
    session.add(model(**values))

    with pytest.raises(IntegrityError):
        session.commit()


def test_encounter_rejects_invalid_time_order(session):
    hospital = make_hospital("H29")
    patient = make_patient(hospital, "MRN-H29-001")
    doctor = make_hospital_user(hospital, make_user("Doctor H29"))
    session.add(
        Encounter(
            hospital=hospital,
            patient=patient,
            doctor_hospital_user=doctor,
            started_at=datetime(2026, 12, 3, 11, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 12, 3, 10, 0, tzinfo=timezone.utc),
            status="completed",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_encounter_has_patient_scoped_unique_key():
    constraint_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in Encounter.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert ("hospital_id", "id", "patient_id") in constraint_columns
def test_primary_and_foreign_keys():
    hospital_mapper = inspect(Hospital)
    user_mapper = inspect(User)
    hospital_user_mapper = inspect(HospitalUser)
    patient_mapper = inspect(Patient)

    assert list(hospital_mapper.primary_key)[0].name == "id"
    assert list(user_mapper.primary_key)[0].name == "id"
    assert list(hospital_user_mapper.primary_key)[0].name == "id"
    assert list(patient_mapper.primary_key)[0].name == "id"

    hospital_user_fks = {
        (fk.parent.name, fk.column.table.name, fk.column.name)
        for fk in HospitalUser.__table__.foreign_keys
    }
    assert ("hospital_id", "hospitals", "id") in hospital_user_fks
    assert ("user_id", "users", "id") in hospital_user_fks

    patient_fks = {
        (fk.parent.name, fk.column.table.name, fk.column.name)
        for fk in Patient.__table__.foreign_keys
    }
    assert ("hospital_id", "hospitals", "id") in patient_fks


def test_hospital_membership_uniqueness(session):
    hospital = make_hospital("H1")
    user = make_user("Synthetic Doctor")
    session.add_all([hospital, user])
    session.flush()

    valid_from = datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc)
    membership = HospitalUser(
        hospital=hospital,
        user=user,
        role_code="doctor",
        relationship_scope="hospital",
        status="active",
        valid_from=valid_from,
    )
    session.add(membership)
    session.commit()

    duplicate = HospitalUser(
        hospital_id=hospital.id,
        user_id=user.id,
        role_code="doctor",
        relationship_scope="hospital",
        status="active",
        valid_from=valid_from,
    )
    session.add(duplicate)

    with pytest.raises(IntegrityError):
        session.commit()


def test_patient_belongs_to_hospital(session):
    hospital = make_hospital("H2")
    session.add(hospital)
    session.flush()

    patient = make_patient(hospital, "MRN-H2-001")
    session.add(patient)
    session.commit()
    session.refresh(patient)

    assert patient.hospital_id == hospital.id
    assert patient in hospital.patients


def test_duplicate_mrn_is_rejected_within_hospital(session):
    hospital = make_hospital("H3")
    session.add(hospital)
    session.flush()

    session.add_all(
        [
            make_patient(hospital, "MRN-H3-001"),
            make_patient(hospital, "MRN-H3-001"),
        ]
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_patient_can_merge_into_same_hospital_patient(session):
    hospital = make_hospital("H4")
    session.add(hospital)
    session.flush()

    source = make_patient(hospital, "MRN-H4-001")
    target = make_patient(hospital, "MRN-H4-002")
    session.add_all([source, target])
    session.flush()

    source.merged_into = target
    session.commit()
    session.expire_all()

    persisted_source = session.get(Patient, source.id)
    persisted_target = session.get(Patient, target.id)

    assert persisted_source is not None
    assert persisted_target is not None
    assert persisted_source.merged_into is persisted_target


def test_patient_merge_cannot_cross_hospitals(session):
    first_hospital = make_hospital("H4")
    second_hospital = make_hospital("H5")
    session.add_all([first_hospital, second_hospital])
    session.flush()

    source = make_patient(first_hospital, "MRN-H4-001")
    target = make_patient(second_hospital, "MRN-H5-001")
    session.add_all([source, target])
    session.flush()

    source.merged_into_patient_id = target.id

    with pytest.raises(IntegrityError):
        session.commit()


def test_patient_target_delete_is_restricted_when_merge_reference_exists(session):
    hospital = make_hospital("H6")
    session.add(hospital)
    session.flush()

    source = make_patient(hospital, "MRN-H6-001")
    target = make_patient(hospital, "MRN-H6-002")
    session.add_all([source, target])
    session.flush()

    source.merged_into = target
    session.commit()

    session.delete(target)

    with pytest.raises(IntegrityError):
        session.commit()


def test_patient_identifier_creation_and_relationship_loading(session):
    hospital = make_hospital("H7")
    patient = make_patient(hospital, "MRN-H7-001")
    identifier = PatientIdentifier(
        hospital=hospital,
        patient=patient,
        identifier_type="academic_id",
        identifier_value="A-001",
        verification_status="verified",
    )
    session.add(identifier)
    session.commit()
    session.expire_all()

    persisted = session.get(PatientIdentifier, identifier.id)
    assert persisted is not None
    assert persisted.patient is patient
    assert persisted.hospital is hospital
    assert identifier in patient.identifiers


def test_duplicate_patient_identifier_is_rejected_within_hospital(session):
    hospital = make_hospital("H8")
    first = make_patient(hospital, "MRN-H8-001")
    second = make_patient(hospital, "MRN-H8-002")
    session.add(
        PatientIdentifier(
            hospital=hospital,
            patient=first,
            identifier_type="academic_id",
            identifier_value="A-001",
        )
    )
    session.flush()
    session.add(
        PatientIdentifier(
            hospital=hospital,
            patient=second,
            identifier_type="academic_id",
            identifier_value="A-001",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_same_patient_identifier_is_allowed_in_different_hospitals(session):
    first_hospital = make_hospital("H9")
    second_hospital = make_hospital("H10")
    first = make_patient(first_hospital, "MRN-H9-001")
    second = make_patient(second_hospital, "MRN-H10-001")
    session.add_all(
        [
            PatientIdentifier(
                hospital=first_hospital,
                patient=first,
                identifier_type="academic_id",
                identifier_value="A-001",
            ),
            PatientIdentifier(
                hospital=second_hospital,
                patient=second,
                identifier_type="academic_id",
                identifier_value="A-001",
            ),
        ]
    )

    session.commit()
    assert len(first.identifiers) == 1
    assert len(second.identifiers) == 1


def test_patient_identifier_rejects_invalid_hospital_association(session):
    first_hospital = make_hospital("H11")
    second_hospital = make_hospital("H12")
    patient = make_patient(first_hospital, "MRN-H11-001")
    session.add(patient)
    session.flush()
    session.add(
        PatientIdentifier(
            hospital_id=second_hospital.id,
            patient_id=patient.id,
            identifier_type="academic_id",
            identifier_value="A-001",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_patient_match_candidate_creation_and_relationships(session):
    hospital = make_hospital("H13")
    candidate = make_patient(hospital, "MRN-H13-001")
    possible = make_patient(hospital, "MRN-H13-002")
    candidate_row = PatientMatchCandidate(
        hospital=hospital,
        candidate_patient=candidate,
        possible_patient=possible,
        match_score=Decimal("0.8750"),
        status="open",
    )
    session.add(candidate_row)
    session.commit()
    session.expire_all()

    persisted = session.get(PatientMatchCandidate, candidate_row.id)
    assert persisted is not None
    assert persisted.candidate_patient is candidate
    assert persisted.possible_patient is possible
    assert persisted.match_score == Decimal("0.8750")
    assert candidate_row in candidate.match_candidates_as_candidate
    assert candidate_row in possible.match_candidates_as_possible


def test_patient_match_candidate_rejects_same_patient(session):
    hospital = make_hospital("H14")
    patient = make_patient(hospital, "MRN-H14-001")
    session.add(
        PatientMatchCandidate(
            hospital=hospital,
            candidate_patient=patient,
            possible_patient=patient,
            status="open",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_patient_match_candidate_rejects_cross_hospital_patients(session):
    first_hospital = make_hospital("H15")
    second_hospital = make_hospital("H16")
    candidate = make_patient(first_hospital, "MRN-H15-001")
    possible = make_patient(second_hospital, "MRN-H16-001")
    session.add_all(
        [
            PatientMatchCandidate(
                hospital=first_hospital,
                candidate_patient=candidate,
                possible_patient=possible,
                status="open",
            )
        ]
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_patient_match_candidate_accepts_same_hospital_reviewer(session):
    hospital = make_hospital("H17")
    user = make_user("Synthetic Reviewer")
    candidate = make_patient(hospital, "MRN-H17-001")
    possible = make_patient(hospital, "MRN-H17-002")
    reviewer = make_hospital_user(hospital, user)
    row = PatientMatchCandidate(
        hospital=hospital,
        candidate_patient=candidate,
        possible_patient=possible,
        reviewed_by_hospital_user=reviewer,
        reviewed_at=datetime.now(timezone.utc),
        status="confirmed_same",
    )
    session.add(row)
    session.commit()
    session.expire_all()

    persisted = session.get(PatientMatchCandidate, row.id)
    assert persisted is not None
    assert persisted.reviewed_by_hospital_user is reviewer
    assert row in reviewer.reviewed_match_candidates


def test_patient_match_candidate_rejects_cross_hospital_reviewer(session):
    first_hospital = make_hospital("H18")
    second_hospital = make_hospital("H19")
    first_user = make_user("Synthetic Reviewer One")
    second_user = make_user("Synthetic Reviewer Two")
    candidate = make_patient(first_hospital, "MRN-H18-001")
    possible = make_patient(first_hospital, "MRN-H18-002")
    foreign_reviewer = make_hospital_user(second_hospital, second_user)
    session.add_all(
        [
            PatientMatchCandidate(
                hospital=first_hospital,
                candidate_patient=candidate,
                possible_patient=possible,
                reviewed_by_hospital_user=foreign_reviewer,
                status="confirmed_same",
            )
        ]
    )
    session.add(make_hospital_user(first_hospital, first_user))

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("verification_status", "invalid"),
        ("status", "invalid"),
    ],
)
def test_invalid_identifier_and_match_statuses_are_rejected(
    session,
    field,
    value,
):
    hospital = make_hospital("H20")
    first = make_patient(hospital, "MRN-H20-001")
    second = make_patient(hospital, "MRN-H20-002")
    if field == "verification_status":
        row = PatientIdentifier(
            hospital=hospital,
            patient=first,
            identifier_type="academic_id",
            identifier_value="A-020",
            verification_status=value,
        )
    else:
        row = PatientMatchCandidate(
            hospital=hospital,
            candidate_patient=first,
            possible_patient=second,
            status=value,
        )
    session.add(row)

    with pytest.raises(IntegrityError):
        session.commit()


def test_invalid_match_score_is_rejected(session):
    hospital = make_hospital("H21")
    first = make_patient(hospital, "MRN-H21-001")
    second = make_patient(hospital, "MRN-H21-002")
    session.add(
        PatientMatchCandidate(
            hospital=hospital,
            candidate_patient=first,
            possible_patient=second,
            match_score=Decimal("1.0001"),
            status="open",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()
    MedicationStatement,
    Observation,
