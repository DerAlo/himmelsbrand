"""Fetch/build the zero-shot cloning reference clips that casting.json points at.
References are CC0 / public domain, permissively-licensed (MIT) TTS model output, or - for the two
Bavarian voices - CC BY / CC BY-SA Wikimedia Commons audio (attribution required); see README.md
"Credits / Lizenzen".

Four groups:
  1. refs/thorsten/*.wav   - real human speech, cut from the CC0 Thorsten-Voice emotional
                             recordings (Thorsten-Voice/TV-44kHz-Full, subset TV-2021.06-Emotional,
                             https://huggingface.co/datasets/Thorsten-Voice/TV-44kHz-Full, CC0).
  2. refs/piper/*.wav      - synthetic references, generated locally with Piper voices that are
                             themselves MIT-licensed models (no real-person recording is reused here
                             beyond what those MIT-licensed voices already ship with).
  3. refs/librivox/*.wav   - real human speech, 9-13 s cut from public-domain LibriVox recordings
                             (archive.org, licence: public domain). One distinct reader per main male
                             character so WAGNER/SEPP/KELLER no longer clone the same man. Exact file,
                             offset and length below -> byte-identical rebuild (needs ffmpeg + curl).
  4. refs/bavarian/*.wav    - real Bavarian dialect speech (Wikimedia Commons, CC BY 3.0 / CC BY-SA 4.0)
                             for SEPP and WIGGERL, cut the same way as group 3.

Run once (or with --force to rebuild): needs the 'cbx' venv (soundfile) for group 1, and a working
Piper install under $TTS_BAKE/piper (see setup.ps1 -Only piper) for group 2.
"""
import os, sys, argparse, subprocess

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

LV = 'https://www.archive.org/download/'
# out name -> (LibriVox 64 kbps MP3, start s, length s, reader, work, used for). Credits: README.md "Credits / Lizenzen".
LIBRIVOX_REFS = {
    'fritzsavira': (LV + 'andersensmarchenerganzungsband_2404_librivox/andersensmaerchenergaenzungsband_32_andersen_64kb.mp3',
                    128.12, 9.46, 'FritzSavira', 'H. C. Andersen: Die Dryade', 'WAGNER'),
    'marham63':    (LV + 'schriften_liebermann_1811_librivox/schriften_05_liebermann_64kb.mp3',
                    240.98, 9.68, 'marham63', 'Max Liebermann: Zwei Holzschnitte von Manet', 'SEPP'),
    'alkadi':      (LV + 'sammlung_karl_may_1010_librivox/karlmay_11_deroelprinz_alkadi_64kb.mp3',
                    93.90, 10.84, 'Christian Al-Kadi', 'Karl May: Der Ölprinz', 'KELLER'),
    'boris':       (LV + 'don_quixote_band_1_1805_librivox/donquixote1_17_cervantes_64kb.mp3',
                    48.36, 9.72, 'Boris', 'Cervantes: Don Quixote, Band 1, Abschnitt 17', 'archetype officer_m'),
    'carsten':     (LV + 'sammlung_kurzer_deutscher_prosa_060_2311_librivox/sammlungprosa060_04_gelbekater_cm_64kb.mp3',
                    148.36, 11.18, 'Carsten', 'Sammlung kurzer deutscher Prosa 060: Der gelbe Kater', 'archetype old_bavarian_m'),
}


WM = 'https://upload.wikimedia.org/wikipedia/commons/'
# out name -> (Wikimedia-Commons-Datei, start s, length s, speaker, work, licence, used for). Echtes Bairisch statt
# Hochdeutsch-Leser. Credits: README.md "Credits / Lizenzen" (CC BY / CC BY-SA -> Namensnennung Pflicht).
COMMONS_REFS = {
    'sebastian': (WM + '4/42/Bavarian_%28Wikitongues%29.ogg', 0.22, 10.57, 'Sebastian (Wikitongues)',
                  'WIKITONGUES: Sebastian speaking Bavarian (Rosenheim)', 'CC BY 3.0', 'WIGGERL'),
    'keglbua':   (WM + '5/5c/Keglbua.ogg', 48.59, 11.48, 'Dawaiamoi',
                  'Gesprochene Boarische Wikipedia: „Keglbua“', 'CC BY-SA 4.0', 'SEPP'),
}
UA = 'himmelsbrand-voice-bake/1.0 (make_refs.py)'   # Wikimedia blockt anonyme curl-Default-UAs mit 429/403


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


