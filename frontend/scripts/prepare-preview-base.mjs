import { cp, mkdir } from 'node:fs/promises';
import path from 'node:path';

const basePath = process.env.VITE_APP_BASE_PATH;

if (!basePath || basePath === '/') {
  process.exit(0);
}

const normalizedBase = basePath.replace(/^\/+|\/+$/g, '');
const distRoot = path.resolve('dist');
const sourceAssets = path.join(distRoot, 'assets');
const targetAssets = path.join(distRoot, normalizedBase, 'assets');

await mkdir(path.dirname(targetAssets), { recursive: true });
await cp(sourceAssets, targetAssets, { recursive: true });

console.log(`Prepared Vite preview assets for /${normalizedBase}/`);
