import { describe, expect, it, vi } from 'vitest';
import {
  ACCESS_DENIED_REDIRECT,
  FORMS_PATH,
  FORMS_TOOL_ID,
  SIGNED_OUT_REDIRECT,
  requireFormsAccess,
} from './accessGuard.js';

function clientWith(session, rpcResult = { data: false, error: null }) {
  return {
    auth: { getSession: vi.fn().mockResolvedValue({ data: { session }, error: null }) },
    rpc: vi.fn().mockResolvedValue(rpcResult),
  };
}

describe('Forms Converter access guard', () => {
  it('redirects a signed-out user to the exact protected return path', async () => {
    const client = clientWith(null);
    await expect(requireFormsAccess(client)).resolves.toEqual({
      allowed: false,
      reason: 'signed-out',
      redirectTo: '/work/?next=/work/forms/',
    });
    expect(client.rpc).not.toHaveBeenCalled();
    expect(SIGNED_OUT_REDIRECT).toBe('/work/?next=/work/forms/');
    expect(FORMS_PATH).toBe('/work/forms/');
  });

  it('denies an authenticated user without forms permission', async () => {
    const client = clientWith({ user: {} }, { data: false, error: null });
    await expect(requireFormsAccess(client)).resolves.toEqual({
      allowed: false,
      reason: 'forbidden',
      redirectTo: ACCESS_DENIED_REDIRECT,
    });
    expect(client.rpc).toHaveBeenCalledWith('has_tool_access', { p_tool_id: 'forms' });
  });

  it('allows an authenticated user with forms permission', async () => {
    const client = clientWith({ user: {} }, { data: true, error: null });
    await expect(requireFormsAccess(client)).resolves.toEqual({ allowed: true });
    expect(client.rpc).toHaveBeenCalledWith('has_tool_access', { p_tool_id: FORMS_TOOL_ID });
  });

  it('fails closed when the access RPC returns an error', async () => {
    const error = new Error('RPC unavailable');
    const client = clientWith({ user: {} }, { data: null, error });
    await expect(requireFormsAccess(client)).rejects.toBe(error);
    expect(client.rpc).toHaveBeenCalledWith('has_tool_access', { p_tool_id: 'forms' });
  });
});
