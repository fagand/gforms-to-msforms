import { readFile, readdir } from 'node:fs/promises';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadEnv } from 'vite';

const root = dirname(fileURLToPath(new URL('../package.json', import.meta.url)));
const env = loadEnv('production', root, 'VITE_');
const requiredConfig = ['VITE_SUPABASE_URL', 'VITE_SUPABASE_PUBLISHABLE_KEY'];

for (const name of requiredConfig) {
  if (!env[name]?.trim()) throw new Error(`${name} is required for a production build.`);
}

const html = await readFile(new URL('../app/static/index.html', import.meta.url), 'utf8');
if (!html.includes('/work/forms/assets/')) {
  throw new Error('Production assets are not rooted at /work/forms/.');
}

const assetNames = await readdir(new URL('../app/static/assets/', import.meta.url));
const browserCode = (await Promise.all(
  assetNames.filter((name) => name.endsWith('.js')).map((name) =>
    readFile(new URL(`../app/static/assets/${name}`, import.meta.url), 'utf8')),
)).join('\n');

for (const forbidden of ['service_role', 'SUPABASE_SERVICE_ROLE', 'database password']) {
  if (browserCode.includes(forbidden)) throw new Error(`Privileged credential marker in bundle: ${forbidden}`);
}
for (const name of requiredConfig) {
  if (!browserCode.includes(env[name].trim())) {
    throw new Error(`${name} is missing from the production bundle.`);
  }
}
if (!browserCode.includes('work-portal-auth')) {
  throw new Error('Shared auth storage key is missing from production bundle.');
}
