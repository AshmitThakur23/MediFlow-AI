import { GoogleGenAI, Type } from '@google/genai'
import type { ExtractedDraft, FormattedPersonalNotes, Patient } from './types.ts'

const DEFAULT_GEMINI_MODEL = 'gemini-4-hydrogen'

const clinicalDraftResponseSchema = {
  type: Type.OBJECT,
  properties: {
    chief_complaint: { type: Type.STRING },
    history_of_present_illness: { type: Type.STRING },
    patient_reported_facts: {
      type: Type.ARRAY,
      items: { type: Type.STRING },
    },
    doctor_questions: {
      type: Type.ARRAY,
      items: { type: Type.STRING },
    },
    examination_findings: {
      type: Type.ARRAY,
      items: { type: Type.STRING },
    },
    assessment: { type: Type.STRING },
    plan: { type: Type.STRING },
    missing_information: {
      type: Type.ARRAY,
      items: { type: Type.STRING },
    },
    uncertainty: {
      type: Type.ARRAY,
      items: { type: Type.STRING },
    },
    medication_candidates: {
      type: Type.ARRAY,
      items: { type: Type.STRING },
    },
    prescription_draft: {
      type: Type.OBJECT,
      properties: {
        medicines: {
          type: Type.ARRAY,
          items: {
            type: Type.OBJECT,
            properties: {
              medicine_name: { type: Type.STRING },
              strength: { type: Type.STRING, nullable: true },
              dose: { type: Type.STRING, nullable: true },
              route: { type: Type.STRING, nullable: true },
              frequency: { type: Type.STRING, nullable: true },
              duration: { type: Type.STRING, nullable: true },
              quantity: { type: Type.STRING, nullable: true },
              instructions: { type: Type.STRING, nullable: true },
              source_uncertainty: { type: Type.STRING, nullable: true },
            },
            required: ['medicine_name'],
          },
        },
        advice: {
          type: Type.ARRAY,
          items: { type: Type.STRING },
        },
        follow_up: { type: Type.STRING, nullable: true },
        missing_prescription_information: {
          type: Type.ARRAY,
          items: { type: Type.STRING },
        },
      },
      required: [
        'medicines',
        'advice',
        'missing_prescription_information',
      ],
    },
  },
  required: [
    'chief_complaint',
    'history_of_present_illness',
    'patient_reported_facts',
    'doctor_questions',
    'examination_findings',
    'assessment',
    'plan',
    'missing_information',
    'uncertainty',
    'medication_candidates',
    'prescription_draft',
  ],
}

function getGeminiClient(): GoogleGenAI {
  const apiKey = process.env.GEMINI_API_KEY
  if (!apiKey) {
    throw new Error('GEMINI_API_KEY_MISSING')
  }
  return new GoogleGenAI({
    apiKey,
    apiVersion: 'v1beta',
    httpOptions: {
      headers: {
        'User-Agent': 'aistudio-build',
      },
    },
  })
}

export async function generateClinicalDraftWithGemini(params: {
  patient: Patient
  transcript: string
  manualText: string
}): Promise<ExtractedDraft> {
  const ai = getGeminiClient()
  const model = process.env.GEMINI_MODEL?.trim() || DEFAULT_GEMINI_MODEL

  const systemInstruction = [
    'You are a clinical documentation assistant for an academic synthetic-data system.',
    'Never diagnose, prescribe, sign, approve, or create a confirmed clinical assessment.',
    'Produce an editable draft only.',
    'Separate patient-reported statements from doctor findings.',
    'Preserve negation, uncertainty, duration, missing information and contradictions.',
    'Do not invent medicines, doses, diagnoses or findings.',
    'The patient is synthetic.',
    'Build a reviewable prescription_draft only. Never make it a confirmed prescription.',
    'For each medicine candidate, preserve only information supported by the transcript.',
    'If a dose, route, frequency or duration is missing or unclear, set it to null or place it in missing_prescription_information. Do not invent clinical data.',
  ].join('\n')

  const prompt = [
    'Patient:',
    `${params.patient.given_name} ${params.patient.family_name}`,
    `MRN: ${params.patient.synthetic_mrn}`,
    '',
    'Consultation transcript:',
    params.transcript,
    '',
    'Clinician-entered text and existing template fields:',
    params.manualText || 'None',
    '',
    'Return only JSON matching the requested schema.',
  ].join('\n')

  const response = await ai.models.generateContent({
    model,
    contents: prompt,
    config: {
      systemInstruction,
      responseMimeType: 'application/json',
      responseSchema: clinicalDraftResponseSchema,
    },
  })

  const rawText = (response.text ?? '').trim()
  if (!rawText) {
    throw new Error('Empty response from Gemini')
  }

  const parsed = JSON.parse(rawText) as Partial<ExtractedDraft>

  return {
    chief_complaint: parsed.chief_complaint ?? 'Pending clinician review',
    history_of_present_illness: parsed.history_of_present_illness ?? '',
    patient_reported_facts: Array.isArray(parsed.patient_reported_facts)
      ? parsed.patient_reported_facts
      : [],
    doctor_questions: Array.isArray(parsed.doctor_questions)
      ? parsed.doctor_questions
      : [],
    examination_findings: Array.isArray(parsed.examination_findings)
      ? parsed.examination_findings
      : [],
    assessment: parsed.assessment ?? 'Draft only — clinician approval required',
    plan: parsed.plan ?? '',
    missing_information: Array.isArray(parsed.missing_information)
      ? parsed.missing_information
      : [],
    uncertainty: Array.isArray(parsed.uncertainty) ? parsed.uncertainty : [],
    medication_candidates: Array.isArray(parsed.medication_candidates)
      ? parsed.medication_candidates
      : [],
    prescription_draft: {
      medicines: Array.isArray(parsed.prescription_draft?.medicines)
        ? parsed.prescription_draft.medicines.map((medicine) => ({
            medicine_name: medicine.medicine_name ?? '',
            strength: medicine.strength ?? null,
            dose: medicine.dose ?? null,
            route: medicine.route ?? null,
            frequency: medicine.frequency ?? null,
            duration: medicine.duration ?? null,
            quantity: medicine.quantity ?? null,
            instructions: medicine.instructions ?? null,
            source_uncertainty: medicine.source_uncertainty ?? null,
          }))
        : [],
      advice: Array.isArray(parsed.prescription_draft?.advice)
        ? parsed.prescription_draft.advice
        : [],
      follow_up: parsed.prescription_draft?.follow_up ?? null,
      missing_prescription_information: Array.isArray(
        parsed.prescription_draft?.missing_prescription_information,
      )
        ? parsed.prescription_draft.missing_prescription_information
        : [],
    },
  }
}

