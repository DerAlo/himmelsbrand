#!/usr/bin/env python
"""Bake every game line into voice_clips.js.

    D:/tts-bake/venvs/cbx/Scripts/python.exe tools/voice/bake.py [--in D:/tts-bake/lines.json]
        [--out voice_clips.js] [--only-missing] [--speakers WAGNER,SEPP] [--force] [--limit N]

Pipeline per line: resolve casting (speaker + hint mood, tools/voice/casting.json) -> generate with
the assigned engine (chatterbox: zero-shot clone from refs/*, retrying bad candidates with a new seed;
piper: local ONNX voice, single deterministic shot) -> QA each candidate (Whisper WER/CER, UTMOS, ECAPA
speaker similarity, duration sanity) via qa.py, keep the best -> loudness-normalise (~-18 LUFS, peak
-1 dBTP), trim to ~80 ms lead/trail silence, mono -> encode MP3 (ffmpeg, mono, ~48 kbps) -> cache by
(key, engine, casting-hash) under D:/tts-bake/cache/clips so a re-bake with unchanged casting/text is
instant. Writes voice_clips.js and a per-line report to D:/tts-bake/report/bake_report.json.

Must run inside the 'cbx' venv (has torch+CUDA, chatterbox, and the QA deps installed alongside it).
"""
import argparse, json, os, re, sys, glob, hashlib, base64, subprocess, time, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))  # repo root
sys.path.insert(0, HERE)
import qa  # noqa: E402

BAKE = os.environ.get('TTS_BAKE', 'D:/tts-bake')
CACHE_DIR = os.path.join(BAKE, 'cache', 'clips')
REPORT_DIR = os.path.join(BAKE, 'report')
PIPER_BIN = os.path.join(BAKE, 'piper', 'bin', 'piper.exe')
PIPER_VOICES = os.path.join(BAKE, 'piper', 'voices')
FFMPEG = 'ffmpeg'
SR_OUT = 24000
TARGET_LUFS = -18.0
PEAK_DBTP = -1.0
KEEP_SIL_MS = 80
MAX_CANDIDATES = 3


def fnv(s):
    h = 0x811c9dc5
    for b in s.encode('utf-8'):
        h ^= b
        h = (h * 0x01000193) & 0xffffffff
    return format(h, '08x')


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ---------------------------------------------------------------- casting resolution
def load_casting():
    return json.load(open(os.path.join(HERE, 'casting.json'), encoding='utf-8'))


def resolve_params(speaker, hint, casting):
    sp = casting['speakers'].get(speaker)
    if sp is None:
        sp = casting['archetypes']['officer_m']
        print(f'WARN: no casting for speaker {speaker!r}, defaulting to officer_m', file=sys.stderr)
    p = {k: v for k, v in sp.items() if not k.startswith('_')}
    p.setdefault('speed', 1.0)
    if hint:
        for h in re.split(r'[,+ ]+', hint.strip()):
            mood = casting.get('moods', {}).get(h)
            if not mood:
                continue
            for k, v in mood.items():
                if k in ('exaggeration', 'cfg_weight', 'temperature'):
                    p[k] = clamp(p.get(k, 0.5) + v, 0.0, 1.0)
                elif k == 'speed':
                    p['speed'] = p.get('speed', 1.0) * (1.0 + v)
                elif k == 'gain_db':
                    p['gain_db'] = p.get('gain_db', 0.0) + v
    return p


def casting_hash(params):
    return hashlib.sha1(json.dumps(params, sort_keys=True).encode('utf-8')).hexdigest()[:10]


# ---------------------------------------------------------------- engines
_cbx_model = None


def cbx_model():
    global _cbx_model
    if _cbx_model is None:
        os.environ.setdefault('HF_HOME', BAKE + '/hf')
        os.environ.setdefault('TORCH_HOME', BAKE + '/cache/torch')
        import torch  # noqa
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        _cbx_model = ChatterboxMultilingualTTS.from_pretrained(device='cuda' if torch.cuda.is_available() else 'cpu')
    return _cbx_model


def gen_chatterbox(say, params, seed, tmp_wav):
    import torch, torchaudio
    torch.manual_seed(seed)
    m = cbx_model()
    ref = params['ref']
    if not os.path.isabs(ref):
        ref = os.path.join(BAKE, ref)
    wav = m.generate(say, language_id='de', audio_prompt_path=ref,
                      exaggeration=params.get('exaggeration', 0.5),
                      cfg_weight=params.get('cfg_weight', 0.5),
                      temperature=params.get('temperature', 0.8))
    torchaudio.save(tmp_wav, wav, m.sr)
    return m.sr


def gen_piper(say, params, tmp_wav):
    voice = os.path.join(PIPER_VOICES, params['voice'] + '.onnx')
    args = [PIPER_BIN, '-m', voice, '-f', tmp_wav,
             '--length_scale', str(params.get('length_scale', 1.0)),
             '--sentence_silence', str(params.get('sentence_silence', 0.25))]
    p = subprocess.run(args, input=say.encode('utf-8'), capture_output=True)
    if p.returncode != 0 or not os.path.exists(tmp_wav):
        raise RuntimeError('piper failed: ' + p.stderr.decode('utf-8', 'ignore')[:300])
    import soundfile as sf
    info = sf.info(tmp_wav)
    return info.samplerate


