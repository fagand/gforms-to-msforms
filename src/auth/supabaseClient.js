import { createClient } from '@supabase/supabase-js';
import { getAuthConfig } from './config.js';

export const AUTH_STORAGE_KEY = 'work-portal-auth';

let client;

export function getSupabaseClient() {
  const config = getAuthConfig();
  client ??= createClient(config.supabaseUrl, config.supabasePublishableKey, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
      storageKey: AUTH_STORAGE_KEY,
    },
  });
  return client;
}
