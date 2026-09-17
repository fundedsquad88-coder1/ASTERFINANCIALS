import crypto from 'node:crypto';

/**
 * Production safety boundary.
 * Real-money execution remains disabled until the deployment explicitly
 * satisfies the required controls. This module deliberately fails closed.
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
  const allConfigured = Object.values(configured).every(Boolean);
  return { configured, allConfigured, realMoneyExecution: false };
}

export function createRequestId() {
  return crypto.randomUUID();
}

export function isProduction() {
  return process.env.NODE_ENV === 'production';
}

/** Never use this as an authorization check for financial execution. */
export function assertSandboxOnly() {
  return { allowed: true, realMoneyExecution: false } as const;
}
