import { beforeEach, describe, expect, it, vi } from 'vitest';

const createClient = vi.fn(() => ({ client: true }));
vi.mock('@supabase/supabase-js', () => ({ createClient }));
vi.mock('./config.js', () => ({
  getAuthConfig: () => ({
    supabaseUrl: 'https://project.supabase.co',
    supabasePublishableKey: 'publishable',
  }),
}));

describe('shared Supabase client', () => {
  beforeEach(() => createClient.mockClear());

  it('reuses the portal auth storage namespace', async () => {
    const { AUTH_STORAGE_KEY, getSupabaseClient } = await import('./supabaseClient.js');
    expect(getSupabaseClient()).toEqual({ client: true });
    expect(AUTH_STORAGE_KEY).toBe('work-portal-auth');
    expect(createClient).toHaveBeenCalledWith(
      'https://project.supabase.co',
      'publishable',
      {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
          storageKey: 'work-portal-auth',
        },
      },
    );
  });
});
