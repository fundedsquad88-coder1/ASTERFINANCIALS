import { cleanupSecurityState } from './security-persistence';

let started = false;

export function startSecurityMaintenance() {
  if (started) return;
  started = true;
  void cleanupSecurityState();
  setInterval(() => void cleanupSecurityState(), 15 * 60 * 1000).unref();
}
