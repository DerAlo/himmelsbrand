# Sprachausgabe-Pipeline (Track: TTS)

Backt jede Spielzeile offline zu einem MP3-Clip und schreibt sie nach `voice_clips.js`
(Repo-Root), das `index.html` per `<script src="voice_clips.js">` lädt. Trockene Clips ohne
Funk-FX — Rauschen/Kompression zur Laufzeit ist Sache des VOICE-Tracks.

## Das eine Kommando

```powershell
# einmalig, danach nur bei neuen/entfernten Sprechern/Voices nötig
powershell -ExecutionPolicy Bypass -File tools/voice/setup.ps1 -Only cbx,piper
D:/tts-bake/venvs/cbx/Scripts/python.exe tools/voice/make_refs.py     # Referenzstimmen holen/bauen

# Zeilen aus index.html extrahieren (Node, kein Python-venv nötig)
node tools/voice/extract_lines.mjs > D:/tts-bake/lines.json

# backen (Cache macht Re-Runs schnell: nur neue/geänderte Zeilen werden generiert)
D:/tts-bake/venvs/cbx/Scripts/python.exe tools/voice/bake.py
```

Das war's — `voice_clips.js` im Repo-Root ist danach aktuell. Für einen schnellen Re-Bake nach der
Story-Merge (nur neue Zeilen, alte bleiben aus dem Cache):

```powershell
D:/tts-bake/venvs/cbx/Scripts/python.exe tools/voice/bake.py --only-missing
```

Nützliche Flags: `--speakers WAGNER,SEPP` (nur bestimmte Sprecher), `--force` (Cache ignorieren,
z. B. nach einer Casting-Änderung — der Cache-Key enthält ohnehin einen Hash der Casting-Parameter,
daher invalidiert sich das meiste automatisch), `--limit N` (Smoke-Test), `--in`/`--out` (andere
Pfade).

## Wie es funktioniert

1. **`extract_lines.mjs`** liest `index.html` (nur lesend!) und findet jede Sprecherzeile —
   statische String-Literale wie `SPEAK('WAGNER', "...", "hinweis")` und die Cutscene-Segmente
   (`'SPRECHER|Text|Hinweis'`-Format, siehe `df3c318`). Schreibt eine flache Liste
   `{speaker, text, say, hint, key}` nach `lines.json`. `key` ist FNV-1a(32) von
   `speaker + "|" + text` (Hinweis zählt nicht mit) — **muss** mit dem `voiceKey`, das das Spiel
   selbst berechnet, übereinstimmen, sonst findet die Laufzeit den Clip nicht.
2. **`casting.json`** ordnet jedem Sprecher eine Engine + Stimme + Basisparameter zu, plus
   Mood-Deltas (aus dem Sprechhinweis-Vokabular, z. B. "wuetend", "fluestern") und generische
   Archetypen für Sprecher, die noch nicht namentlich erfasst sind.
3. **`bake.py`** generiert pro Zeile bis zu 3 Kandidaten (Chatterbox) bzw. 1 (Piper, deterministisch),
   lässt jeden durch `qa.py` laufen (WER/CER, MOS, Sprecherähnlichkeit, F0, Lautstärke/Clipping/
   Stille-Sanity) und nimmt den besten. Danach: Mono-Downmix, optionaler Pitch-Shift/Zeit-Stretch,
   Stille am Anfang/Ende auf ~80 ms getrimmt, Loudness-Normalisierung auf -18 LUFS / Peak -1 dBTP,
   MP3-Encode (mono, ~48 kbps via ffmpeg). Cache-Key: `{key}_{engine}_{casting-hash}` unter
   `D:/tts-bake/cache/clips/` — ein Re-Bake generiert nur, was sich wirklich geändert hat.
4. **`voice_clips.js`** wird mit exakt erhaltenen `/*CLIPS*/…/*/CLIPS*/`- und
   `/*DUR*/…/*/DUR*/`-Markern geschrieben (regex-basiertes Merge), damit `--only-missing` bestehende
   Einträge nicht anfasst.

## Engines & Lizenzen

| Engine | Lizenz | Verwendet für |
|---|---|---|
| Chatterbox Multilingual TTS | MIT | alle menschlichen/klonbaren Sprecher (WAGNER, LÄRCHE, SEPP, WIGGERL, NARRATOR, KELLER, KIEBITZ, "?") |
| Piper (ONNX-Voices) | MIT | HELIOS, STIMME (bewusst synthetisch/nicht-menschlich) |
| XTTS-v2 | Coqui Public Model License (nicht-kommerziell) | **nicht verwendet** — siehe `report/bakeoff.md` |
| F5-TTS + `aihpi/F5-TTS-German` | Basis-Code MIT, Fine-tune-Checkpoint CC-BY-NC-4.0 | **nicht verwendet** — siehe `report/bakeoff.md` |
| Qwen3-TTS | Apache-2.0 | in `setup.ps1` vorbereitet, nicht mehr getestet — nicht verwendet |

