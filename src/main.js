import './styles.css';
import { requireFormsAccess } from './auth/accessGuard.js';
import { runAccessControlledBootstrap } from './auth/bootstrap.js';

const status = document.getElementById('access-status');

void runAccessControlledBootstrap({
  checkAccess: requireFormsAccess,
  startProtectedApplication: async () => {
    const template = document.getElementById('protected-content');
    document.body.replaceChildren(template.content.cloneNode(true));
    const { startConverter } = await import('./converter.js');
    startConverter();
  },
  redirect: (url) => window.location.replace(url),
  showError: () => {
    status.textContent = 'Unable to verify access.';
    status.setAttribute('role', 'alert');
  },
});
