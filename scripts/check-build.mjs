import { readFile, readdir } from 'node:fs/promises';

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
if (!browserCode.includes('work-portal-auth')) {
  throw new Error('Shared auth storage key is missing from production bundle.');
}
