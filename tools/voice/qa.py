"""Quality checks for synthesized lines: Whisper WER/CER, UTMOS naturalness, ECAPA speaker similarity,
F0 expressiveness, speech rate and signal sanity. Runs in the `eval` venv; models load lazily, once."""
import os, re, math, unicodedata
import numpy as np

BAKE = os.environ.get('TTS_BAKE', 'D:/tts-bake')
for k, v in (('HF_HOME', BAKE + '/hf'), ('TORCH_HOME', BAKE + '/cache/torch'), ('TMP', BAKE + '/tmp'), ('TEMP', BAKE + '/tmp')):
    os.environ.setdefault(k, v)

_whisper = _mos = _spk = None
_DEV = None


def dev():
    global _DEV
    if _DEV is None:
        import torch
        _DEV = 'cuda' if torch.cuda.is_available() else 'cpu'
    return _DEV


def load(path, sr=None):
    import soundfile as sf
    x, r = sf.read(path, dtype='float32', always_2d=True)
    x = x.mean(axis=1)
    if sr and r != sr:
        import librosa
        x = librosa.resample(x, orig_sr=r, target_sr=sr); r = sr
    return x, r


# ---------------------------------------------------------------- text normalisation for WER
_NUM = {0: 'null', 1: 'eins', 2: 'zwei', 3: 'drei', 4: 'vier', 5: 'fünf', 6: 'sechs', 7: 'sieben', 8: 'acht', 9: 'neun', 10: 'zehn',
        11: 'elf', 12: 'zwölf', 13: 'dreizehn', 14: 'vierzehn', 15: 'fünfzehn', 16: 'sechzehn', 17: 'siebzehn', 18: 'achtzehn',
        19: 'neunzehn', 20: 'zwanzig', 30: 'dreißig', 40: 'vierzig', 50: 'fünfzig', 60: 'sechzig', 70: 'siebzig', 80: 'achtzig', 90: 'neunzig', 100: 'hundert'}


def _num(m):
    n = int(m.group(0))
    if n in _NUM: return ' ' + _NUM[n] + ' '
    if n < 100:
        u, t = n % 10, n - n % 10
        return ' ' + ('ein' if u == 1 else _NUM[u]) + 'und' + _NUM[t] + ' '
    return ' ' + m.group(0) + ' '


def norm_text(s):
    s = unicodedata.normalize('NFC', s).lower()
    s = re.sub(r'\d+', _num, s)
    s = s.replace('ß', 'ss')
    s = re.sub(r"[^\w\säöü]", ' ', s)
    s = s.replace('_', ' ')
    return re.sub(r'\s+', ' ', s).strip()


def wer_cer(ref, hyp):
    import jiwer
    r, h = norm_text(ref), norm_text(hyp)
    if not r: return 0.0, 0.0
    if not h: return 1.0, 1.0
    return float(jiwer.wer(r, h)), float(jiwer.cer(r, h))


# ---------------------------------------------------------------- models
def whisper():
    global _whisper
    if _whisper is None:
        import torch  # noqa: F401  (loads the CUDA runtime DLLs ctranslate2 needs on Windows)
        from faster_whisper import WhisperModel
        _whisper = WhisperModel('large-v3', device=dev(), compute_type='float16' if dev() == 'cuda' else 'int8',
                                download_root=BAKE + '/models/whisper')
    return _whisper


def transcribe(x16):
    segs, _ = whisper().transcribe(x16, language='de', beam_size=5, condition_on_previous_text=False,
                                   without_timestamps=True, vad_filter=False, temperature=0.0)
    return ' '.join(s.text.strip() for s in segs).strip()


def mos_model():
    global _mos
    if _mos is None:
        import torch
        _mos = torch.hub.load('tarepan/SpeechMOS:v1.2.0', 'utmos22_strong', trust_repo=True).to(dev()).eval()
    return _mos


def mos(x16):
    import torch
    with torch.no_grad():
        t = torch.from_numpy(x16[None, :].copy()).to(dev())
        return float(mos_model()(t, 16000).item())


def spk_model():
    global _spk
    if _spk is None:
        from speechbrain.inference.speaker import EncoderClassifier
        _spk = EncoderClassifier.from_hparams('speechbrain/spkrec-ecapa-voxceleb', savedir=BAKE + '/models/ecapa',
                                              run_opts={'device': dev()})
    return _spk


def embed(x16):
    import torch
    with torch.no_grad():
        e = spk_model().encode_batch(torch.from_numpy(x16[None, :].copy()).to(dev()))
    e = e.squeeze().cpu().numpy().astype(np.float64)
    return e / (np.linalg.norm(e) + 1e-9)


_emb_cache = {}


def ref_embed(path):
    if path not in _emb_cache:
        x, _ = load(path, 16000)
        _emb_cache[path] = embed(x)
    return _emb_cache[path]


