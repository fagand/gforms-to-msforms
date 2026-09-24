import { getSupabaseClient } from './supabaseClient.js';
import { isToolTrialActive } from '../trial/trialAccess.js';

export const FORMS_TOOL_ID = 'forms';
export const FORMS_PATH = '/work/forms/';
export const SIGNED_OUT_REDIRECT = '/work/?next=/work/forms/';
export const ACCESS_DENIED_REDIRECT = '/work/?denied=1';

export async function requireFormsAccess(client = getSupabaseClient()) {
  if (isToolTrialActive(FORMS_TOOL_ID)) return { allowed: true, trial: true };
  const { data: sessionData, error: sessionError } = await client.auth.getSession();
  if (sessionError) throw sessionError;

  if (!sessionData.session) {
    return { allowed: false, reason: 'signed-out', redirectTo: SIGNED_OUT_REDIRECT };
  }

  const { data, error } = await client.rpc('has_tool_access', {
    p_tool_id: FORMS_TOOL_ID,
  });
  if (error) throw error;

  return data === true
    ? { allowed: true }
    : { allowed: false, reason: 'forbidden', redirectTo: ACCESS_DENIED_REDIRECT };
}