const personalNotesResponseSchema = {
  type: Type.OBJECT,
  properties: {
    mode_applied: {
      type: Type.STRING,
      description:
        'Use "concise_polish" when the input is short (spelling/grammar polish + point-wise formatting), or "key_points_summary" when the input is long (distilled main points).',
    },
    title: { type: Type.STRING },
    bullet_points: {
      type: Type.ARRAY,
      items: { type: Type.STRING },
    },
    spelling_corrections_note: { type: Type.STRING, nullable: true },
    uncertainties: {
      type: Type.ARRAY,
      items: { type: Type.STRING },
    },
  },
  required: ['mode_applied', 'title', 'bullet_points', 'uncertainties'],
}

export async function formatPersonalNotesWithGemini(params: {
  patient: Patient
  rawText: string
  inputMode: 'voice' | 'written'
}): Promise<FormattedPersonalNotes> {
  const ai = getGeminiClient()
  const model = process.env.GEMINI_MODEL?.trim() || DEFAULT_GEMINI_MODEL

  const wordCount = params.rawText.trim().split(/\s+/).filter(Boolean).length
  const isLongConversation = wordCount >= 45

  const systemInstruction = [
    'You are a clinical patient-communication assistant for an academic synthetic-data system.',
    'Never diagnose, prescribe, invent medicines or doses, or approve clinical decisions.',
    'Produce an editable point-wise draft of patient instructions for clinician review only.',
    'If the input is short (roughly under 45 words or a brief note): fix spelling, grammar, and clarity while keeping all clinician-stated points, format them cleanly as concise point-wise bullet items, and set mode_applied to "concise_polish".',
    'If the input is long (a detailed consultation conversation or long notes): extract and organize ONLY the most important patient-facing takeaways, care instructions, precautions, and follow-up steps into clear point-wise bullet items, and set mode_applied to "key_points_summary".',
    'Preserve negations, warnings, and exact timings stated by the clinician.',
    'Do not fabricate missing doses, diagnoses, or instructions. Place unclear fragments in uncertainties.',
    'The patient is synthetic.',
  ].join('\n')

  const prompt = [
    `Patient: ${params.patient.given_name} ${params.patient.family_name} (MRN: ${params.patient.synthetic_mrn})`,
    `Input mode: ${params.inputMode}`,
    `Approximate word count: ${wordCount} (${isLongConversation ? 'long input — summarize main key points' : 'short input — fix spelling and format point-wise'})`,
    '',
    'Clinician note / conversation text:',
    params.rawText,
    '',
    'Return only JSON matching the requested schema.',
  ].join('\n')

  const response = await ai.models.generateContent({
    model,
    contents: prompt,
    config: {
      systemInstruction,
      responseMimeType: 'application/json',
      responseSchema: personalNotesResponseSchema,
    },
  })

  const rawOutput = (response.text ?? '').trim()
  if (!rawOutput) {
    throw new Error('Empty response from Gemini')
  }

  const parsed = JSON.parse(rawOutput) as Partial<FormattedPersonalNotes>
  const modeApplied =
    parsed.mode_applied === 'key_points_summary' ||
    (parsed.mode_applied !== 'concise_polish' && isLongConversation)
      ? 'key_points_summary'
      : 'concise_polish'

  const bulletPoints = Array.isArray(parsed.bullet_points)
    ? parsed.bullet_points.map((item) => String(item).trim()).filter(Boolean)
    : []

  return {
    mode_applied: modeApplied,
    title: parsed.title?.trim() || 'Patient Care Instructions',
    bullet_points:
      bulletPoints.length > 0 ? bulletPoints : [params.rawText.trim()],
    spelling_corrections_note: parsed.spelling_corrections_note ?? null,
    uncertainties: Array.isArray(parsed.uncertainties)
      ? parsed.uncertainties.map((item) => String(item).trim()).filter(Boolean)
      : [],
  }
}

