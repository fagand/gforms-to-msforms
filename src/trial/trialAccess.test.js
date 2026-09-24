import { beforeEach, describe, expect, it } from 'vitest';
import { isToolTrialActive, readToolTrial, TRIAL_DURATION_MS, TRIAL_STORAGE_KEY } from './trialAccess.js';

describe('Forms Converter trial', () => {
  beforeEach(() => sessionStorage.clear());
  it('lasts thirty seconds and is tool-specific', () => {
    sessionStorage.setItem(TRIAL_STORAGE_KEY, JSON.stringify({toolId:'forms',startedAt:1_000,expiresAt:1_000+TRIAL_DURATION_MS}));
    expect(isToolTrialActive('forms',30_999)).toBe(true);
    expect(isToolTrialActive('forms',31_000)).toBe(false);
    expect(readToolTrial('bulletin',2_000)).toBeNull();
  });
});