# ---------------------------------------------------------------- signal features
def voiced_bounds(x, sr, thr_db=-42):
    """first/last sample above thr relative to peak (20 ms frames)"""
    f = max(1, int(sr * 0.02))
    n = len(x) // f
    if n == 0: return 0, len(x)
    e = np.sqrt((x[:n * f].reshape(n, f) ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(e / (e.max() + 1e-12))
    idx = np.where(db > thr_db)[0]
    if not len(idx): return 0, 0
    return idx[0] * f, min(len(x), (idx[-1] + 1) * f)


def max_gap(x, sr, thr_db=-40):
    f = max(1, int(sr * 0.02)); n = len(x) // f
    if n == 0: return 0.0
    e = np.sqrt((x[:n * f].reshape(n, f) ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(e / (e.max() + 1e-12))
    a, b = voiced_bounds(x, sr)
    quiet = db[a // f:b // f] < thr_db
    best = cur = 0
    for q in quiet:
        cur = cur + 1 if q else 0; best = max(best, cur)
    return best * 0.02


def f0_stats(x16):
    import librosa
    f0, vflag, _ = librosa.pyin(x16, fmin=55, fmax=600, sr=16000, frame_length=1024, hop_length=320)
    f = f0[vflag & ~np.isnan(f0)]
    if len(f) < 10: return {'f0_med': 0.0, 'f0_st': 0.0, 'f0_range': 0.0, 'voiced': float(len(f)) / max(1, len(f0))}
    st = 12 * np.log2(f / np.median(f))
    return {'f0_med': float(np.median(f)), 'f0_st': float(np.std(st)), 'f0_range': float(np.percentile(st, 95) - np.percentile(st, 5)),
            'voiced': float(len(f)) / max(1, len(f0))}


def syllables(text):
    t = norm_text(text)
    return max(1, len(re.findall(r'[aeiouyäöü]+', t)))


def expected_dur(text):
    """rough duration model for German radio speech (s)"""
    syl = syllables(text)
    pauses = len(re.findall(r'[.!?…—–]', text)) * 0.25 + len(re.findall(r'[,;:]', text)) * 0.12
    return syl / 5.2 + pauses


def analyse(path, say, ref_wav=None, want_f0=True, want_mos=True):
    x, sr = load(path)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    clip = float(np.mean(np.abs(x) > 0.995)) if len(x) else 0.0
    a, b = voiced_bounds(x, sr)
    dur = len(x) / sr
    speech = max(0.0, (b - a) / sr)
    x16, _ = load(path, 16000)
    r = {'dur': round(dur, 3), 'speech': round(speech, 3), 'peak': round(peak, 3), 'clip': round(clip, 5),
         'lead': round(a / sr, 3), 'trail': round(dur - b / sr, 3), 'gap': round(max_gap(x, sr), 3)}
    exp = expected_dur(say)
    r['dur_ratio'] = round(speech / exp, 3) if exp > 0 else 1.0
    r['rate'] = round(syllables(say) / max(0.3, speech), 2)
    hyp = transcribe(x16[a * 16000 // sr: b * 16000 // sr] if b > a else x16)
    r['asr'] = hyp
    r['wer'], r['cer'] = [round(v, 3) for v in wer_cer(say, hyp)]
    if want_mos and speech > 0.3: r['mos'] = round(mos(x16), 3)
    if ref_wav and speech > 0.3:
        r['sim'] = round(float(np.dot(embed(x16), ref_embed(ref_wav))), 3)
    if want_f0 and speech > 0.3: r.update({k: round(v, 3) for k, v in f0_stats(x16).items()})
    return r


def score(r, lax=False):
    """single number to rank candidates of the same line (higher = better); lax for dialect speakers"""
    s = r.get('mos', 3.0)
    s -= (0.6 if lax else 1.6) * min(1.0, r.get('cer', 1.0)) * 2.5
    s += 1.5 * (r.get('sim', 0.5) - 0.5) if 'sim' in r else 0
    dr = r.get('dur_ratio', 1.0)
    if dr > 1.9 or dr < 0.45: s -= 1.5
    if r.get('gap', 0) > 1.2: s -= 0.8
    if r.get('clip', 0) > 0.002: s -= 0.5
    if r.get('speech', 0) < 0.3: s -= 5
    return round(s, 3)


def bad(r, lax=False):
    """hard failure -> regenerate with another seed"""
    reasons = []
    if r.get('speech', 0) < 0.25: reasons.append('silent')
    if r.get('cer', 1) > (0.45 if lax else 0.2): reasons.append('cer %.2f' % r.get('cer', 1))
    dr = r.get('dur_ratio', 1)
    if dr > 2.1 or dr < 0.4: reasons.append('dur %.2f' % dr)
    if r.get('gap', 0) > 1.5: reasons.append('gap %.1fs' % r['gap'])
    if r.get('mos', 3) < 2.2: reasons.append('mos %.2f' % r.get('mos', 0))
    return reasons
