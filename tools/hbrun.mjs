#!/usr/bin/env node
// hbrun.mjs — headless-Chrome test driver for HIMMELSBRAND (CDP over Node's built-in WebSocket).
//
// Usage:
//   node tools/hbrun.mjs --root . --scenario my_test.mjs [--out D:/tmp/shots] [--w 1600 --h 900]
//                  [--swiftshader] [--timeout 180] [--page index.html]
//
// The scenario is an ES module whose default export is an async function receiving helpers:
//   export default async function({ ev, shot, sleep, log, fps, key, tap, errors, cdp }) { ... }
//     ev(expr)            -> evaluate JS in the page (awaits promises, returns JSON value)
//     shot(name)          -> PNG screenshot to <out>/<name>.png, returns the path (view it with the Read tool)
//     sleep(ms)           -> real-time wait (the game keeps running its rAF loop)
//     fps(ms=3000)        -> {fps, p50, p95, p99, max} frame times measured in-page over ms
//     key(code, down)     -> set the game's keys[code] (e.g. 'ShiftLeft','KeyW','Space')
//     tap(code, ms=80)    -> dispatch a real keydown/keyup (for handlers like KeyB, KeyX, KeyV)
//     log(...)            -> collected into the summary
//     errors()            -> exceptions + console errors so far
// Prints a JSON summary at the end: { ok, exceptions, consoleErrors, logs, shots, gpu }.
//
// Defaults: REAL GPU (ANGLE/D3D11) so frame timings mean something; audio is MUTED at the
// output (--mute-audio) but the AudioContext still runs (autoplay policy disabled).
import { spawn, spawnSync } from 'node:child_process';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { pathToFileURL } from 'node:url';

const argv = process.argv.slice(2);
const arg = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 ? (argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[i + 1] : true) : d; };
const ROOT = path.resolve(arg('root', process.cwd()));
const SCEN = arg('scenario', null);
const OUT = path.resolve(arg('out', path.join(os.tmpdir(), 'hbshots')));
const W = +arg('w', 1600), H = +arg('h', 900);
const TIMEOUT = +arg('timeout', 240) * 1000;
const PAGE = arg('page', 'index.html');
const SWIFT = !!arg('swiftshader', false);
fs.mkdirSync(OUT, { recursive: true });

const CHROME = ['C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(p => fs.existsSync(p));

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript',
  '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.css': 'text/css',
  '.m4a': 'audio/mp4', '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.ogg': 'audio/ogg', '.opus': 'audio/ogg', '.webm': 'audio/webm' };

const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]); if (p === '/') p = '/' + PAGE;
  const f = path.join(ROOT, p);
  if (!f.startsWith(ROOT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); res.end('nf'); return; }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(f).toLowerCase()] || 'application/octet-stream', 'Cache-Control': 'no-store' });
  fs.createReadStream(f).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const HTTP_PORT = server.address().port;

const userDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hbchrome-'));
const flags = ['--headless=new', `--window-size=${W},${H}`, '--remote-debugging-port=0', '--remote-allow-origins=*',
  `--user-data-dir=${userDir}`, '--no-first-run', '--no-default-browser-check', '--mute-audio',
  '--autoplay-policy=no-user-gesture-required', '--disable-background-timer-throttling',
  '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows', '--hide-scrollbars'];
if (SWIFT) flags.push('--enable-unsafe-swiftshader', '--use-gl=angle', '--use-angle=swiftshader');
else flags.push('--use-angle=d3d11', '--ignore-gpu-blocklist', '--enable-gpu-rasterization');
const chrome = spawn(CHROME, [...flags, 'about:blank'], { stdio: 'ignore' });

const summary = { ok: false, exceptions: [], consoleErrors: [], logs: [], shots: [], gpu: null };
let finished = false;
async function cleanup(code) {
  if (finished) return; finished = true;
  // Windows: killing the launcher leaves the GPU/renderer children alive (they keep rendering!) -> close + kill the tree
  try { if (typeof cdp === 'function') await Promise.race([cdp('Browser.close'), new Promise(r => setTimeout(r, 1500))]); } catch (e) { }
  try { if (process.platform === 'win32') spawnSync('taskkill', ['/PID', String(chrome.pid), '/T', '/F'], { stdio: 'ignore' }); } catch (e) { }
  try { chrome.kill(); } catch (e) { }
  try { server.close(); } catch (e) { }
  setTimeout(() => { try { fs.rmSync(userDir, { recursive: true, force: true }); } catch (e) { } }, 800);
  console.log(JSON.stringify(summary, null, 1));
  setTimeout(() => process.exit(code), 1000);
}
const hardTimer = setTimeout(() => { summary.logs.push('HARD TIMEOUT'); cleanup(2); }, TIMEOUT);

