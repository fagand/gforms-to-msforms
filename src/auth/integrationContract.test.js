import { readFile } from 'node:fs/promises';
import { describe, expect, it } from 'vitest';

describe('Forms Converter integration contract', () => {
  it('keeps converter DOM and code behind the access check', async () => {
    const html = await readFile('index.html', 'utf8');
    const main = await readFile('src/main.js', 'utf8');
    expect(html).toContain('Checking access…');
    expect(html).toContain('<template id="protected-content">');
    expect(main.indexOf('runAccessControlledBootstrap')).toBeLessThan(main.indexOf("import('./converter.js')"));
  });

  it('uses only browser-safe Supabase environment names', async () => {
    const source = await readFile('src/auth/config.js', 'utf8');
    expect(source).toContain('VITE_SUPABASE_URL');
    expect(source).toContain('VITE_SUPABASE_PUBLISHABLE_KEY');
    expect(source).not.toMatch(/SERVICE_ROLE|DATABASE_PASSWORD|SECRET/i);
  });

  it('configures the production base path', async () => {
    const config = await readFile('vite.config.js', 'utf8');
    expect(config).toContain("base: '/work/forms/'");
  });
});
