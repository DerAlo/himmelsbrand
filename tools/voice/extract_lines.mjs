#!/usr/bin/env node
// extract_lines.mjs — collect every spoken line of the game for the voice bake.
//
//   node tools/voice/extract_lines.mjs [--root .] [--out D:/tts-bake/lines.json] [--static] [--cvo out_cvo.json]
//
// Output: JSON array [{speaker, text, say, hint, kind, key, cs?}]
//   key  = fnv-1a 32-bit over UTF-8 of speaker+'|'+text (== the game's voiceKey; hint excluded)
//   say  = what the TTS should actually speak (glitch marks stripped); the game keys on `text`
//   kind = 'radio' | 'cutscene' | whatever the game's collectVoiceLines() reports
// Modes:
//   default  : run the game headless (tools/hbrun.mjs). If the page has window.collectVoiceLines() its list
//              is used (plus anything the static scan finds that it missed); otherwise cutscene objects are
//              read from the live page and radio lines from a static scan of the source.
//   --static : no browser; cutscene objects are evaluated from the source with node:vm.
// Also writes the cutscene voice-over map (cutsceneId -> [[key, speaker], ...]) to --cvo (default next to --out)
// and checks it against the /*CVO*/ block that is currently in index.html.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import vm from 'node:vm';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const argv = process.argv.slice(2);
const arg = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 ? (argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[i + 1] : true) : d; };
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(arg('root', path.join(HERE, '..', '..')));
const OUT = path.resolve(arg('out', 'D:/tts-bake/lines.json'));
const CVO_OUT = path.resolve(arg('cvo', OUT.replace(/\.json$/i, '') + '_cvo.json'));
const STATIC = !!arg('static', false);
const SRC = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

