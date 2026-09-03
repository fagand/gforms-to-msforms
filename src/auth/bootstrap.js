export async function runAccessControlledBootstrap({ checkAccess, startProtectedApplication, redirect, showError }) {
  try {
    const result = await checkAccess();
    if (!result.allowed) {
      redirect(result.redirectTo);
      return false;
    }
    await startProtectedApplication();
    return true;
  } catch (error) {
    console.error('Unable to verify Forms Converter access.', error);
    showError();
    return false;
  }
}