// wait for DevToolsActivePort
let dtPort = null;
for (let i = 0; i < 200 && !dtPort; i++) {
  await new Promise(r => setTimeout(r, 100));
  try { dtPort = fs.readFileSync(path.join(userDir, 'DevToolsActivePort'), 'utf8').split('\n')[0].trim(); } catch (e) { }
}
if (!dtPort) { summary.logs.push('chrome did not start'); await cleanup(3); }
let targets = [];
for (let i = 0; i < 50; i++) { try { targets = await (await fetch(`http://127.0.0.1:${dtPort}/json`)).json(); } catch (e) { } if (targets.find(t => t.type === 'page')) break; await new Promise(r => setTimeout(r, 100)); }
const tgt = targets.find(t => t.type === 'page');
const ws = new WebSocket(tgt.webSocketDebuggerUrl);
await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
let msgId = 0; const pending = new Map();
ws.onmessage = (m) => {
  const d = JSON.parse(m.data);
  if (d.id && pending.has(d.id)) { const { res, rej } = pending.get(d.id); pending.delete(d.id); d.error ? rej(new Error(JSON.stringify(d.error))) : res(d.result); return; }
  if (d.method === 'Runtime.exceptionThrown') { const e = d.params.exceptionDetails; summary.exceptions.push(((e.exception && e.exception.description) || e.text || '').slice(0, 600)); }
  if (d.method === 'Runtime.consoleAPICalled' && (d.params.type === 'error' || d.params.type === 'assert')) summary.consoleErrors.push(d.params.args.map(a => a.value ?? a.description ?? '').join(' ').slice(0, 400));
  if (d.method === 'Log.entryAdded' && d.params.entry.level === 'error') summary.consoleErrors.push(('[log] ' + d.params.entry.text + ' ' + (d.params.entry.url || '')).slice(0, 400));
};
const cdp = (method, params = {}) => new Promise((res, rej) => { const id = ++msgId; pending.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params })); });
await cdp('Runtime.enable'); await cdp('Page.enable'); await cdp('Log.enable');

const ev = async (expr) => {
  const r = await cdp('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error('eval failed: ' + ((r.exceptionDetails.exception && r.exceptionDetails.exception.description) || r.exceptionDetails.text));
  return r.result.value;
};
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const shot = async (name) => {
  const r = await cdp('Page.captureScreenshot', { format: 'png' });
  const f = path.join(OUT, name.replace(/[^\w.-]/g, '_') + '.png'); fs.writeFileSync(f, Buffer.from(r.data, 'base64'));
  summary.shots.push(f); return f;
};
const fps = async (ms = 3000) => ev(`new Promise(res=>{ const t=[]; let last=performance.now(); const t0=last;
  function f(now){ t.push(now-last); last=now; if(now-t0<${ms}) requestAnimationFrame(f); else { t.shift(); t.sort((a,b)=>a-b);
    const q=p=>+t[Math.min(t.length-1,Math.floor(p*t.length))].toFixed(2);
    res({ fps:+(1000/(t.reduce((a,b)=>a+b,0)/t.length)).toFixed(1), p50:q(0.5), p95:q(0.95), p99:q(0.99), max:+t[t.length-1].toFixed(2), n:t.length }); } }
  requestAnimationFrame(f); })`);
const key = (code, down = true) => ev(`(keys[${JSON.stringify(code)}]=${down ? 'true' : 'false'}, true)`);
const tap = async (code, ms = 80) => {
  const keyName = code.startsWith('Key') ? code.slice(3).toLowerCase() : code;
  await cdp('Input.dispatchKeyEvent', { type: 'keyDown', code, key: keyName });
  await sleep(ms); await cdp('Input.dispatchKeyEvent', { type: 'keyUp', code, key: keyName });
};
const log = (...a) => summary.logs.push(a.map(x => typeof x === 'string' ? x : JSON.stringify(x)).join(' '));
const errors = () => ({ exceptions: summary.exceptions.slice(), consoleErrors: summary.consoleErrors.slice() });

try {
  await cdp('Page.navigate', { url: `http://127.0.0.1:${HTTP_PORT}/${PAGE}` });
  for (let i = 0; i < 300; i++) { await sleep(100); try { if (await ev(`typeof launchMission==='function' && document.readyState==='complete'`)) break; } catch (e) { } }
  await sleep(600);
  try { summary.gpu = await ev(`(()=>{ const gl=renderer.getContext(); const e=gl.getExtension('WEBGL_debug_renderer_info'); return e?gl.getParameter(e.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER); })()`); } catch (e) { }
  if (SCEN) {
    const mod = await import(pathToFileURL(path.resolve(SCEN)).href);
    await mod.default({ ev, shot, sleep, log, fps, key, tap, errors, cdp });
  }
  summary.ok = summary.exceptions.length === 0;
} catch (e) {
  summary.logs.push('SCENARIO ERROR: ' + (e && e.stack || e));
}
clearTimeout(hardTimer);
await cleanup(summary.ok ? 0 : 1);
