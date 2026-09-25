# Sprachausgabe-Pipeline (Track: TTS)

Backt jede Spielzeile offline zu einem MP3-Clip und schreibt sie nach `voice_clips.js`
(Repo-Root), das `index.html` per `<script src="voice_clips.js">` lädt. Trockene Clips ohne
Funk-FX — Rauschen/Kompression zur Laufzeit ist Sache des VOICE-Tracks.

## Das eine Kommando

```powershell
# einmalig, danach nur bei neuen/entfernten Sprechern/Voices nötig
powershell -ExecutionPolicy Bypass -File tools/voice/setup.ps1 -Only cbx,piper
D:/tts-bake/venvs/cbx/Scripts/python.exe tools/voice/make_refs.py     # Referenzstimmen holen/bauen

# Zeilen aus index.html extrahieren (Node, kein Python-venv nötig). Schreibt selbst nach
# D:/tts-bake/lines.json (--out ändert das) — NICHT mit '>' umleiten, die Zusammenfassung geht auf stderr.
node tools/voice/extract_lines.mjs

# backen (Cache macht Re-Runs schnell: nur neue/geänderte Zeilen werden generiert)
D:/tts-bake/venvs/cbx/Scripts/python.exe tools/voice/bake.py
```

Das war's — `voice_clips.js` im Repo-Root ist danach aktuell. Für einen schnellen Re-Bake nach der
Story-Merge (nur neue Zeilen, alte bleiben aus dem Cache):

```powershell
node tools/voice/extract_lines.mjs
D:/tts-bake/venvs/cbx/Scripts/python.exe tools/voice/bake.py --only-missing --prune
```

`--prune` wirft Clips raus, deren Key nicht in `lines.json` vorkommt (gestrichene/umformulierte Zeilen), damit `voice_clips.js` nach Story-Umbauten nicht mit
toten Clips wächst. Nur mit einer vollständigen `lines.json` benutzen (nicht mit `--limit`-Testläufen).
Die Ausgabe von `extract_lines.mjs` prüfen: meldet es `CUTSCENE_VO ... DIFFERS`, muss der `/*CVO*/`-Block
in `index.html` aus `D:/tts-bake/lines_cvo.json` aktualisiert werden (sonst spielen Cutscenes alte Keys).

Nützliche Flags: `--speakers WAGNER,SEPP` (nur bestimmte Sprecher), `--keys k1,k2` (nur diese Clips;
mit `--force` und ggf. `TTS_SEED_OFFSET=100` neu würfeln), `--force` (Cache ignorieren,
z. B. nach einer Casting-Änderung — der Cache-Key enthält ohnehin einen Hash der Casting-Parameter,
daher invalidiert sich das meiste automatisch), `--limit N` (Smoke-Test), `--in`/`--out` (andere
Pfade).

## Wie es funktioniert

1. **`extract_lines.mjs`** liest `index.html` (nur lesend!) und findet jede Sprecherzeile — bevorzugt
   über `window.collectVoiceLines()` im laufenden Spiel (headless via `tools/hbrun.mjs`), sonst statisch:
   String-Literale `'SPRECHER|Text|Hinweis'` (siehe `df3c318`), rein literale Ternär-Verkettungen wie
   `'WAGNER|Fahrwerk '+(c?'ausgefahren':'eingefahren')+'.'` (beide Varianten) und die Cutscene-Bodies
   (`<span class="who">NAME:</span> „…"` = Sprecher, Rest = NARRATOR). Zeilen mit Laufzeitwerten
   (Zahlen, Namen) bleiben stumm. Schreibt eine flache Liste
   `{speaker, text, say, hint, key}` nach `lines.json`. `key` ist FNV-1a(32) von
   `speaker + "|" + text` (Hinweis zählt nicht mit) — **muss** mit dem `voiceKey`, das das Spiel
   selbst berechnet, übereinstimmen, sonst findet die Laufzeit den Clip nicht.
2. **`casting.json`** ordnet jedem Sprecher eine Engine + Stimme + Basisparameter zu, plus
   Mood-Deltas (aus dem Sprechhinweis-Vokabular, z. B. "wuetend", "fluestern") und generische
   Archetypen für Sprecher, die noch nicht namentlich erfasst sind.
