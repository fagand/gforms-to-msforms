import './styles.css';
import { requireFormsAccess } from './auth/accessGuard.js';
import { runAccessControlledBootstrap } from './auth/bootstrap.js';
import { isToolTrialActive, mountTrialBanner } from './trial/trialAccess.js';

const status = document.getElementById('access-status');

void runAccessControlledBootstrap({
  checkAccess: requireFormsAccess,
  startProtectedApplication: async () => {
    const template = document.getElementById('protected-content');
    document.body.replaceChildren(template.content.cloneNode(true));
    const { startConverter } = await import('./converter.js');
    startConverter();
    if (isToolTrialActive('forms')) mountTrialBanner('forms', () => {
      document.body.innerHTML = '<main style="max-width:42rem;margin:7rem auto;padding:2rem;text-align:center"><h1>Your trial has ended</h1><p>Sign in to continue using Forms Converter.</p><a href="/work/?next=/work/forms/">Sign in</a></main>';
    });
  },
  redirect: (url) => window.location.replace(url),
  showError: () => {
    status.textContent = 'Unable to verify access.';
    status.setAttribute('role', 'alert');
  },
});