export function fnv(s) {
  let h = 0x811c9dc5 >>> 0; const b = Buffer.from(s, 'utf8');
  for (const x of b) { h ^= x; h = Math.imul(h, 0x01000193) >>> 0; }
  return (h >>> 0).toString(16).padStart(8, '0');
}
// glitch text (combining strike-through etc.) is keyed as-is but spoken clean
export function cleanSay(t) { return String(t).normalize('NFC').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ').trim(); }
const SPK_RE = /^[A-ZÄÖÜ?][A-ZÄÖÜ?0-9_ .-]{0,23}$/;

// ---- static scan: every JS string literal that looks like 'SPEAKER|text[|hint]' ----
function scanLiterals(src) {
  const out = []; const n = src.length; let i = 0;
  const scripts = []; const sre = /<script(\s[^>]*)?>([\s\S]*?)<\/script>/gi; let m;
  while ((m = sre.exec(src))) if (!/\ssrc\s*=/.test(m[1] || '')) scripts.push(m[2]);
  for (const js of scripts) {
    i = 0; const L = js.length;
    while (i < L) {
      const c = js[i];
      if (c === '/' && js[i + 1] === '/') { const e = js.indexOf('\n', i); i = e < 0 ? L : e; continue; }
      if (c === '/' && js[i + 1] === '*') { const e = js.indexOf('*/', i + 2); i = e < 0 ? L : e + 2; continue; }
      if (c === "'" || c === '"' || c === '`') {
        let j = i + 1, s = '', tmplExpr = false;
        while (j < L && js[j] !== c) {
          if (js[j] === '\\') { const d = js[j + 1]; s += d === 'n' ? '\n' : d === 't' ? '\t' : d; j += 2; continue; }
          if (c === '`' && js[j] === '$' && js[j + 1] === '{') tmplExpr = true;
          if (c !== '`' && js[j] === '\n') break;
          s += js[j]; j++;
        }
        const next = js.slice(j + 1).match(/^\s*(\+)?/);
        const concat = !!(next && next[1]) || /\+\s*$/.test(js.slice(Math.max(0, i - 4), i));
        if (!tmplExpr && !concat && s.includes('|')) {
          const p = s.split('|');
          if (SPK_RE.test(p[0]) && p[1] && /\p{L}/u.test(p[1]) && p[0] !== 'SPEAKER') out.push({ speaker: p[0], text: p[1], hint: p.slice(2).join('|'), kind: 'radio' });
        }
        i = j + 1; continue;
      }
      i++;
    }
  }
  return out;
}
// 'SPK|a'+(cond?'b':'c')+'d' -> both variants (only fully literal ternaries; anything with runtime values stays unvoiced)
function scanTernaries(src) {
  const out = []; const q = `(?:'([^'\n]*)'|"([^"\n]*)")`;
  const re = new RegExp(q + String.raw`\s*\+\s*\(\s*[^?()'"]+\?\s*` + q + String.raw`\s*:\s*` + q + String.raw`\s*\)(?:\s*\+\s*` + q + ')?', 'g');
  let m;
  while ((m = re.exec(src))) {
    const head = m[1] ?? m[2], a = m[3] ?? m[4], b = m[5] ?? m[6], tail = m[7] ?? m[8] ?? '';
    if (/\+\s*$/.test(src.slice(Math.max(0, m.index - 4), m.index)) || /^\s*\+/.test(src.slice(re.lastIndex))) continue;
    const p = head.split('|'); if (p.length < 2 || !SPK_RE.test(p[0]) || p[0] === 'SPEAKER') continue;
    for (const v of [a, b]) { const t = (p.slice(1).join('|') + v + tail).split('|'); if (/\p{L}/u.test(t[0])) out.push({ speaker: p[0], text: t[0], hint: t.slice(1).join('|'), kind: 'radio' }); }
  }
  return out;
}

// ---- cutscene bodies -> ordered segments, replicating the original piper-studio split ----
// Paragraphs split at <br>. <span class="who">NAME:</span> sets the speaker for „quotes" in that paragraph;
// a who-span without colon is plain text. Text outside quotes is NARRATOR; adjacent narrator text runs merge.
export function segmentBody(html) {
  const segs = [];
  const paras = String(html).split(/<br\s*\/?>/i);
  for (const para of paras) {
    let spk = 'NARRATOR';
    const toks = []; const re = /<span class="who">([^<]*?):\s*<\/span>/g; let last = 0, m;
    while ((m = re.exec(para))) { toks.push({ t: 'txt', v: para.slice(last, m.index) }); toks.push({ t: 'who', v: m[1] }); last = re.lastIndex; }
    toks.push({ t: 'txt', v: para.slice(last) });
    for (const tk of toks) {
      if (tk.t === 'who') { spk = normSpeaker(tk.v); continue; }
      const txt = tk.v.replace(/<[^>]+>/g, '');
      const qre = /„([^"“]*)["“]/g; let l = 0, q;
      const push = (kind, s, v) => {
        v = v.replace(/\s+/g, ' ').trim(); if (!v) return;
        const prev = segs[segs.length - 1];
        if (kind === 'n' && prev && prev.kind === 'n') { prev.text += ' ' + v; return; }
        segs.push({ kind, speaker: s, text: v });
      };
      while ((q = qre.exec(txt))) { push('n', 'NARRATOR', txt.slice(l, q.index)); push('q', spk, q[1]); l = qre.lastIndex; }
      push('n', 'NARRATOR', txt.slice(l));
    }
  }
  return segs.map(s => ({ speaker: s.speaker, text: s.text }));
}
function normSpeaker(s) {
  s = s.replace(/\([^)]*\)/g, '').trim();
  const w = s.split(/\s+/); return w[w.length - 1].toUpperCase();
}
function cutsceneLines(objs) {
  const lines = [], cvo = {};
  for (const obj of objs) for (const id in obj) {
    const cs = obj[id];
    const bodies = cs.dynamic && cs.variants ? Object.keys(cs.variants).map(k => ['ending_' + k, cs.variants[k].body]) : [[id, cs.body]];
    for (const [vid, body] of bodies) {
      if (!body) continue;
      cvo[vid] = [];
      for (const s of segmentBody(body)) {
        const key = fnv(s.speaker + '|' + s.text);
        cvo[vid].push([key, s.speaker]);
        lines.push({ speaker: s.speaker, text: s.text, hint: '', kind: 'cutscene', cs: vid, key });
      }
    }
  }
  return { lines, cvo };
}
function staticCutsceneObjects(src) {
  const objs = [];
  for (const name of ['BTEAM_CUTSCENES', 'CUTSCENES']) {
    const at = src.indexOf('const ' + name + ' = {'); if (at < 0) continue;
    let i = src.indexOf('{', at), depth = 0, j = i, inS = null;
    for (; j < src.length; j++) {
      const c = src[j];
      if (inS) { if (c === '\\') { j++; continue; } if (c === inS) inS = null; continue; }
      if (c === "'" || c === '"' || c === '`') { inS = c; continue; }
      if (c === '{') depth++; else if (c === '}') { depth--; if (!depth) break; }
    }
    try { objs.push(vm.runInNewContext('(' + src.slice(i, j + 1) + ')', {})); } catch (e) { console.error('static eval of ' + name + ' failed: ' + e.message); }
  }
  return objs;
}

async function runtimeCollect() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'hbvoice-'));
  const res = path.join(tmp, 'res.json');
  const scen = path.join(tmp, 'collect.mjs');
  fs.writeFileSync(scen, `import fs from 'node:fs';
export default async function({ ev }) {
  const r = await ev(\`(()=>{ const o={};
    try{ o.collected = (typeof window.collectVoiceLines==='function') ? window.collectVoiceLines() : null; }catch(e){ o.err=String(e); }
    try{ o.cs = [typeof BTEAM_CUTSCENES!=='undefined'?BTEAM_CUTSCENES:{}, typeof CUTSCENES!=='undefined'?CUTSCENES:{}]; }catch(e){ o.cs=null; }
    return JSON.parse(JSON.stringify(o)); })()\`);
  fs.writeFileSync(${JSON.stringify(res)}, JSON.stringify(r));
}`);
  const hb = path.join(ROOT, 'tools', 'hbrun.mjs');
  const p = spawnSync(process.execPath, [hb, '--root', ROOT, '--scenario', scen, '--out', path.join(tmp, 'shots'), '--timeout', '120', '--w', '640', '--h', '360'], { encoding: 'utf8', maxBuffer: 1 << 26 });
  let r = null; try { r = JSON.parse(fs.readFileSync(res, 'utf8')); } catch (e) { console.error('runtime collect failed; hbrun said:\n' + (p.stdout || '').slice(-1500) + (p.stderr || '').slice(-800)); }
  try { fs.rmSync(tmp, { recursive: true, force: true }); } catch (e) { }
  return r;
}