def fetch_librivox(force):
    out = os.path.join(BAKE, 'refs', 'librivox')
    src_dir = os.path.join(BAKE, 'refs', 'src', 'librivox')
    os.makedirs(out, exist_ok=True); os.makedirs(src_dir, exist_ok=True)
    for name, (url, start, dur, reader, work, role) in LIBRIVOX_REFS.items():
        dest = os.path.join(out, f'{name}.wav')
        if os.path.exists(dest) and not force:
            print(name, 'already present, skipping'); continue
        # only the head of the MP3 is needed (64 kbps CBR = 8000 B/s); keep it for reproducible re-cuts
        mp3 = os.path.join(src_dir, f'{name}.mp3')
        need = int((start + dur) * 8000) + 200000
        if not os.path.exists(mp3) or os.path.getsize(mp3) < need:
            p = subprocess.run(['curl', '-s', '-L', '--fail', '--max-time', '300', '-r', f'0-{need}', url, '-o', mp3])
            if p.returncode != 0:
                print('download FAILED', name, url, file=sys.stderr); continue
        # clean prompt: rumble highpass, 30/50 ms fades, loudness -20 LUFS, mono 24 kHz
        af = f'highpass=f=60,afade=t=in:d=0.03,afade=t=out:st={dur - 0.05:.3f}:d=0.05,loudnorm=I=-20:TP=-2:LRA=11'
        p = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{start:.3f}', '-t', f'{dur:.3f}', '-i', mp3,
                            '-af', af, '-ac', '1', '-ar', '24000', dest], capture_output=True)
        if p.returncode != 0:
            print('ffmpeg FAILED', name, p.stderr.decode('utf-8', 'ignore')[-300:], file=sys.stderr)
        else:
            print(f'{name} -> {dest} ({dur:.1f} s, {reader}, {role})')


def fetch_commons(force):
    out = os.path.join(BAKE, 'refs', 'bavarian')
    src_dir = os.path.join(BAKE, 'refs', 'src', 'bavarian')
    os.makedirs(out, exist_ok=True); os.makedirs(src_dir, exist_ok=True)
    for name, (url, start, dur, who, work, lic, role) in COMMONS_REFS.items():
        dest = os.path.join(out, f'{name}.wav')
        if os.path.exists(dest) and not force:
            print(name, 'already present, skipping'); continue
        src = os.path.join(src_dir, name + os.path.splitext(url)[1])
        if not os.path.exists(src):
            p = subprocess.run(['curl', '-s', '-L', '--fail', '--retry', '4', '--retry-delay', '5', '--max-time', '300',
                                '-A', UA, url, '-o', src])
            if p.returncode != 0:
                print('download FAILED', name, url, file=sys.stderr); continue
        af = f'highpass=f=60,afade=t=in:d=0.03,afade=t=out:st={dur - 0.05:.3f}:d=0.05,loudnorm=I=-20:TP=-2:LRA=11'
        p = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{start:.3f}', '-t', f'{dur:.3f}', '-i', src,
                            '-af', af, '-ac', '1', '-ar', '24000', dest], capture_output=True)
        if p.returncode != 0:
            print('ffmpeg FAILED', name, p.stderr.decode('utf-8', 'ignore')[-300:], file=sys.stderr)
        else:
            print(f'{name} -> {dest} ({dur:.1f} s, {who}, {lic}, {role})')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--only', choices=['thorsten', 'piper', 'librivox', 'commons'], default=None)
    a = ap.parse_args()
    if a.only in (None, 'thorsten'):
        fetch_thorsten(a.force)
    if a.only in (None, 'piper'):
        fetch_piper(a.force)
    if a.only in (None, 'librivox'):
        fetch_librivox(a.force)
    if a.only in (None, 'commons'):
        fetch_commons(a.force)
