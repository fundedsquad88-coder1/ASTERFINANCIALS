import crypto from 'node:crypto';

/**
 * Production safety boundary.
 * Real-money execution remains disabled until custody, settlement,
 * authorization, compliance and regulatory controls are separately approved.
 */
export const PRODUCTION_REQUIREMENTS = [
  'DATABASE_URL',
  'ADMIN_EMAIL',
  'ADMIN_PASSWORD',
  'TWELVEDATA_API_KEY'
] as const;

export function productionConfigStatus() {
  const configured = Object.fromEntries(
    PRODUCTION_REQUIREMENTS.map(key => [key, Boolean(process.env[key])])
  );
  return {
    configured,
    allConfigured: Object.values(configured).every(Boolean),
    realMoneyExecution: false as const
  };
}

export function createRequestId() {
  return crypto.randomUUID();
}

export function isProduction() {
  return process.env.NODE_ENV === 'production';
}

/** Deliberately does not authorize financial execution. */
export function assertSandboxOnly() {
  return { allowed: true, realMoneyExecution: false } as const;
}
