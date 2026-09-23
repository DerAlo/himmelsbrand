#!/usr/bin/env node
// jsgate.mjs — syntax gate: extracts every inline <script> (no src) from the page and runs `node --check` on it.
// Usage: node jsgate.mjs [path/to/index.html]   -> exit 0 = all inline scripts parse
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
const F = path.resolve(process.argv[2] || 'index.html');
const html = fs.readFileSync(F, 'utf8');
const re = /<script(\s[^>]*)?>([\s\S]*?)<\/script>/gi;
let m, n = 0, bad = 0;
while ((m = re.exec(html))) {
  const attrs = m[1] || '';
  if (/\ssrc\s*=/.test(attrs)) continue;
  n++;
  const tmp = path.join(os.tmpdir(), `jsgate_${process.pid}_${n}.js`);
  fs.writeFileSync(tmp, m[2]);
  const r = spawnSync(process.execPath, ['--check', tmp], { encoding: 'utf8' });
  if (r.status !== 0) { bad++; console.log(`inline script #${n} FAILED:\n` + (r.stderr || r.stdout)); }
  try { fs.unlinkSync(tmp); } catch (e) { }
}
// sibling .js files next to the page (e.g. voice_clips.js) — check the small ones fully, big data files only head/tail shape
for (const f of fs.readdirSync(path.dirname(F))) {
  if (!f.endsWith('.js')) continue;
  const p = path.join(path.dirname(F), f);
  const r = spawnSync(process.execPath, ['--check', p], { encoding: 'utf8' });
  if (r.status !== 0) { bad++; console.log(`${f} FAILED:\n` + (r.stderr || r.stdout).slice(0, 1500)); }
}
console.log(bad ? `JSGATE FAIL (${bad})` : `JSGATE OK (${n} inline scripts)`);
process.exit(bad ? 1 : 0);