# ---------------------------------------------------------------- post-processing
def postprocess(src_wav, params, dst_wav):
    import soundfile as sf, librosa
    x, sr = sf.read(src_wav, dtype='float32', always_2d=True)
    x = x.mean(axis=1)
    # NOTE: librosa.effects.pitch_shift/time_stretch (phase-vocoder DSP) are deliberately NOT used
    # here anymore. Measured impact on this voice: MOS 3.25 -> 1.3-1.4 for a mere 3% time-stretch or
    # a 2.5-semitone pitch-shift (see D:/tts-bake/report/bakeoff.md, "Bekannte Grenzen") - WER stays
    # fine (content survives) but it sounds audibly robotic/phasey, which tanked nearly every clip's
    # perceived quality in the first full-bake attempt. Voice differentiation (WAGNER/SEPP/KELLER
    # sharing one reference) now comes only from exaggeration/cfg_weight/temperature at generation
    # time, never from post-hoc pitch/speed DSP. 'speed' and 'pitch_semitones' in casting.json are
    # intentionally unused by this function.
    if sr != SR_OUT:
        x = librosa.resample(x, orig_sr=sr, target_sr=SR_OUT)
        sr = SR_OUT
    # trim to ~KEEP_SIL_MS lead/trail silence
    a, b = qa.voiced_bounds(x, sr)
    pad = int(sr * KEEP_SIL_MS / 1000)
    a = max(0, a - pad)
    b = min(len(x), b + pad)
    if b > a:
        x = x[a:b]
    # gentle "studio polish" for KELLER: light compression + presence bump
    if params.get('polish'):
        thr = 0.35
        over = np.abs(x) > thr
        x = np.where(over, np.sign(x) * (thr + (np.abs(x) - thr) * 0.5), x)
    # loudness normalise to TARGET_LUFS
    try:
        import pyloudnorm as pyln
        meter = pyln.Meter(sr)
        loud = meter.integrated_loudness(x)
        if np.isfinite(loud):
            x = pyln.normalize.loudness(x, loud, TARGET_LUFS)
    except Exception as e:
        print('loudnorm skipped:', e, file=sys.stderr)
    gain_db = params.get('gain_db', 0.0)
    if gain_db:
        x = x * (10 ** (gain_db / 20))
    # peak limit to PEAK_DBTP
    peak = np.max(np.abs(x)) + 1e-9
    target_peak = 10 ** (PEAK_DBTP / 20)
    if peak > target_peak:
        x = x * (target_peak / peak)
    sf.write(dst_wav, x, sr, subtype='PCM_16')
    return sr, len(x) / sr


def encode_mp3(wav_path, mp3_path, bitrate='48k'):
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', wav_path,
                     '-ac', '1', '-ar', str(SR_OUT), '-b:a', bitrate, mp3_path], check=True)


# ---------------------------------------------------------------- main bake loop
def bake_line(line, casting, force, report):
    speaker, text = line['speaker'], line['text']
    say = line.get('say') or text
    hint = line.get('hint') or ''
    key = line.get('key') or fnv(speaker + '|' + text)
    params = resolve_params(speaker, hint, casting)
    engine = params['engine']
    chash = casting_hash(params)
    cache_wav = os.path.join(CACHE_DIR, f'{key}_{engine}_{chash}.wav')
    cache_meta = os.path.join(CACHE_DIR, f'{key}_{engine}_{chash}.json')
    os.makedirs(CACHE_DIR, exist_ok=True)

    if not force and os.path.exists(cache_wav) and os.path.exists(cache_meta):
        meta = json.load(open(cache_meta, encoding='utf-8'))
        report.append(meta)
        return cache_wav, meta

    with tempfile.TemporaryDirectory() as td:
        best = None
        seed_base = int(key, 16) % 1000000
        tries = 1 if engine == 'piper' else MAX_CANDIDATES
        for i in range(tries):
            raw = os.path.join(td, f'raw{i}.wav')
            t0 = time.time()
            try:
                if engine == 'chatterbox':
                    gen_chatterbox(say, params, seed_base + i, raw)
                elif engine == 'piper':
                    gen_piper(say, params, raw)
                else:
                    raise RuntimeError('unknown engine ' + engine)
            except Exception as e:
                print(f'GEN FAIL {key} {speaker} try{i}: {e}', file=sys.stderr)
                continue
            proc = os.path.join(td, f'proc{i}.wav')
            sr, dur = postprocess(raw, params, proc)
            ref = params.get('ref')
            ref_path = (ref if not ref or os.path.isabs(ref) else os.path.join(BAKE, ref)) if ref else None
            r = qa.analyse(proc, say, ref_wav=ref_path if ref_path and os.path.exists(ref_path) else None)
            lax = params.get('lax', False)
            sc = qa.score(r, lax=lax)
            bad = qa.bad(r, lax=lax)
            cand = {'idx': i, 'proc': proc, 'r': r, 'score': sc, 'bad': bad, 'gen_s': round(time.time() - t0, 2)}
            if best is None or sc > best['score']:
                best = cand
            if not bad:
                break
        if best is None:
            print(f'ALL CANDIDATES FAILED {key} {speaker}: {say[:60]}', file=sys.stderr)
            return None, None
        os.makedirs(CACHE_DIR, exist_ok=True)
        import shutil
        shutil.copyfile(best['proc'], cache_wav)
        meta = {'key': key, 'speaker': speaker, 'text': text, 'say': say, 'hint': hint,
                 'engine': engine, 'casting_hash': chash, 'duration': best['r']['dur'],
                 'wer': best['r']['wer'], 'cer': best['r']['cer'], 'mos': best['r'].get('mos'),
                 'sim': best['r'].get('sim'), 'score': best['score'], 'bad': best['bad'],
                 'retries': best['idx'], 'gen_s': best['gen_s']}
        json.dump(meta, open(cache_meta, 'w', encoding='utf-8'), ensure_ascii=False)
        report.append(meta)
        return cache_wav, meta


