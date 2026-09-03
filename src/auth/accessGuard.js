import { getSupabaseClient } from './supabaseClient.js';

export const FORMS_TOOL_ID = 'forms';
export const FORMS_PATH = '/work/forms/';
export const SIGNED_OUT_REDIRECT = '/work/?next=/work/forms/';
export const ACCESS_DENIED_REDIRECT = '/work/?denied=1';

export async function requireFormsAccess(client = getSupabaseClient()) {
  const { data: sessionData, error: sessionError } = await client.auth.getSession();
  if (sessionError) throw sessionError;

  if (!sessionData.session) {
    return { allowed: false, reason: 'signed-out', redirectTo: SIGNED_OUT_REDIRECT };
  }

  const { data, error } = await client.from('user_tool_access').select('tool_id');
  if (error) throw error;

  const allowed = (data ?? []).some(({ tool_id }) => String(tool_id) === FORMS_TOOL_ID);
  return allowed
    ? { allowed: true }
    : { allowed: false, reason: 'forbidden', redirectTo: ACCESS_DENIED_REDIRECT };
}
