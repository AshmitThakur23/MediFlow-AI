import crypto from 'node:crypto'
import type { NextFunction, Request, Response } from 'express'
import type { AuthorizationContext, HospitalUser, User } from './types.ts'
import { store } from './store.ts'

const PBKDF2_ALGORITHM = 'sha256'
const PBKDF2_ITERATIONS = 600_000
const PBKDF2_KEYLEN = 32
const PASSWORD_HASH_PARTS = 4

export const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export function isValidUuid(value: unknown): value is string {
  return typeof value === 'string' && UUID_PATTERN.test(value)
}

export function hashPassword(password: string): string {
  if (!password) {
    throw new Error('Password is required')
  }
  const salt = crypto.randomBytes(16)
  const digest = crypto.pbkdf2Sync(
    password,
    salt,
    PBKDF2_ITERATIONS,
    PBKDF2_KEYLEN,
    PBKDF2_ALGORITHM,
  )
  return `pbkdf2_${PBKDF2_ALGORITHM}$${PBKDF2_ITERATIONS}$${salt.toString('base64')}$${digest.toString('base64')}`
}

export function verifyPassword(
  password: string,
  passwordHash: string | null | undefined,
): boolean {
  if (!password || !passwordHash) return false
  const parts = passwordHash.split('$')
  if (parts.length !== PASSWORD_HASH_PARTS) return false
  const [algorithmLabel, iterationsText, saltText, digestText] = parts
  if (algorithmLabel !== `pbkdf2_${PBKDF2_ALGORITHM}`) return false

  const iterations = Number.parseInt(iterationsText, 10)
  if (!Number.isFinite(iterations) || iterations <= 0) return false

  try {
    const salt = Buffer.from(saltText, 'base64')
    const expectedDigest = Buffer.from(digestText, 'base64')
    const actualDigest = crypto.pbkdf2Sync(
      password,
      salt,
      iterations,
      expectedDigest.length,
      PBKDF2_ALGORITHM,
    )
    if (actualDigest.length !== expectedDigest.length) return false
    return crypto.timingSafeEqual(actualDigest, expectedDigest)
  } catch {
    return false
  }
}

export function authenticateUser(email: string, password: string): User | null {
  for (const user of store.users.values()) {
    if (user.email === email && user.status === 'active') {
      if (verifyPassword(password, user.password_hash)) {
        return user
      }
      return null
    }
  }
  return null
}

export function getActiveHospitalAssignments(user: User): HospitalUser[] {
  const now = Date.now()
  const active: HospitalUser[] = []
  for (const assignment of store.hospitalUsers.values()) {
    if (assignment.user_id !== user.id || assignment.status !== 'active') {
      continue
    }
    const validFrom = Date.parse(assignment.valid_from)
    const validUntil = assignment.valid_until
      ? Date.parse(assignment.valid_until)
      : null
    if (validFrom <= now && (validUntil === null || validUntil >= now)) {
      active.push(assignment)
    }
  }
  return active
}

export function findActiveHospitalAssignment(
  assignments: HospitalUser[],
  hospitalId: string,
): HospitalUser | null {
  return (
    assignments.find((assignment) => assignment.hospital_id === hospitalId) ??
    null
  )
}

export function validateLegitimatePurpose(
  purpose: string | undefined | null,
): boolean {
  if (!purpose) return false
  const normalized = purpose.trim()
  return normalized.length >= 1 && normalized.length <= 128
}

export function validatePatientObjectAccess(
  assignment: HospitalUser,
  patientId: string | null | undefined,
): boolean {
  if (!patientId) return false
  if (assignment.relationship_scope === 'hospital') return true
  // Department and patient_relationship scopes fail closed until a relationship model exists.
  return false
}

export function parseBasicAuth(
  req: Request,
): { username: string; password: string } | null {
  const authHeader = req.header('authorization')
  if (!authHeader || !authHeader.startsWith('Basic ')) return null
  try {
    const decoded = Buffer.from(authHeader.slice(6).trim(), 'base64').toString(
      'utf-8',
    )
    const colonIndex = decoded.indexOf(':')
    if (colonIndex === -1) return null
    return {
      username: decoded.slice(0, colonIndex),
      password: decoded.slice(colonIndex + 1),
    }
  } catch {
    return null
  }
}

export interface AuthenticatedRequest extends Request {
  authContext?: AuthorizationContext
}

export function requireRoles(...allowedRoleCodes: string[]) {
  return (
    req: AuthenticatedRequest,
    res: Response,
    next: NextFunction,
  ): void => {
    const credentials = parseBasicAuth(req)
    if (!credentials) {
      res.setHeader('WWW-Authenticate', 'Basic')
      res.status(401).json({ detail: 'Invalid email or password' })
      return
    }
    const user = authenticateUser(credentials.username, credentials.password)
    if (!user) {
      res.setHeader('WWW-Authenticate', 'Basic')
      res.status(401).json({ detail: 'Invalid email or password' })
      return
    }

    const hospitalId = req.header('x-hospital-id')
    if (!isValidUuid(hospitalId)) {
      res.status(422).json({ detail: 'Valid X-Hospital-Id header is required' })
      return
    }

    const purpose = req.header('x-mediflow-purpose')
    if (!validateLegitimatePurpose(purpose)) {
      res.status(400).json({ detail: 'X-Mediflow-Purpose is required' })
      return
    }

    const assignments = getActiveHospitalAssignments(user)
    const assignment = findActiveHospitalAssignment(assignments, hospitalId)
    if (!assignment) {
      res.status(403).json({
        detail: 'No active assignment in the requested hospital',
      })
      return
    }

    if (
      allowedRoleCodes.length > 0 &&
      !allowedRoleCodes.includes(assignment.role_code)
    ) {
      res.status(403).json({
        detail: 'Role is not permitted for this operation',
      })
      return
    }

    req.authContext = {
      user,
      assignment,
      hospitalId,
      purpose: purpose!.trim(),
    }
    next()
  }
}