VOICE_CLIPS_RE = re.compile(r'window\.VOICE_CLIPS\s*=\s*/\*CLIPS\*/(\{.*?\})/\*/CLIPS\*/;', re.S)
VOICE_DUR_RE = re.compile(r'window\.VOICE_DUR\s*=\s*/\*DUR\*/(\{.*?\})/\*/DUR\*/;', re.S)


def load_existing(out_path):
    if not os.path.exists(out_path):
        return {}, {}
    src = open(out_path, encoding='utf-8').read()
    mc = VOICE_CLIPS_RE.search(src)
    md = VOICE_DUR_RE.search(src)
    clips = json.loads(mc.group(1)) if mc else {}
    durs = json.loads(md.group(1)) if md else {}
    return clips, durs


def write_voice_clips(out_path, clips, durs):
    js = ('window.VOICE_CLIPS = /*CLIPS*/' + json.dumps(clips, ensure_ascii=False, separators=(',', ':')) +
          '/*/CLIPS*/;\n' +
          'window.VOICE_DUR = /*DUR*/' + json.dumps(durs, ensure_ascii=False, separators=(',', ':')) +
          '/*/DUR*/;\n')
    open(out_path, 'w', encoding='utf-8').write(js)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', default=os.path.join(BAKE, 'lines.json'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'voice_clips.js'))
    ap.add_argument('--only-missing', action='store_true')
    ap.add_argument('--speakers', default=None)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--limit', type=int, default=None)
    args = ap.parse_args()

    casting = load_casting()
    lines = json.load(open(args.inp, encoding='utf-8'))
    if args.speakers:
        want = set(args.speakers.split(','))
        lines = [l for l in lines if l['speaker'] in want]

    clips, durs = load_existing(args.out)
    if args.only_missing:
        before = len(lines)
        lines = [l for l in lines if fnv(l['speaker'] + '|' + l['text']) not in clips]
        print(f'only-missing: {before} -> {len(lines)} lines to bake')
    if args.limit:
        lines = lines[:args.limit]

    os.makedirs(REPORT_DIR, exist_ok=True)
    report = []
    n_ok = n_fail = 0
    t0 = time.time()
    for i, line in enumerate(lines):
        wav, meta = bake_line(line, casting, args.force, report)
        if wav is None:
            n_fail += 1
            continue
        key = meta['key']
        mp3 = os.path.join(tempfile.gettempdir(), f'{key}.mp3')
        encode_mp3(wav, mp3, '48k')
        b64 = base64.b64encode(open(mp3, 'rb').read()).decode('ascii')
        clips[key] = 'data:audio/mpeg;base64,' + b64
        durs[key] = round(meta['duration'], 2)
        os.remove(mp3)
        n_ok += 1
        tag = 'RETRY' + str(meta['retries']) if meta['retries'] else 'ok'
        print(f'[{i+1}/{len(lines)}] {meta["speaker"]:10s} {key} {tag:6s} '
              f'wer={meta["wer"]:.2f} mos={meta.get("mos", 0):.2f} dur={meta["duration"]:.2f}s '
              f'{meta["say"][:50]}')

    write_voice_clips(args.out, clips, durs)
    json.dump(report, open(os.path.join(REPORT_DIR, 'bake_report.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    total_bytes = sum(len(v) for v in clips.values())
    print(f'\nDONE: {n_ok} ok, {n_fail} failed, {len(clips)} total clips, '
          f'~{total_bytes/1e6:.1f} MB base64, {round(time.time()-t0,1)}s -> {args.out}')
    if report:
        import statistics
        mos = [r['mos'] for r in report if r.get('mos') is not None]
        wer = [r['wer'] for r in report]
        retried = sum(1 for r in report if r['retries'])
        bad = [r for r in report if r['bad']]
        print(f'avg mos={statistics.mean(mos):.2f} avg wer={statistics.mean(wer):.3f} '
              f'retried={retried} still-flagged-bad={len(bad)}')
        for r in bad:
            print('  STILL BAD:', r['key'], r['speaker'], r['bad'], r['say'][:60])


if __name__ == '__main__':
    main()
