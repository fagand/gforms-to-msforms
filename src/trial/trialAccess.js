export const TRIAL_STORAGE_KEY = 'work-tools:trial:v1';
export const TRIAL_DURATION_MS = 30 * 1000;

export function readToolTrial(toolId, now = Date.now()) {
  try {
    let value = JSON.parse(sessionStorage.getItem(TRIAL_STORAGE_KEY) || 'null');
    if (!value && new URLSearchParams(location.search).get('trial') === '1') {
      const startedAt = Number(new URLSearchParams(location.search).get('trialStartedAt'));
      if (Number.isFinite(startedAt) && startedAt <= now + 5000) {
        value = { toolId, startedAt, expiresAt: startedAt + TRIAL_DURATION_MS };
        sessionStorage.setItem(TRIAL_STORAGE_KEY, JSON.stringify(value));
      }
    }
    if (!value || value.toolId !== toolId) return null;
    const expiresAt = Math.min(value.expiresAt, value.startedAt + TRIAL_DURATION_MS);
    return expiresAt > now ? { ...value, expiresAt } : null;
  } catch { return null; }
}

export const isToolTrialActive = (toolId, now = Date.now()) => Boolean(readToolTrial(toolId, now));

export function mountTrialBanner(toolId, onExpire) {
  const trial = readToolTrial(toolId);
  if (!trial) return;
  const banner = document.createElement('aside');
  banner.setAttribute('role', 'status');
  banner.style.cssText = 'position:sticky;top:0;z-index:10000;display:flex;align-items:center;justify-content:center;gap:12px;padding:8px 16px;background:#fff4cc;border-bottom:1px solid #d8b85d;color:#44360d;font:600 13px/1.3 system-ui';
  let timer = 0;
  const update = () => {
    const remaining = Math.max(0, trial.expiresAt - Date.now());
    banner.innerHTML = `<strong>Private trial</strong><span>${Math.ceil(remaining / 1000)} seconds remaining</span><a href="/work/">Sign in</a>`;
    if (!remaining) { clearInterval(timer); onExpire(); }
  };
  document.body.prepend(banner);
  update();
  timer = window.setInterval(update, 250);
}
