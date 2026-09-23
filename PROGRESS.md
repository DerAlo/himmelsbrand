# FX-MODELS Fortschritt

## Erledigt
- `collectMerge`/`flushMerge`-Helfer (nach `triGeo()`, Sektion 8) für statisches Geometrie-Merging via
  `THREE.BufferGeometryUtils.mergeBufferGeometries` (r128-CDN-Tag ergänzt). Normalisiert indexed/
  non-indexed vor dem Merge (sonst Konsolenfehler bei gemischten Primitiven + `triGeo()`-Meshes).
- `buildEurofighter`: alle statischen Teile (Rumpf, Cockpit, Lufteinlässe, Flügel, Canards,
  Leitwerk, Triebwerke, Pylonwaffen, Tank, Markierungen/Decals) laufen durchs Merging; Fahrwerk,
  Flammen-Array (`userData.flames`), AB-Licht (`userData.ab`) unverändert/einzeln. Pylon-Materialien
  (Rumpf/Spitze) + Decal-Materialien (Kreuz/Stencil) gehoben, damit sie sich über die 4 Pylonen bzw.
  6 Decals hinweg zusammenfassen. Neue Schock-Diamant-Textur (`afterburnerTexture`) auf den
  Flammenkegeln. Neue Positionslicht-Strobes (`userData.strobes`) + `HOOKS.always`-Blinker.
- `buildEnemy`: gleiches Merging (body/dark/Streifen-Material gehoben). Neue `tintAceVisual()`
  (magenta Sensorauge + Emissive-Wash) an `spawnAce()` gehängt (1 Zeile, foreign edit).
- `buildGroundModel`: `truck`/`depot`/`bierkiste` gemerged (waren die einzigen Tags mit echtem
  Dedup-Potential; Radar/SAM/Turm/Pylon/Bunker/Hangar/Default bleiben unverändert — Turm-/Spin-Teile
  brauchen Einzel-Meshes für Laufzeit-Rotation).
- Sektion 7 (Partikel/Juice): `spawnDebris`/`updateDebris` — brennende Trümmer ziehen jetzt eine
  Rauch/Glut-Spur und blitzen beim Aufschlag einmalig auf. `groundExplode` erkennt Wasser
  (`terrainHeight<waterLevel`) und spawnt eine helle Gischt statt des Staubrings.
- `updateAlly`: Banking/Roll aus Gier-Rate (lokale Z-Rotation nach dem lookAt), vorher reine
  Blickrichtung ohne Schräglage.
- `updateMissiles`: `trailCd` (existierte, wurde aber nie ausgewertet) nutzt jetzt einen
  Intervall-Spawn heller, kurzlebiger Glut-Partikel zusätzlich zur bestehenden Rauch/Feuer-Spur —
  liest sich als „brennende" Spur statt nur grauer Nebel.

## Getestet
- `node tools/jsgate.mjs index.html` → OK nach jeder Änderung.
- Eigenes Szenario (Spieler-Jet-Nahaufnahme, Gegner+Ass, Raketenstart): 0 exceptions/consoleErrors.
- Eigenes Szenario 2 (Ally-Banking, alle 9 Bodenziel-Tags, Depot-Explosion, erzwungener
  Wasser-Splash via `terrainHeight`-Mock): 0 exceptions/consoleErrors, Screenshots geprüft.
- Voller Sweep (`tools/sweep.mjs`, SWEEP_MS=2200): 27/27 Missionen + Endlos + 12 Cutscenes,
  0 newErrors überall. Draw calls jetzt 448-968 (vorher Baseline ~1000-1300) — klar runter.
  Dreiecke 685k-786k (Baseline ~700-780k) — praktisch unverändert, Budget eingehalten.
- Zweiter voller Sweep nach dem Glut-Spur-Zusatz in `updateMissiles`: erneut 27/27 Missionen +
  Endlos + 12 Cutscenes, 0 newErrors, minFps 54.7, maxCalls 947 — keine Regression.

## Nächste Schritte (falls Zeit/Budget reicht)
- Tracer-Streckung nach Geschwindigkeit nicht umgesetzt (Tracer ist bereits ein langer, dünner
  Box-Streak + additivem Glow-Sprite — bewusst nicht angefasst, geteiltes Pool-Mesh/Material,
  Risiko > Nutzen).
- Ally-Banking optisch noch nicht per Screenshot bestätigt (Ally war im Testlauf nicht sichtbar
  im Frame, aber Code-Pfad lief fehlerfrei durch alle 27 Missionen inkl. B-Team wo Allies spawnen).

## Ownership-Hinweis
- Fahrwerk-Subtree in `buildEurofighter` unverändert (LANDING-Track).
- `buildRunway` nicht angefasst.
- Hit-Logik/Schadenswerte in Sektion 10/10b/10c/11 unverändert — nur die Partikel-Spawn-Zeilen und
  Modell-Builder gehören mir.
