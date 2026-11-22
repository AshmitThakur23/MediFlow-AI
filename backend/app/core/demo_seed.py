from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.appointment import Appointment
from app.models.allergy_intolerance import AllergyIntolerance
from app.models.condition import Condition
from app.models.encounter import Encounter
from app.models.hospital import Hospital
from app.models.hospital_user import HospitalUser
from app.models.medication_statement import MedicationStatement
from app.models.observation import Observation
from app.models.patient import Patient
from app.models.provenance_record import ProvenanceRecord
from app.models.user import User


DEMO_EMAIL = "doctor.synthetic@mediflow.local"
DEMO_PASSWORD = "MediFlowDemo123!"


def seed_demo_data(db: Session) -> None:
    hospital = db.scalar(
        select(Hospital).where(Hospital.code == "SYN-001")
    )
    if hospital is None:
        hospital = Hospital(
            name="MediFlow Synthetic Hospital",
            code="SYN-001",
            status="active",
        )
        db.add(hospital)
        db.flush()

    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        user = User(
            email=DEMO_EMAIL,
            display_name="Dr. Aanya Sharma",
            status="active",
            password_hash=hash_password(DEMO_PASSWORD),
        )
        db.add(user)
        db.flush()

    doctor = db.scalar(
        select(HospitalUser).where(
            HospitalUser.hospital_id == hospital.id,
            HospitalUser.user_id == user.id,
        )
    )
    if doctor is None:
        doctor = HospitalUser(
            hospital=hospital,
            user=user,
            role_code="doctor",
            relationship_scope="hospital",
            status="active",
            valid_from=datetime.now(timezone.utc) - timedelta(days=30),
        )
        db.add(doctor)
        db.flush()

    synthetic_patients = [
        ("MRN-DEMO-001", "Meera", "Patel", datetime(1994, 5, 18).date(), "female"),
        ("MRN-DEMO-002", "Rohan", "Verma", datetime(1981, 9, 3).date(), "male"),
        ("MRN-DEMO-003", "Sara", "Khan", datetime(1998, 1, 26).date(), "female"),
    ]

    for offset, (mrn, given, family, dob, sex) in enumerate(synthetic_patients):
        patient = db.scalar(
            select(Patient).where(
                Patient.hospital_id == hospital.id,
                Patient.synthetic_mrn == mrn,
            )
        )
        if patient is None:
            patient = Patient(
                hospital=hospital,
                synthetic_mrn=mrn,
                given_name=given,
                family_name=family,
                date_of_birth=dob,
                sex_at_birth=sex,
                identity_status="verified",
            )
            db.add(patient)
            db.flush()

        appointment = db.scalar(
            select(Appointment).where(
                Appointment.hospital_id == hospital.id,
                Appointment.patient_id == patient.id,
            )
        )
        if appointment is None:
            appointment = Appointment(
                hospital=hospital,
                patient=patient,
                doctor_hospital_user=doctor,
                scheduled_at=datetime.now(timezone.utc)
                + timedelta(minutes=8 * (offset + 1)),
                status="scheduled",
            )
            db.add(appointment)
            db.flush()

        encounter = db.scalar(
            select(Encounter).where(
                Encounter.hospital_id == hospital.id,
                Encounter.patient_id == patient.id,
            )
        )
        if encounter is None:
            encounter = Encounter(
                hospital=hospital,
                patient=patient,
                appointment=appointment,
                doctor_hospital_user=doctor,
                status="planned",
            )
            db.add(encounter)
            db.flush()

        if mrn == "MRN-DEMO-001":
            provenance = db.scalar(
                select(ProvenanceRecord).where(
                    ProvenanceRecord.hospital_id == hospital.id,
                    ProvenanceRecord.patient_id == patient.id,
                )
            )
            if provenance is None:
                provenance = ProvenanceRecord(
                    hospital=hospital,
                    patient=patient,
                    encounter=encounter,
                    author_hospital_user=doctor,
                    source_type="doctor_entry",
                    recorded_at=datetime.now(timezone.utc),
                    verification_status="reviewed",
                    uncertainty="unknown",
                )
                db.add(provenance)
                db.flush()

            if db.scalar(
                select(Condition).where(
                    Condition.hospital_id == hospital.id,
                    Condition.patient_id == patient.id,
                )
            ) is None:
                db.add(
                    Condition(
                        hospital=hospital,
                        patient=patient,
                        encounter=encounter,
                        provenance=provenance,
                        display_name="Asthma",
                        status="active",
                        verification_status="verified",
                        onset_at=datetime(2023, 4, 10, tzinfo=timezone.utc),
                    )
                )
            if db.scalar(
                select(AllergyIntolerance).where(
                    AllergyIntolerance.hospital_id == hospital.id,
                    AllergyIntolerance.patient_id == patient.id,
                )
            ) is None:
                db.add(
                    AllergyIntolerance(
                        hospital=hospital,
                        patient=patient,
                        encounter=encounter,
                        provenance=provenance,
                        substance="Penicillin",
                        reaction="Rash",
                        criticality="high",
                        status="active",
                        verification_status="verified",
                        reported_at=datetime(2024, 2, 12, tzinfo=timezone.utc),
                    )
                )
            if db.scalar(
                select(Observation).where(
                    Observation.hospital_id == hospital.id,
                    Observation.patient_id == patient.id,
                )
            ) is None:
                db.add(
                    Observation(
                        hospital=hospital,
                        patient=patient,
                        encounter=encounter,
                        provenance=provenance,
                        observation_type="vital",
                        test_name="Oxygen saturation",
                        value_text="98%",
                        unit="%",
                        reported_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
                    )
                )
            if db.scalar(
                select(MedicationStatement).where(
                    MedicationStatement.hospital_id == hospital.id,
                    MedicationStatement.patient_id == patient.id,
                )
            ) is None:
                db.add(
                    MedicationStatement(
                        hospital=hospital,
                        patient=patient,
                        encounter=encounter,
                        provenance=provenance,
                        medicine_name="Montelukast",
                        statement_type="prescribed",
                        status="active",
                        dose="10 mg once nightly",
                        verification_status="verified",
                    )
                )

    db.commit()
