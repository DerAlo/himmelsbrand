"""Fetch/build the zero-shot cloning reference clips that casting.json points at.
All references are CC0 or come from permissively-licensed (MIT) TTS model output - see README.md.

Two groups:
  1. refs/thorsten/*.wav   - real human speech, cut from the CC0 Thorsten-Voice emotional
                             recordings (Thorsten-Voice/TV-44kHz-Full, subset TV-2021.06-Emotional,
                             https://huggingface.co/datasets/Thorsten-Voice/TV-44kHz-Full, CC0).
  2. refs/piper/*.wav      - synthetic references, generated locally with Piper voices that are
                             themselves MIT-licensed models (no real-person recording is reused here
                             beyond what those MIT-licensed voices already ship with).

Run once (or with --force to rebuild): needs the 'cbx' venv (soundfile) for group 1, and a working
Piper install under $TTS_BAKE/piper (see setup.ps1 -Only piper) for group 2.
"""
import os, sys, argparse

BAKE = os.environ.get('TTS_BAKE', 'D:/tts-bake')
os.environ.setdefault('HF_HOME', BAKE + '/hf')

THORSTEN_STYLES = ['angry', 'amused', 'sleepy', 'whisper', 'disgusted']

PIPER_REFS = {
    # voice -> (out name, sentence read aloud to capture that model's timbre as a cloning prompt)
    'de_DE-kerstin-low': ('kerstin', 'Guten Tag, hier spricht die Flugleitung, bitte kommen Sie herein.'),
    'de_DE-eva_k-x_low': ('eva_k', 'Ich bin gleich bei dir, halt kurz die Höhe und warte auf mein Zeichen.'),
    'de_DE-ramona-low': ('ramona', 'Es war ein ruhiger Morgen über den Bergen, als die Maschinen zum ersten Mal starteten.'),
    'de_DE-karlsson-low': ('karlsson', 'Na servus, des wird heut bestimmt wieder a lustiger Flug, oder?'),
}


def fetch_thorsten(force):
    out = os.path.join(BAKE, 'refs', 'thorsten')
    os.makedirs(out, exist_ok=True)
    have = {s: os.path.exists(os.path.join(out, f'thorsten_{s}.wav')) for s in THORSTEN_STYLES}
    if all(have.values()) and not force:
        print('thorsten refs: all present, skipping (--force to rebuild)')
        return
    from huggingface_hub import hf_hub_download
    import pyarrow.parquet as pq
    print('downloading Thorsten-Voice/TV-44kHz-Full (Emotional subset) ...')
    src = hf_hub_download(repo_id='Thorsten-Voice/TV-44kHz-Full', repo_type='dataset',
                           filename='TV-2021.06-Emotional/train-00000-of-00002.parquet',
                           cache_dir=BAKE + '/hf')
    rows = pq.read_table(src).to_pylist()
    want = {s: None for s in THORSTEN_STYLES}
    for r in rows:
        style = (r.get('style') or '').split('|')[0].strip().lower()
        dur = r.get('durationSeconds') or 0
        if style in want and want[style] is None and 3.0 <= dur <= 7.0:
            want[style] = r
    for style, r in want.items():
        if not r:
            print('MISSING style', style, '(pick a different duration window / row)')
            continue
        p = os.path.join(out, f'thorsten_{style}.wav')
        open(p, 'wb').write(r['audio']['bytes'])
        print(style, '->', p, round(r['durationSeconds'], 1), 's :', r['text'][:60])


def fetch_piper(force):
    out = os.path.join(BAKE, 'refs', 'piper')
    os.makedirs(out, exist_ok=True)
    piper_bin = os.path.join(BAKE, 'piper', 'bin', 'piper.exe')
    voices_dir = os.path.join(BAKE, 'piper', 'voices')
    if not os.path.exists(piper_bin):
        print('ERROR: piper.exe missing at', piper_bin, '- run setup.ps1 -Only piper first', file=sys.stderr)
        return
    import subprocess
    for voice, (name, sentence) in PIPER_REFS.items():
        dest = os.path.join(out, f'{name}.wav')
        if os.path.exists(dest) and not force:
            print(name, 'already present, skipping'); continue
        model = os.path.join(voices_dir, voice + '.onnx')
        if not os.path.exists(model):
            print('MISSING piper voice', model, '- run setup.ps1 -Only piper', file=sys.stderr)
            continue
        p = subprocess.run([piper_bin, '--model', model, '--output_file', dest],
                            input=sentence.encode('utf-8'), capture_output=True)
        if p.returncode != 0:
            print('piper FAILED', name, p.stderr.decode('utf-8', 'ignore')[-400:], file=sys.stderr)
        else:
            print(name, '->', dest)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--only', choices=['thorsten', 'piper'], default=None)
    a = ap.parse_args()
    if a.only in (None, 'thorsten'):
        fetch_thorsten(a.force)
    if a.only in (None, 'piper'):
        fetch_piper(a.force)
