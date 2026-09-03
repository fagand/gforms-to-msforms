import { describe, expect, it, vi } from 'vitest';
import {
  ACCESS_DENIED_REDIRECT,
  FORMS_PATH,
  FORMS_TOOL_ID,
  SIGNED_OUT_REDIRECT,
  requireFormsAccess,
} from './accessGuard.js';

function clientWith(session, toolIds = []) {
  return {
    auth: { getSession: vi.fn().mockResolvedValue({ data: { session }, error: null }) },
    from: vi.fn(() => ({
      select: vi.fn().mockResolvedValue({
        data: toolIds.map((tool_id) => ({ tool_id })),
        error: null,
      }),
    })),
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
    expect(client.from).not.toHaveBeenCalled();
    expect(SIGNED_OUT_REDIRECT).toBe('/work/?next=/work/forms/');
    expect(FORMS_PATH).toBe('/work/forms/');
  });

  it('denies an authenticated user without forms permission', async () => {
    await expect(requireFormsAccess(clientWith({ user: {} }, ['reports']))).resolves.toEqual({
      allowed: false,
      reason: 'forbidden',
      redirectTo: ACCESS_DENIED_REDIRECT,
    });
  });

  it('allows an authenticated user with forms permission', async () => {
    const client = clientWith({ user: {} }, ['reports', FORMS_TOOL_ID]);
    await expect(requireFormsAccess(client)).resolves.toEqual({ allowed: true });
    expect(client.from).toHaveBeenCalledWith('user_tool_access');
  });
});
