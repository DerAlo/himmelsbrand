# Test-Werkzeuge (Node ≥ 22, Chrome installiert)

- `node tools/jsgate.mjs index.html` — Syntax-Check aller Inline-Skripte + der .js-Dateien daneben. Muss vor jedem Commit „JSGATE OK“ melden.
- `node tools/hbrun.mjs --root . --scenario <datei.mjs> --out <ordner>` — startet das Spiel headless (echte GPU, Ton stumm) und führt ein Szenario aus. API im Dateikopf.
- `SWEEP_MS=2500 SWEEP_SHOTS=1 node tools/hbrun.mjs --root . --scenario tools/sweep.mjs --out <ordner> --timeout 600` — Regressionstest über alle Missionen, Endlos-Modus, Zwischensequenzen und Menü (Fehler, Draw-Calls, Dreiecke, fps).
- `node tools/hbrun.mjs --root . --scenario tools/smoke.mjs` — schneller Rauchtest.
