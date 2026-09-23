# TTS Fortschritt

## Erledigt
- Bake-off (Chatterbox multilingual vs. XTTS-v2 vs. F5-TTS-German vs. Piper) mit WER/CER
  (faster-whisper large-v3), MOS (UTMOS), Sprecherähnlichkeit (SpeechBrain ECAPA), F0-Range —
  gleicher Testsatz, gleiche Klon-Referenz. **Chatterbox multilingual (MIT) gewinnt klar**
  (MOS 3.75 vs. 2.20/1.32, WER 0.00 vs. 0.27/1.00) und ist die einzige Klon-Engine mit
  kommerzfreundlicher Lizenz. XTTS-v2 (CPML, nicht-kommerziell) und F5-TTS-German
  (CC-BY-NC-4.0, + Ausgabe teils unbrauchbar) daher nicht verwendet. Volle Tabelle + Rationale:
  `D:/tts-bake/report/bakeoff.md`.
- `tools/voice/casting.json`: Engine/Referenz/Parameter pro Sprecher (WAGNER, LÄRCHE, SEPP,
  WIGGERL, HELIOS, STIMME, NARRATOR, "?", **KELLER**, **KIEBITZ** neu aus narrative_design.md),
  11 Mood-Deltas (Hinweis-Vokabular), 8 generische Archetypen als Fallback für künftige Sprecher.
- `tools/voice/bake.py`: Ein-Kommando-Pipeline. FNV-1a-Key = Spiel-`voiceKey`, Cache pro
  (Key, Engine, Casting-Hash), bis zu 3 Kandidaten mit QA-Retry, Post-Processing
  (Mono, Pitch/Speed, Silence-Trim ~80ms, Loudness -18 LUFS/-1dBTP, MP3 mono ~48kbps),
  regex-Merge nach `voice_clips.js` (erhält bestehende Einträge bei `--only-missing`).
- `tools/voice/qa.py`: WER/CER, MOS, Sprecherähnlichkeit, F0, Sanity-Checks. Fix: MOS/Dauer-
  Härtetests klammern jetzt Clips mit ≤2 Silben aus (Einwort-Zeilen wie "Adler" wurden vorher
  grundlos als `bad` markiert und unnötig neu generiert — UTMOS ist auf so kurzen Clips
  unzuverlässig). Verifiziert per Re-Run: „still-flagged-bad" für den Testfall ging von 2→1
  (die verbleibende, echte Low-MOS-Zeile bleibt korrekt markiert).
- `tools/voice/make_refs.py`: reproduzierbarer Fetch/Build der Klon-Referenzen (CC0
  Thorsten-Voice-Emotional-Datensatz via HuggingFace + selbst erzeugte Piper-Referenzen).
- `tools/voice/setup.ps1`: `cbx`-Venv jetzt komplett (Chatterbox + kompletter QA-Stack +
  `setuptools<81`-Pin gegen den `pkg_resources`-Bruch in `resemble-perth`) — das ist die einzige
  Venv, die `bake.py` braucht. Neuer `-Only piper`-Block holt Binary (GitHub Release) + Stimmen
  (`rhasspy/piper-voices` via HuggingFace) reproduzierbar, statt (wie vorher ad-hoc) von einem
  anderen Track-Ordner (`D:/piper-studio`) abzuhängen.
- `tools/voice/README.md`: Ein-Kommando-Anleitung, Engine-/Referenz-Lizenzen, Casting-Erklärung.

## Kritischer Bugfix nach dem letzten Commit (wichtig!)
- Der erste volle Bake-Lauf lieferte für **alle** WAGNER-Zeilen auffällig einheitlich niedrigen
  MOS (~1.3-1.9), obwohl der Bake-off-Sanity-Check MOS 3.75 für eine ähnliche WAGNER-Zeile zeigte.
  Root-Cause isoliert über `D:/tts-bake/diag_postprocess.py`: **`librosa.effects.pitch_shift`/
  `time_stretch` (Phasenvocoder-DSP) ruinieren die wahrgenommene Qualität massiv, schon bei
  winzigen Werten** (3% Tempo → MOS 3.25→1.39, 2.5 Halbtöne → MOS 1.33). WER/CER bleiben fast
  unverändert (Inhalt übersteht es), aber es klingt hörbar phasig/robotisch. STFT-Parameter-Tuning
  rettet es nicht (bestes Ergebnis weiterhin MOS ~1.4).
- **Fix**: laufenden (verseuchten) Bake gestoppt; `bake.py`s `postprocess()` führt keine Pitch-/
  Tempo-DSP mehr aus; `casting.json` neu geschrieben ohne `speed`/`pitch_semitones`-Felder,
  `_note`-Texte korrigiert (Differenzierung von WAGNER/SEPP/KELLER läuft jetzt nur noch über
  `exaggeration`/`cfg_weight`/`temperature` + Referenzwahl); `report/bakeoff.md` „Bekannte
  Grenzen" um den Befund ergänzt.
- **Verifiziert per Smoke-Test durch die echte `bake.py`-Pipeline** (nicht nur das Diagnose-Skript):
  `--speakers WAGNER --limit 6 --force` → avg MOS 3.43, `--speakers SEPP --limit 4 --force` →
  avg MOS 2.99 (Dialekt, `lax:true`) — beide im gesunden Bereich, `still-flagged-bad=0`.
- Cache invalidiert sich für den vollen Re-Bake automatisch (Casting-Hash ändert sich, weil
  `speed`/`pitch_semitones` aus den Casting-Werten verschwunden sind), zusätzlich mit `--force`
  gestartet, um wirklich jede Zeile durch die reparierte Pipeline laufen zu lassen.

## In Arbeit / noch nicht abgeschlossen
- **Voller Bake aller 158 Basiszeilen läuft (2. Versuch, mit dem Fix), Hintergrundprozess.**
  Nach Abschluss: Größenbudget (≤12MB) prüfen, In-Game-Laden per hbrun verifizieren
  (`Object.keys(window.VOICE_CLIPS).length`, `decodeAudioData`-Stichprobe), finalen Sweep/jsgate
  laufen lassen, dann committen.
- Dieser Zwischenstand: Pipeline + Doku + Bugfix fertig, Bake noch nicht fertig —
  `voice_clips.js` im Repo ist noch der alte Baseline-Stand (XTTS+Piper aus `54ee9a8`).

## Getestet
- `node tools/jsgate.mjs index.html` → OK (index.html von mir nicht angefasst).
- `qa.py`-Fix per gezieltem Re-Run verifiziert (s.o.).
- Bake-off-Metriken reproduzierbar über `python D:/tts-bake/qa_bakeoff.py`.

## Ownership-Hinweis
- `index.html` read-only für mich, nicht angefasst.
- Eigentum: `tools/voice/*` (Repo) + `D:/tts-bake/*` (außerhalb Repo, Venvs/Modelle/Caches/Referenzen).
- Neue Sprecher KELLER/KIEBITZ sind bereits gecastet — sobald der STORY-Track neue Zeilen für sie
  einbaut, reicht `python tools/voice/bake.py --only-missing` für einen inkrementellen Re-Bake
  (Cache trifft für alles Unveränderte).