Volle Begründung, Metriken (WER/CER/MOS/Sprecherähnlichkeit) und Vergleichstabelle:
**`D:/tts-bake/report/bakeoff.md`**.

## Referenzstimmen (Zero-Shot-Klon-Prompts) — Herkunft & Lizenz

Siehe `tools/voice/make_refs.py` (reproduzierbarer Fetch/Build) und `report/bakeoff.md` fürs Detail.
Kurzfassung:

- `refs/thorsten/*.wav` — echte menschliche Aufnahmen aus dem **CC0**-Datensatz
  `Thorsten-Voice/TV-44kHz-Full` (Subset `TV-2021.06-Emotional`) auf HuggingFace.
- `refs/piper/*.wav` — selbst generiert, indem MIT-lizenzierte Piper-Stimmen
  (`rhasspy/piper-voices`) einen kurzen Satz vorlesen. Keine zusätzliche Aufnahme einer realen
  Person; die Ausgabe eines bereits permissiv lizenzierten Modells wird hier als Klon-Prompt
  wiederverwendet.

Beide Quellen sind damit für ein potenziell kommerzielles Spiel unbedenklich.

## Casting (`casting.json`)

Pro Sprecher: `engine`, Referenz/Stimme, Basisparameter (`exaggeration`, `cfg_weight`,
`temperature`, `speed`, optional `pitch_semitones`, `polish`, `lax`). `moods` sind Deltas,
die anhand des Sprechhinweis-Textes (z. B. "(wütend)") automatisch angewendet werden — siehe
`resolve_params()` in `bake.py`. `archetypes` sind Fallback-Presets (officer_f/m, boss_ai,
boss_pilot_m, old_bavarian_m, young_m/f, narrator) für Sprecher, die noch keinen eigenen Eintrag
haben; ein unbekannter Sprecher fällt automatisch auf `narrator` zurück (siehe `resolve_params()`).

`lax: true` lockert die WER/CER-Härtetests in `qa.py` für Dialektsprecher (Whisper transkribiert
bayrische Wörter oft als das nächste Hochdeutsch-Wort — das ist ein ASR-Artefakt, keine
Aussprachefehler; CER bleibt der verlässlichere Indikator, siehe `bakeoff.md`).

**Neue Sprecher KELLER und KIEBITZ** (aus `narrative_design.md`) sind bereits gecastet. Jeder
weitere neue Sprecher braucht keinen eigenen Eintrag — er fällt auf den `narrator`-Archetyp zurück
und produziert trotzdem einen brauchbaren Clip; ein passender casting.json-Eintrag verbessert die
Stimme aber gezielt.

## Setup von Grund auf

```powershell
powershell -ExecutionPolicy Bypass -File tools/voice/setup.ps1 -Only cbx,piper
```

Baut die `cbx`-Venv (Python 3.11: Chatterbox + kompletter QA-Stack in einem Prozess — das ist die
einzige Venv, die `bake.py` tatsächlich braucht) und holt Piper (Binary von GitHub Releases,
Stimmen von `rhasspy/piper-voices` auf HuggingFace). `-Only eval,qwen,f5` baut zusätzlich die
Venvs, die nur für die Bake-off-Exploration in `report/bakeoff.md` gebraucht wurden — für einen
normalen Re-Bake nicht nötig.

`tools/voice/make_refs.py` holt danach den CC0-Datensatz und generiert die Piper-Referenzen (siehe
oben); beides ist idempotent (`--force` zum Neubauen).

## Dateien in diesem Ordner

- `casting.json` — Sprecher/Mood/Archetyp-Konfiguration (siehe oben).
- `bake.py` — die Pipeline (Generierung, QA, Post-Processing, Encode, `voice_clips.js`-Schreiben).
- `qa.py` — Qualitätsmetriken (WER/CER, MOS, Sprecherähnlichkeit, F0, Sanity-Checks, Scoring).
- `extract_lines.mjs` — Zeilen aus `index.html` extrahieren (read-only).
- `make_refs.py` — Referenzstimmen reproduzierbar holen/bauen.

Alles Schwere (Venvs, Modelle, Caches, Referenzaudio, Reports) liegt außerhalb des Repos unter
`D:/tts-bake/` (Pfad überschreibbar via `$env:TTS_BAKE`).