async function main() {
  let collected = null, csObjs = null;
  if (!STATIC) { const r = await runtimeCollect(); if (r) { collected = Array.isArray(r.collected) ? r.collected : null; csObjs = r.cs; if (r.err) console.error('collectVoiceLines threw: ' + r.err); } }
  if (!csObjs) csObjs = staticCutsceneObjects(SRC);
  const cut = cutsceneLines(csObjs);
  const scanned = [...scanLiterals(SRC), ...scanTernaries(SRC)];
  let all = [];
  if (collected) {
    for (const l of collected) {
      const speaker = String(l.speaker || l.spk || 'NARRATOR'), text = String(l.text || '');
      all.push({ speaker, text, say: l.say, hint: l.hint || '', kind: l.kind || 'game', cs: l.cs, key: l.key });
    }
  }
  all.push(...scanned, ...cut.lines);
  // normalise + de-duplicate on key (first occurrence wins: the game's own list beats the scans)
  const seen = new Map();
  for (const l of all) {
    if (!l.text || !/\p{L}/u.test(l.text)) continue;
    const key = fnv(l.speaker + '|' + l.text);
    if (l.key && l.key !== key) console.error(`key mismatch for ${l.speaker}|${l.text.slice(0, 40)}: game ${l.key} vs ${key}`);
    if (seen.has(key)) { const o = seen.get(key); if (!o.hint && l.hint) o.hint = l.hint; continue; }
    const say = l.say ? cleanSay(l.say) : cleanSay(l.text);
    seen.set(key, { speaker: l.speaker, text: l.text, say, hint: l.hint || '', kind: l.kind, ...(l.cs ? { cs: l.cs } : {}), key });
  }
  const lines = [...seen.values()];
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(lines, null, 1));
  fs.writeFileSync(CVO_OUT, JSON.stringify(cut.cvo));
  // compare with the CUTSCENE_VO block the game currently ships
  const m = SRC.match(/\/\*CVO\*\/([\s\S]*?)\/\*\/CVO\*\//);
  let cvoMsg = 'no /*CVO*/ block in index.html';
  if (m) {
    const cur = JSON.parse(m[1]); const want = new Set(Object.values(cur).flat().map(x => x[0]));
    const have = new Set(lines.map(l => l.key)); const miss = [...want].filter(k => !have.has(k));
    const ids = new Set([...Object.keys(cur), ...Object.keys(cut.cvo)]);
    const same = [...ids].every(id => JSON.stringify(cur[id]) === JSON.stringify(cut.cvo[id]));
    cvoMsg = `CUTSCENE_VO in index.html: ${want.size} keys, ${miss.length} not among extracted lines${miss.length ? ' (' + miss.join(',') + ')' : ''}; map ${same ? 'identical' : 'DIFFERS (update the /*CVO*/ block from ' + CVO_OUT + ')'}`;
  }
  const bySpk = {}; for (const l of lines) bySpk[l.speaker] = (bySpk[l.speaker] || 0) + 1;
  console.error(`lines: ${lines.length} (${collected ? 'collectVoiceLines ' + collected.length + ' + ' : ''}static ${scanned.length} + cutscene ${cut.lines.length}) -> ${OUT}`);
  console.error('speakers: ' + JSON.stringify(bySpk));
  console.error(cvoMsg);
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