3. **`bake.py`** generiert pro Zeile bis zu 3 Kandidaten (Chatterbox) bzw. 1 (Piper, deterministisch),
   lässt jeden durch `qa.py` laufen (WER/CER, MOS, Sprecherähnlichkeit, F0, Lautstärke/Clipping/
   Stille-Sanity) und nimmt den besten. Danach: Mono-Downmix (**kein** Pitch-Shift/Zeit-Stretch mehr —
   ruiniert die MOS massiv, siehe `report/bakeoff.md` "Bekannte Grenzen"; Stimmdifferenzierung läuft
   nur noch über Referenzwahl + `exaggeration`/`cfg_weight`/`temperature`), Stille am Anfang/Ende auf
   ~80 ms getrimmt, Loudness-Normalisierung auf -18 LUFS / Peak -1 dBTP, MP3-Encode (mono, ~48 kbps via
   ffmpeg). Cache-Key: `{key}_{engine}_{casting-hash}` unter `D:/tts-bake/cache/clips/` — ein Re-Bake
   generiert nur, was sich wirklich geändert hat.
4. **`voice_clips.js`** wird mit exakt erhaltenen `/*CLIPS*/…/*/CLIPS*/`- und
   `/*DUR*/…/*/DUR*/`-Markern geschrieben (regex-basiertes Merge), damit `--only-missing` bestehende
   Einträge nicht anfasst.

## Engines & Lizenzen

| Engine | Lizenz | Verwendet für |
|---|---|---|
| Chatterbox Multilingual TTS | MIT | alle menschlichen/klonbaren Sprecher (WAGNER, LÄRCHE, SEPP, WIGGERL, NARRATOR, KELLER, KIEBITZ, "?") |
| Piper (ONNX-Voices) | Code MIT, Stimmen je nach Datensatz (s. u.) | HELIOS, STIMME (bewusst synthetisch/nicht-menschlich) |
| XTTS-v2 | Coqui Public Model License (nicht-kommerziell) | **nicht verwendet** — siehe `report/bakeoff.md` |
| F5-TTS + `aihpi/F5-TTS-German` | Basis-Code MIT, Fine-tune-Checkpoint CC-BY-NC-4.0 | **nicht verwendet** — siehe `report/bakeoff.md` |
| Qwen3-TTS | Apache-2.0 | in `setup.ps1` vorbereitet, nicht mehr getestet — nicht verwendet |

Volle Begründung, Metriken (WER/CER/MOS/Sprecherähnlichkeit) und Vergleichstabelle:
**`D:/tts-bake/report/bakeoff.md`**.

## Referenzstimmen (Zero-Shot-Klon-Prompts) — Herkunft & Lizenz

Siehe `tools/voice/make_refs.py` (reproduzierbarer Fetch/Build) und `report/bakeoff.md` fürs Detail.
Kurzfassung:

