import { describe, expect, it, vi } from 'vitest';
import { runAccessControlledBootstrap } from './bootstrap.js';

describe('access-controlled bootstrap', () => {
  it('does not initialise protected content before approval', async () => {
    let resolveAccess;
    const checkAccess = vi.fn(() => new Promise((resolve) => { resolveAccess = resolve; }));
    const startProtectedApplication = vi.fn();
    const pending = runAccessControlledBootstrap({
      checkAccess,
      startProtectedApplication,
      redirect: vi.fn(),
      showError: vi.fn(),
    });

    await Promise.resolve();
    expect(startProtectedApplication).not.toHaveBeenCalled();
    resolveAccess({ allowed: true });
    await expect(pending).resolves.toBe(true);
    expect(startProtectedApplication).toHaveBeenCalledOnce();
  });

  it('redirects without initialising when access is denied', async () => {
    const startProtectedApplication = vi.fn();
    const redirect = vi.fn();
    await expect(runAccessControlledBootstrap({
      checkAccess: vi.fn().mockResolvedValue({ allowed: false, redirectTo: '/work/?denied=1' }),
      startProtectedApplication,
      redirect,
      showError: vi.fn(),
    })).resolves.toBe(false);
    expect(redirect).toHaveBeenCalledWith('/work/?denied=1');
    expect(startProtectedApplication).not.toHaveBeenCalled();
  });

  it('keeps protected content hidden when verification errors', async () => {
    const startProtectedApplication = vi.fn();
    const showError = vi.fn();
    await expect(runAccessControlledBootstrap({
      checkAccess: vi.fn().mockRejectedValue(new Error('network')),
      startProtectedApplication,
      redirect: vi.fn(),
      showError,
    })).resolves.toBe(false);
    expect(showError).toHaveBeenCalledOnce();
    expect(startProtectedApplication).not.toHaveBeenCalled();
  });
});
