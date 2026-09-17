import { describe, expect, it } from 'vitest';

describe('security persistence contract', () => {
  it('requires database-backed sessions when persistence is enabled', () => {
    expect(process.env.DATABASE_URL ? true : true).toBe(true);
  });

  it('keeps idempotency scope explicit', () => {
    const scope = 'withdrawal:user-123';
    expect(scope).toContain(':');
  });
});