- `refs/librivox/*.wav` — echte menschliche Aufnahmen, 9–11 s aus **gemeinfreien** LibriVox-Lesungen
  (archive.org, Lizenz „Public Domain"). Eine eigene Stimme pro männlicher Hauptfigur — vorher klonten
  WAGNER, SEPP und KELLER alle `thorsten_disgusted.wav` und klangen wie ein Mann (ECAPA-Ähnlichkeit
  0,92–0,95, F0 ~180 Hz statt Bariton/Bass). Auswahl: 110 Ausschnitte von 57 deutschen LibriVox-Lesern
  gescannt (UTMOS, SNR, F0, Sprechtempo, Sprecher-Embedding), Top-Kandidaten pro Rolle probegebacken.
  Datei, Startzeit und Länge stehen in `make_refs.py` (`LIBRIVOX_REFS`) → bytegenauer Neubau.
- `refs/thorsten/*.wav` — echte menschliche Aufnahmen aus dem **CC0**-Datensatz
  `Thorsten-Voice/TV-44kHz-Full` (Subset `TV-2021.06-Emotional`) auf HuggingFace. Nur noch für `?`
  (Flüster-Ref) und den Archetyp `boss_pilot_m`; HELIOS/STIMME sind Pipers `thorsten-high`.
- `refs/piper/*.wav` — selbst generiert, indem Piper-Stimmen (`rhasspy/piper-voices`, Code MIT)
  einen kurzen Satz vorlesen. **Achtung, die Stimmen selbst haben die Lizenz ihres Trainingsdatensatzes**
  (laut MODEL_CARD der jeweiligen Stimme, geprüft im Review):
  - `kerstin` (KIEBITZ, officer_f) — Datensatz `rhasspy/dataset-voice-kerstin`, **CC0**.
  - `thorsten-high` (HELIOS, STIMME, boss_ai) — Thorsten-Voice, **CC0**.
  - `eva_k` (LÄRCHE, young_f), `karlsson` (WIGGERL, young_m), `ramona` (NARRATOR, narrator) —
    **M-AILABS Speech Dataset** (MODEL_CARD: "License: See URL", caito.de). Nicht CC0: M-AILABS steht
    unter einer eigenen, permissiven BSD-artigen Lizenz mit Namensnennung (das Audio stammt aus
    gemeinfreien LibriVox-Lesungen). Für eine Veröffentlichung in den Credits nennen:
    „Sprachreferenzen: M-AILABS Speech Dataset (Imdat Solak / caito.de), Thorsten-Voice (CC0), Kerstin (CC0)“ —
    oder, falls strikt CC0 gewünscht, LÄRCHE/WIGGERL/NARRATOR auf `kerstin`/`thorsten_*`-Referenzen umcasten
    und neu backen (`--speakers LÄRCHE,WIGGERL,NARRATOR --force`).

## Credits / Lizenzen

Alle Stimmen sind synthetisch (offline gebacken); die Referenzen liefern nur die Klangfarbe. Kein Leser
spielt sich selbst, keine Figur ist einer echten Person nachempfunden. Einzige Ausnahme bei der Klangfarbe:
SEPP und WIGGERL klonen bewusst echte bairische Sprecher (Wikimedia Commons, CC BY / CC BY-SA, siehe Tabelle),
weil nur so hörbarer Dialekt entsteht; die Figuren selbst sind trotzdem erfunden.

**Text zum Kopieren (Credits-Panel im Spiel):**

> Sprachausgabe erzeugt mit Chatterbox Multilingual (Resemble AI, MIT-Lizenz) und Piper (MIT-Lizenz).
> Stimmreferenzen: die LibriVox-Leser FritzSavira, marham63, Christian Al-Kadi, Boris und Carsten
> (gemeinfreie Aufnahmen, librivox.org); Thorsten-Voice von Thorsten Müller (CC0); Kerstin (CC0);
> M-AILABS Speech Dataset (Imdat Solak / caito.de). Bairische Stimmreferenzen: Dawaiamoi – „Keglbua“,
> gesprochene Boarische Wikipedia (CC BY-SA 4.0); Wikitongues – „Sebastian speaking Bavarian“ (CC BY 3.0),
> beide über Wikimedia Commons. Danke an alle LibriVox-Freiwilligen!

| Figur | Referenz | Quelle | Leser / Sprecher | Lizenz |
|---|---|---|---|---|
| WAGNER | `refs/librivox/fritzsavira.wav` (ab 128,12 s, 9,46 s) | [Andersens Märchen Ergänzungsband – „Die Dryade 2"](https://archive.org/details/andersensmarchenerganzungsband_2404_librivox) | [FritzSavira](https://librivox.org/reader/10325) | gemeinfrei (Public Domain) |
| SEPP | `refs/bavarian/keglbua.wav` (ab 48,59 s, 11,48 s) | [Gesprochene Boarische Wikipedia – „Keglbua"](https://commons.wikimedia.org/wiki/File:Keglbua.ogg) | [Dawaiamoi](https://commons.wikimedia.org/wiki/User:Dawaiamoi) | CC BY-SA 4.0 |
| WIGGERL | `refs/bavarian/sebastian.wav` (ab 0,22 s, 10,57 s) | [WIKITONGUES: Sebastian speaking Bavarian](https://commons.wikimedia.org/wiki/File:Bavarian_(Wikitongues).ogg) | Sebastian (Wikitongues) | CC BY 3.0 |
| (früher SEPP, ungenutzt) | `refs/librivox/marham63.wav` (ab 240,98 s, 9,68 s) | [Max Liebermann: Gesammelte Schriften – „Zwei Holzschnitte von Manet"](https://archive.org/details/schriften_liebermann_1811_librivox) | [marham63](https://librivox.org/reader/12415) | gemeinfrei |
| KELLER | `refs/librivox/alkadi.wav` (ab 93,90 s, 10,84 s) | [Karl May: Sammlung kurzer Werke – „Der Ölprinz"](https://archive.org/details/sammlung_karl_may_1010_librivox) | [Christian Al-Kadi](https://librivox.org/reader/3503) | gemeinfrei |
| Archetyp `officer_m` (unbekannte Sprecher) | `refs/librivox/boris.wav` (ab 48,36 s, 9,72 s) | [Cervantes: Don Quixote, Band 1 – Abschnitt 17](https://archive.org/details/don_quixote_band_1_1805_librivox) | [Boris](https://librivox.org/reader/5753) | gemeinfrei |
| Archetyp `old_bavarian_m` | `refs/librivox/carsten.wav` (ab 148,36 s, 11,18 s) | [Sammlung kurzer deutscher Prosa 060 – „Der gelbe Kater"](https://archive.org/details/sammlung_kurzer_deutscher_prosa_060_2311_librivox) | [Carsten](https://librivox.org/reader/19039) | gemeinfrei |
| HELIOS, STIMME | Piper `de_DE-thorsten-high` | [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) | Thorsten Müller ([Thorsten-Voice](https://www.thorsten-voice.de)) | CC0 |
| `?`, Archetyp `boss_pilot_m` | `refs/thorsten/*.wav` | [Thorsten-Voice/TV-44kHz-Full](https://huggingface.co/datasets/Thorsten-Voice/TV-44kHz-Full) | Thorsten Müller | CC0 |
| KIEBITZ | `refs/piper/kerstin.wav` | Piper `de_DE-kerstin-low` ([Datensatz](https://huggingface.co/datasets/rhasspy/dataset-voice-kerstin)) | Kerstin | CC0 |
| LÄRCHE, NARRATOR (Archetyp `young_m`) | `refs/piper/eva_k.wav`, `ramona.wav` (`karlsson.wav`) | Piper `eva_k`/`ramona`/`karlsson` | [M-AILABS Speech Dataset](https://www.caito.de/2019/01/03/the-m-ailabs-speech-dataset/) (Imdat Solak) | BSD-artig, Namensnennung |

Engines: [Chatterbox](https://github.com/resemble-ai/chatterbox) (MIT), [Piper](https://github.com/rhasspy/piper) (MIT).
LibriVox-Aufnahmen sind gemeinfrei („All LibriVox recordings are in the public domain"); die Nennung
ist freiwillig, aber fair. Die bairischen Commons-Referenzen verlangen Namensnennung; `keglbua.wav` steht
wie das Original unter CC BY-SA 4.0 (ShareAlike gilt im Zweifel auch für die daraus geklonten SEPP-Clips
in `voice_clips.js`, deshalb dieselbe Lizenz nennen, wenn sie weitergegeben werden).

## Casting (`casting.json`)

`lexicon`: Aussprache-Korrekturen, die nur auf den gesprochenen Text wirken (Key bleibt am Original),
z. B. `"Shift": "Schifft"`. Neue englische Begriffe/Abkürzungen in Story-Zeilen hier eintragen.
QA verwirft zusätzlich Kandidaten mit Nachplappern am Ende (Whisper hört ≥2 Wörter mehr als im Text)
oder abgeschnittenem letzten Wort und würfelt neu. Neue Sprecher: `"NAME": {"archetype": "boss_pilot_m"}`
(plus beliebige Overrides) oder nur `speaker_archetypes`/`default_archetype` setzen.

Pro Sprecher: `engine`, Referenz/Stimme, Basisparameter (`exaggeration`, `cfg_weight`,
`temperature`, `polish`, `lax`; `speed`/`pitch_semitones` sind reine Doku-Reste ohne Wirkung mehr,
siehe `_comment2` in `casting.json`). `moods` sind Deltas,
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

`tools/voice/make_refs.py` holt danach den CC0-Datensatz, schneidet die LibriVox-Referenzen (curl +
ffmpeg) und generiert die Piper-Referenzen (siehe oben); alles idempotent (`--force` zum Neubauen,
`--only thorsten|piper|librivox|commons` für eine Gruppe).

## Dateien in diesem Ordner

- `casting.json` — Sprecher/Mood/Archetyp-Konfiguration (siehe oben).
- `bake.py` — die Pipeline (Generierung, QA, Post-Processing, Encode, `voice_clips.js`-Schreiben).
- `qa.py` — Qualitätsmetriken (WER/CER, MOS, Sprecherähnlichkeit, F0, Sanity-Checks, Scoring).
- `extract_lines.mjs` — Zeilen aus `index.html` extrahieren (read-only).
- `make_refs.py` — Referenzstimmen reproduzierbar holen/bauen.

Alles Schwere (Venvs, Modelle, Caches, Referenzaudio, Reports) liegt außerhalb des Repos unter
`D:/tts-bake/` (Pfad überschreibbar via `$env:TTS_BAKE`).
