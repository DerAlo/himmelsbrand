# HANDOFF — Projektübergabe (HIMMELSBRAND + alo-tower Musik-KI)

> Vollständige Wissens- und Statusübergabe, damit auf anderen Geräten / mit anderen Agents nahtlos
> weitergearbeitet werden kann. Stand: Commit `952baba` (main). Zwei getrennte Projekte:
> **(A) HIMMELSBRAND** — Browser-Flugsimulator (dieses Repo). **(B) alo-tower** — lokale Musik-KI
> (ACE-Step + YuE) auf einem Windows-GPU-Tower, ferngesteuert per MCP/Web-UI.

## Inhalt
- [0. Schnellstart](#0-schnellstart)
- [A. HIMMELSBRAND – Flugsimulator](#a-himmelsbrand--flugsimulator)
  - [A1. Repo, Build, Push (zwei GitHub-Konten!)](#a1-repo-build-push)
  - [A2. Architektur (alles in `index.html`)](#a2-architektur)
  - [A3. Flugmodell & Kamera](#a3-flugmodell--kamera)
  - [A4. Waffen](#a4-waffen)
  - [A5. Gegner-KI](#a5-gegner-ki)
  - [A6. Bosse](#a6-bosse)
  - [A7. Kampagnen-Runtime & Missionen](#a7-kampagnen-runtime--missionen)
  - [A8. Das B-Team (Komödien-Kampagne)](#a8-das-b-team)
  - [A9. Audio (Musik + Engine + TTS)](#a9-audio)
  - [A10. HUD, Progress/Save, Juice](#a10-hud-progresssave-juice)
  - [A11. Balance-Stand](#a11-balance-stand)
  - [A12. Testen (headless Chrome via CDP)](#a12-testen)
- [B. alo-tower – lokale Musik-KI](#b-alo-tower--lokale-musik-ki)
  - [B1. Zugang zum Tower (Windows/SSH/PowerShell)](#b1-zugang)
  - [B2. ACE-Step + MCP + Player](#b2-ace-step)
  - [B3. YuE + Web-UI](#b3-yue)
  - [B4. VRAM / gleichzeitiger Betrieb](#b4-vram)
- [C. Arbeitsweise & Konventionen](#c-arbeitsweise--konventionen)
- [D. Offene Ideen / mögliche nächste Schritte](#d-offene-ideen)
- [E. Fallstricke (hart erkämpftes Wissen)](#e-fallstricke)

---

## 0. Schnellstart
- **Flugsim spielen:** `open /Users/riedhammer/local_llm_test/index.html` (oder lokalen Server). Braucht nur Internet fürs Three.js-CDN.
- **Repo (privat):** `DerAlo/himmelsbrand`, Branch `main`. Lokal: `/Users/riedhammer/local_llm_test/`.
- **Musik-KI:** Tower per `ssh alo-tower` (Windows). YuE-Web-UI: `http://192.168.178.88:7870/`. ACE-Step-Player: `http://192.168.178.88:8766/`. ACE-Step-MCP: `http://192.168.178.88:8765/mcp`.
- **Sprache:** Nutzer ist deutschsprachig → **alle Spieltexte & Kommunikation auf Deutsch**.

---

## A. HIMMELSBRAND – Flugsimulator

Arcade-Kampfflugsim: deutscher **Eurofighter** gegen die abtrünnige NATO-Drohnen-KI **HELIOS**.
**Eine einzige Datei** (`index.html`, ~4230 Zeilen): Three.js r128 (CDN) + Web Audio API, prozedurale
unendliche Welt (Simplex Noise), keine externen Assets. Repo-Dateien: `index.html`, `README.md`,
`B-TEAM.md` (Design-Bibel der Komödien-Kampagne), `HANDOFF.md` (diese Datei).

### A1. Repo, Build, Push
- **Kein Build.** Alles in `index.html`. Ändern → im Browser neu laden.
- **Zwei GitHub-Konten** in `gh`: `riedhammer_agenda` (Default/aktiv) und `DerAlo` (Besitzer des privaten Repos). Ein normaler `git push` scheitert („Repository not found"), weil das Default-Konto keinen Zugriff hat.
- **Push-Rezept (bewährt):**
  ```bash
  gh auth switch --user DerAlo >/dev/null 2>&1
  git push "https://x-access-token:$(gh auth token)@github.com/DerAlo/himmelsbrand.git" main
  git update-ref refs/remotes/origin/main HEAD   # sonst zeigt git fälschlich "N commits ahead"
  ```
  (Der Token-URL-Push aktualisiert die lokale `origin/main`-Tracking-Ref NICHT → daher das `update-ref`.)
- **Pre-Commit-Gate (immer):** JS-Syntax prüfen, bevor committet wird:
  ```bash
  node -e "const fs=require('fs');const h=fs.readFileSync('index.html','utf8');const m=h.match(/<script>([\s\S]*)<\/script>\s*<\/body>/);new Function(m[1]);console.log('JS OK');"
  ```
- **Commit-Trailer** (Vorgabe der Session):
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01ULeW4w2zaW73aMG1uBYdzo
  ```

### A2. Architektur
Ein `<script>` in `index.html`, grob in nummerierten Blöcken. Wichtige Einstiegspunkte / globale Objekte:
- `CFG` — zentrale Tunables (Geschwindigkeiten, Waffen, Landung). Direkt am Anfang.
- `CAMPAIGN[]` (20 HELIOS-Missionen) und `BTEAM_CAMPAIGN[]` (7), `CUTSCENES{}` + `BTEAM_CUTSCENES{}`.
- `player` (Zustandsobjekt), `enemies[]`, `missiles[]`, `enemyMissiles[]`, `bombs[]`, `bullets[]`, `groundTargets[]`, `boss`, `ally`.
- Kernschleife `loop(now)`: teilt `rawDt` (Echtzeit; Juice/Timer/HUD-Puls) vs. `dt = rawDt*ts` (Welt/Physik; friert bei hitStop/slowmo). `menuTime += rawDt` jeden Frame (HUD-Blinken).
- `state`: `'menu' | 'playing' | 'paused' | 'gameover' | 'cutscene'`. `gameMode`: `'menu' | 'campaign' | 'endless'`.
- Zwei-Kampagnen-Umschaltung: `activeCampaign` (Zeiger auf `CAMPAIGN` oder `BTEAM_CAMPAIGN`) + `campaignId` (`'helios' | 'bteam'`). `unlockedCount()`/`bumpUnlocked()` wählen den richtigen Zähler.

### A3. Flugmodell & Kamera
- **Stabilisiertes Arcade-Modell:** absolute `heading` (Gier) + `pitch` werden **jedes Frame neu** aus Eulerwinkeln aufgebaut → kann nie invertieren; `roll` ist rein kosmetisch. Pitch ungeklammert/gewrappt → volle Loopings.
- **Energie-Kampf:** Wenderate hängt von Airspeed ab. `playerTurnMultFor(sp)` lerpt **2.0→0.95** (min→boost); `TURN_RATE=1.5*mult` → 3.0 rad/s bei min, ~1.43 bei boost. Gegner: `turnMultFor` lerpt 1.5→0.5 (klar unterlegen). **Fairness-Cap:** Ass `baseTurn*turnMul ≤ 1.85` < Spieler-Langsam-Turn 3.0. Skill = bremsen (Strg) und in den Rücken ziehen.
- **Kamera:** roll-frei (Horizont bleibt waagerecht), folgt Pitch durch Loopings. Früherer Bug: Kamera-Hochachse sprang am senkrechten Scheitel → gefixt mit `leanFade` (blendet Neigung nahe senkrecht aus) + Lerp-Glättung. Yaw-Vorzeichen mit Hysterese (`player.yawSign`).
- **Start/Landung:** Missionen mit `start:'runway'` setzen das Flugzeug still auf eine `buildRunway()`-Piste. Vr (`CFG.rotateSpeed`), Abheben `CFG.liftoffSpeed`. Landung in `updatePlayer` nach Sinkrate (`player.vy`) + Ausrichtung + Fahrwerk (`gearDown`, Taste **B**) benotet → sauber/hart/Crash. Auto-Flare nah an der Piste.

### A4. Waffen
Drei Sekundärwaffen; **X** wechselt, **F/Rechtsklick** feuert selektierte, dedizierte Tasten daneben:
- **MG** (Leertaste/Linksklick): Lead-Pipper via `computeLeadPoint` (First-Order-Intercept) + `CFG.aimAssist` (0.42, bis 0.672 wenn Nase nah dran). Sofort tödlich gegen Grunts.
- **A2A-Lenkrakete** (Taste **F**): lenkt **nur bei rotem LOCK** (`currentLock` = nächster Gegner im Kegel), sonst Dumb-Fire geradeaus. `CFG.missileMax:6`, **0.45 s Kadenz** (`missileCd`), **nachladendes Magazin** (+1 alle `CFG.missileRegen=2.4 s`). Ass-Kill füllt auf. `missileDmg:90`, vs. Boss `missileDmgBoss:150`.
- **AGM Luft-Boden** (Taste **H**): lenkt auf **grünen Boden-Lock** (`groundLock` via `nearestGroundInFront`), fliegt durch Flugzeuge hindurch, trifft nur Bodenziele/Boss/Terrain. `agmDmg:280`, `agmMax:4`.
- **Bombe** (Taste **G**): ungelenkt, ballistisch, **CCIP-Kreis** (`predictBombImpact`). Direkttreffer 1000 (one-shot), Splash 450 @ radius+22 (eng → CCIP-Genauigkeit zählt). Default 8 Stück auf Bodenmissionen.
- `fireBullet(pos,dir,fromPlayer,dmg?)` hat optionalen Schaden-Override (für Grantl-Boost/Boss-Fan/SAM-Burst).
- **Loadout** in `setupMission`: `def.bombs`/`def.agms`/`def.weapon` überschreiben; Bodenmissionen defaulten auf 8 Bomben + `agmMax` AGMs.

### A5. Gegner-KI
- `ENEMY_STATS` (f16/f18/f22): hp/cruise/max/baseTurn/radius/score/fireRange/fireCd/burst/missileChance/**accuracy**. `accuracy` = Streuung (kleiner = tödlicher): f16 0.058 (locker) → f22 0.032 (präzise).
- `PERSONALITIES` (grunt/aggressor/sniper/ace) modifizieren die FSM (`e.pk`). Sniper committen jetzt (`standoff:1150, aggro:0.42, breakBias:1.20`). f22 Sniper-Anteil ~20 %.
- FSM: engage → break → extend → flee (`updateEnemies`). **Wichtiger Fix (zweimal aufgetreten):** `Matrix4.lookAt`-Ziel muss `+dir` sein (nicht negiert), sonst fliegen Jets rückwärts.
- Feind-Raketen: `enemyMissiles[]` + `fireEnemyMissile`/`updateEnemyMissiles` (ausweichbar; `CFG.ENEMY_MSL_CAP:3`). Nicht-Sniper-f18/f22 bekommen jetzt gelegentlich EINE Rakete (`missileChance` war vorher toter Code).
- `maybeCoordinate` = Zangenangriff; `spawnAce`/`ACE_NAMES`. Leash: `LEASH_SOFT=2200, LEASH_HARD=3600` (Modul-Scope!).

### A6. Bosse
- `boss` + `spawnBoss(kind, finale)`, `buildKronos`/`buildAuge`. Teile (Türme/Pylonen = `bossPart`) zerstören → `checkBossExpose()` legt Kern frei → `damageBoss`.
- **KRONOS** (schwimmende Werft, Türme) — m5, m13, b6. **Das Auge** (Pylonen) — m7, m12. Pylonen **feuern jetzt** (`sam:true`).
- Kern nimmt nur **halben Gun-Schaden** (`damageBoss(b.dmg*0.5)`) → Raketen/AGM-Job. Freigelegt: **telegrafiertes 3-Schuss-Sperrfeuer** (~6 dmg, 0.8 s). Finale/choicePoint-Bosse: +25 % Kern-HP + größere Explosionskette (`boss.finale`).
- HP-Balken zeigt **Teil-Fortschritt** (0→40 %) während der Schildphase, dann echte Kern-HP.
- `killBoss` re-entry-guard: `if(boss.dead) return; boss.dead=true; boss.exposed=false;`.

### A7. Kampagnen-Runtime & Missionen
- Laufzeit: `mission` + `setupMission(i)` / `updateMission(dt)` / `checkMissionComplete` / `checkMissionFailed`. `launchMission(i)`, `startEndless(mod)`, `gotoMenu()`, `resetWorld()`.
- **Objective-Kinds:** `destroyAir`, `destroyGround` (tag), `boss`, `minHP` (Constraint: done=!failed), `takeoff`, `land`, `protect` (Ally lebt), `reach` (über einen Wegpunkt fliegen, z. B. Bierkiste).
- **Sieg-Fenster-Schutz:** Nach Sieg 2,6 s Feier; `winLocked=true` verhindert, dass Rest-Feuer den Sieg in eine Niederlage kippt. Reset in `resetWorld`.
- HELIOS = 20 Missionen: Akt I `m0..m7`, Akt II `m8, m9, m_rueckenwind, m_nachtwache, m10, m_asche, m_grenzgaenger, m_fallwind, m_versprechen, m11, m12, m13`. Ids sind stabile Strings; `SAVE.missions` ist id-gekeyt; Unlock ist **index-basiert** → Einfügen weiterer Missionen ist sicher.
- Story: moralischer Twist (PROMETHEUS ist der wahre Feind, HELIOS war ein Schild). Charaktere: Spieler „Geier", Oberst Wagner, **Hauptmann Lärche** (eskortierbarer Ally, `ally`, `spawnAlly({name,full,color,hp})`). **Slow-burn-Romanze Geier↔Lärche** über Akt II (cutscenes bond1/2/3/confession), bewusst geschlechtsneutral/inklusiv. `storyChoice` ('trust'|'human') färbt das dynamische Ende. Zwischensequenzen: `showCutscene(key, after)` (liest `CUTSCENES` **und** `BTEAM_CUTSCENES`).
- **Nicht** `waveDelay` auf `start:'runway'`-Missionen setzen (Doppel-Spawn: pendingAir + gauntletQueue).

### A8. Das B-Team
Eigenständige, selbstironische **Komödien-Kampagne** (eigener Menü-Button „🍺 DAS B-TEAM"). Design-Bibel: `B-TEAM.md`.
- 7 Missionen `b0..b6` (Wer sonst? / Anfängerglück / Der Grantler / Die verschollene Kiste / Bierzelt-Taktik / Zwei gegen alle / O'zapft is!). Bogen: A-Team ausgelöscht → B-Team übernimmt → rettet durch Unberechenbarkeit die Welt (thematischer Anker: „kein Rechenkern sieht so viel Blödsinn kommen").
- Zwei bayerische Piloten `BTEAM_PILOTS`: **Sepp „Brummbär"** (grantl) & **Wiggerl „Radi"** (dusel). Jede Mission hat `hero`; der andere fliegt als **Wingman** (Ally-System).
- **Mechaniken** (nur wenn `player.hero` gesetzt; HELIOS/Endlos unberührt): **Grantl-Modus** (Sepp: Wut-Leiste → ~5,5 s Berserk ~1,9× dmg / ~1,7× Feuerrate, in `updateHero`), **Dusel** (Wiggerl: ~40 % Feind-Raketen „gehen daneben" + ~16 % Gun-Crit), **Brotzeit** (`BROTZEIT`-Map, `openBrotzeit(i)`-Screen vor jeder Mission → `player.bz` Modifikatoren dmg/fire/turn/wobble/hp; `player.maxHp`).
- Generische Spieler-Modifikatoren: `player.dmgMul/fireRateMul/turnMul/aimWobble` (im MG-Fire-Loop + TURN_RATE), `player.maxHp = CFG.playerHP + bz.hp` (alle STRUKTUR%-Anzeigen + Heals nutzen `maxHp`).
- Ton: bayerische Banner/Killfeed (gated auf `gameMode==='campaign' && campaignId==='bteam'`), Blasmusik-Soundtrack, Bierkisten-Running-Gag (unzerstörbares `bierkiste`-Bodenziel, `gt.invuln`).

### A9. Audio
Alles prozedural (Web Audio), im `Audio`-IIFE. **Wichtig:** headless braucht Chrome-Flag `--autoplay-policy=no-user-gesture-required`, sonst bleibt der Context suspended (Gains 0).
- **Adaptive Musik:** taktgenauer Lookahead-`scheduler()` (130 BPM), 8-Takt-Akkordform, Layer-Busse pad/bass/arp/lead/perc/brass/menace (+`musicDelay`-Echo), wiederkehrendes Lead-Thema, echtes Drum-Kit, Boss-Bläser-Stabs. `updateMusic(rawDt,mode,I)` blendet Layer nach Intensität (menu→cruise→combat→boss).
- **`musicStyle`** (`'score'|'bteam'`): B-Team = **Blasmusik-Oom-pah** in C-Dur via `mnoteMaj` (Tuba/Bläser/Marsch). `Audio.setStyle()` in launchMission/gotoMenu/startEndless. **Fix:** mPad/mBrass nehmen eine Note-Fn (sonst Dissonanz Dur vs. Moll).
- **Engine/Lock:** `setEngine`/`lockTone`. `Audio.silenceFlight()` rampt Motor+Lock auf 0 (in gotoMenu/gameover/pause). `Audio.duckMusic(on)` für Pause.
- **TTS-Stimmen** (`Voice`-IIFE, Web Speech API, offline): sprechen Funkzeilen, **Warteschlange** (jeder Satz zu Ende, dann nächster; onend-getrieben; Backlog-Cap ~5; stop bei Pause/Menü). Pro-Sprecher-Stimme + Pitch/Rate; männliche Stimmen für Sepp/Wagner/Wiggerl, weiblich für Lärche. **Standard AUS**, Toggle **V**. Kein echter Dialekt möglich → deutsche Stimme liest bairisch-geschriebenen Text = gewollter Möchtegern-Bairisch-Gag.

### A10. HUD, Progress/Save, Juice
- HUD: DOM-Readouts (gated via `body.in-game`) + Canvas-Overlay (`drawHUD`): Reticle, Ziel-Boxen, LOCK/Boden-LOCK, CCIP, Radar, Boss-Balken, Ally-Marker, Warnungen. WELLE-Stat (`#wavestat`) nur im Endlos sichtbar.
- **Save:** `localStorage` Key `himmelsbrand_save` (`SAVE`, id-gekeyt). `rateMission` (1–3 Sterne: Struktur `hp/maxHp≥0.65`, Zeit `≤par` via `DEFAULT_PAR`, Finesse `hp/maxHp≥0.92` bzw. saubere Landung — **ratio-basiert**, damit Weißwurst nicht cheatet). Unlocks: `ace` (Endlos, nach Akt I) + `goldWings` (**≥48/60 Sterne**).
- **Juice:** hitStop/slowmo (via `rawDt` vs `dt`), `markHit`, `spawnDebris`/`updateDebris`, damageFlash, Kill-Combo (×2..×5).

### A11. Balance-Stand
Letzter Pass = „klare Fixes + moderate Schärfe" (Commit `952baba`). Leitidee: Überlegenheit soll sich **verdient** anfühlen → Bedrohung oben drauf (Elites/Bosse/SAMs beißen), Grunt-Sofortkills bleiben. Details siehe A4–A6 + Commit-Message. **Bewusst NICHT angefasst** (fühlt sich richtig an): Gun-TTK, aimAssist, Grunt-Kurvenvorteil. Balance ist iterativ — Nutzer wollte selbst spielen und Feinjustierung zurückmelden (mögliche Stellschrauben: Elite-`accuracy`, Boss-Kern-HP, SAM-Burst-Schaden/Kadenz, Endlos-Heal-Kurve, `playerTurnMultFor`).

### A12. Testen
Kein Playwright. **Headless Chrome direkt via CDP** mit Node 22 (eingebautes `WebSocket`/`fetch`). Muster:
1. `python3 -m http.server <port>` im Repo starten (Hintergrund).
2. Chrome headless starten mit Flags: `--headless=new --enable-unsafe-swiftshader --use-gl=angle --use-angle=swiftshader --autoplay-policy=no-user-gesture-required --remote-debugging-port=<p> --remote-allow-origins=*`.
3. Per WebSocket an DevTools; `Runtime.evaluate` auf Spiel-Globals: `state`, `player`, `enemies`, `groundTargets`, `boss`, `mission`, `campaignId`, `activeCampaign`, `CAMPAIGN`, `BTEAM_CAMPAIGN`, `Audio._debug()`.
4. Testfunktionen direkt aufrufen: `launchMission(i)`, `startEndless()`, `openCampaign('bteam')`, `fireMissile()`, `fireAGM()`, `updatePlayer(dt)`, `updateEnemyMissiles(dt)`, `damageBoss(n)`, `killEnemy(e)`, `onAirDestroyed()`, `destroyGround(gt)`, `onLanded(false)`, `onTakeoff()`.
- **Regel:** Kamera-/Gegner-/State-Fixes im **echten rAF-Loop mit Gegnern** verifizieren, nicht nur isolierte Funktionsaufrufe (Lektion aus dem LEASH_SOFT-Crash).
- Headless: SwiftShader ~20 fps (real 60+), Shader kompilieren/validieren aber. Scratchpad-Skripte lagen unter dem Session-Scratchpad (`.mjs`-CDP-Harnische).
- **Review-Prozess:** größere Änderungen wurden über **Multi-Agent-Workflows** (parallele Prüf-Perspektiven → verifizierende Synthese) adversarisch reviewt; bestätigte Funde gefixt + per CDP nachgetestet. Diese Session lief mit „Ultracode" (Workflows als Default für substanzielle Aufgaben).

---

## B. alo-tower – lokale Musik-KI

### B1. Zugang
- **`alo-tower`** = Windows 11 Pro Tower, **SSH-Alias `alo-tower`** (Key-Auth, kein Passwort): HostName **192.168.178.88**, User **snofl**, **NVIDIA RTX 3090 (24 GB)**.
- **Default-Shell ist PowerShell** → verschachtelte Quotes über SSH sind die Hölle. **Robustes Muster:** Befehl base64-kodieren und via `-EncodedCommand` schicken:
  ```bash
  CMD=$(python3 -c "import base64;print(base64.b64encode(PS.encode('utf-16-le')).decode())")
  ssh alo-tower powershell -NoProfile -EncodedCommand "$CMD" 2>&1 | LC_ALL=C tr -d '\r\000'
  ```
  (`LC_ALL=C tr` gegen „illegal byte sequence" bei UTF-16-Ausgaben; CLIXML-Progress-Rauschen wegfiltern.)
- **Dateien remote schreiben:** `[IO.File]::WriteAllBytes(path, [Convert]::FromBase64String(b64))` (nicht `Set-Content -Encoding utf8` → schreibt BOM; Python verträgt führendes BOM, aber `ast.parse` stolpert).
- **Hintergrundprozesse sterben, wenn die SSH-Session schließt** (Windows sshd killt Session-Kinder) → **Scheduled Tasks** nutzen: `schtasks /Create /TN name /TR "powershell -NoProfile -ExecutionPolicy Bypass -File ..." /SC ONLOGON /F` + `schtasks /Run /TN name`. (Nicht `Start-Process`; die Register-ScheduledTask-Cmdlet scheiterte am Konten-SID-Mapping → `schtasks.exe` nutzen.) snofl ist interaktiv eingeloggt (Konsole), daher laufen ONLOGON-Tasks.
- Firewall-Regeln (brauchen Admin; SSH-Session als snofl HAT Admin): `New-NetFirewallRule -DisplayName ... -Direction Inbound -Action Allow -Protocol TCP -LocalPort <p> -Profile Any`.
- Lange Installs/Generierungen laufen als Task, in eine Logdatei; per erneutem SSH pollen (auf ein `DONE`-Marker warten).

### B2. ACE-Step
Schnelle Instrumental-/Song-Generierung. Verzeichnis **`D:\ace-step-studio`** (alles auf D:, nichts auf dem Mac).
- venv (Python 3.11, torch 2.6.0+cu124), `ACE-Step`-Repo (editable), `checkpoints` (~7,7 GB, `ACE-Step/ACE-Step-v1-3.5B`), `hf`-Cache, `outputs` (*.wav), `logs`.
- API: `from acestep.pipeline_ace_step import ACEStepPipeline; p=ACEStepPipeline(checkpoint_dir=r"D:\ace-step-studio\checkpoints", dtype="bfloat16"); p(format="wav", audio_duration, prompt=<Komma-Tags>, lyrics=<Text oder "[inst]">, infer_step, guidance_scale, scheduler_type, manual_seeds=[seed], save_path=...)` → gibt `[wav_path, params]`. Modell lädt einmal (~30–60 s), dann ~7 s/Clip (Diffusion ~5 s).
- **MCP-Server** (Fernsteuerung): `D:\ace-step-studio\mcp_server.py` = **FastMCP** (`pip install fastmcp`; `mcp.server.fastmcp` ist in mcp 2.x weg → standalone `from fastmcp import FastMCP`), streamable-http auf 0.0.0.0:8765 → **`http://192.168.178.88:8765/mcp`**. Tools: `generate_music(prompt,lyrics,duration,infer_step,guidance_scale,scheduler_type,seed,audio_format)`, `list_outputs`, `server_status`. In Claude Code registriert als **`ace-step`** (`claude mcp add --scope user --transport http ace-step http://192.168.178.88:8765/mcp`) — Tools laden beim nächsten Session-Start. Task `ace-step-mcp` (ONLOGON).
- **Anhören:** Browser-Player **`http://192.168.178.88:8766/`** (`player_server.py`, Task `ace-step-player`, listet outputs mit `<audio>`). Optional Gradio-Studio auf Abruf: `schtasks /Run /TN ace-step-studio` → `:7865`.
- ffmpeg fehlt (wav via soundfile ok). WAVs zum Verschicken komprimieren: macOS `afconvert -f m4af -d aac -b 160000 in.wav out.m4a` (Datei-Upload-Limit 30 MB; 90 s wav ≈ 33 MB).

### B3. YuE
Bessere **Gesangs**-Qualität (Nutzer bevorzugt es). Verzeichnis **`D:\yue-studio`** (eigenes venv — YuE-Deps kollidieren mit ACE-Steps gepinntem transformers).
- Repo `multimodal-art-projection/YuE` unter `D:\yue-studio\YuE`; Codec `xcodec_mini_infer` via `huggingface_hub` nach `YuE\inference\`. **`infer.py` gepatcht: `flash_attention_2` → `sdpa`** (flash-attn = Windows-Albtraum; sdpa + Default-Offload passt 2 Segmente in 24 GB). Modelle (`m-a-p/YuE-s1-7B-anneal-en-cot` ~15 GB + `YuE-s2-1B-general`) laden bei erster Generierung nach `D:\yue-studio\hf`.
- **LANGSAM:** ~2–3 min/Segment (Stage 1); 2-Segment-Song ≈ 14 min. Output = Mix + getrennte Vocal-/Instrumental-Spuren (mp3).
- **Web-UI** (was der Nutzer wollte): `D:\yue-studio\yue_webui.py` = **Gradio 6** auf **`http://192.168.178.88:7870/`** (Genre/Lyrics-Formular + Regler + Mix/Vocal/Instr-Player + History; shellt pro Generierung `infer.py`). Task `yue-webui` (ONLOGON), Firewall 7870.
- transformers 5.x ist installiert und funktioniert mit dem sdpa-Patch; falls YuE-Updates brechen, transformers auf 4.x pinnen.

### B4. VRAM
YuE (7B) und ACE-Step passen **nicht gleichzeitig** in die 24 GB. Für YuE wurde der `ace-step-mcp`-Task gestoppt (Prozess mit `player_server.py`/`mcp_server.py` gezielt per CommandLine-Match killen, NICHT pauschal `python.exe`). Faustregel: **ein großes Modell zur Zeit.** Möglicher nächster Schritt: automatisches Umschalten (das eine stoppen, wenn das andere gebraucht wird).

---

## C. Arbeitsweise & Konventionen
- **Deutsch** in allen Spieltexten und in der Kommunikation mit dem Nutzer.
- Nutzer-Stil: entscheidungsfreudig, mag Tiefe („alles vollgas", „mach das"), will bei echten Design-Weichen aber gefragt werden (AskUserQuestion für Balance-Richtung, Musik-Ansatz etc.).
- Vor jedem Commit: JS-Syntax-Gate. Nach substanziellen Änderungen: CDP-Tests. Größere Sachen: Multi-Agent-Review-Workflow → Funde fixen → nachtesten → committen → pushen (Token-URL) → `update-ref`.
- Nichts liegt auf dem Mac fürs Tower-Projekt — alles auf `alo-tower` (D:). Generierte Songs zum Anhören temporär in den Scratchpad holen (scp) + als m4a schicken.

## D. Offene Ideen / mögliche nächste Schritte
- Flugsim: Balance-Feinschliff nach echtem Spieltest (Nutzer-Feedback abwarten). Evtl. Silber-Prestige-Stufe (~30 Sterne) mit CSS. B-Team-Cutscenes im „Bierdeckel-Look".
- Musik-KI: YuE auch als MCP-Tool (`generate_song_yue`) + Ausgaben in die Player-Seite routen; ffmpeg auf dem Tower installieren (direktes mp3); automatisches VRAM-Umschalten ACE-Step↔YuE; YuE ICL-Modus (Stil/Stimme von Referenz-Song).

## E. Fallstricke (hart erkämpftes Wissen)
- **git push zu DerAlo** nur via Token-URL + `gh auth switch`; danach `update-ref`.
- **Headless-Audio** braucht das Autoplay-Flag, sonst Context suspended (Gains 0) → viele „Test-Failures" waren in Wahrheit das.
- **Runway-Start-Missionen:** kein `waveDelay` (Doppel-Spawn). `updatePlayer` kehrt bei `onGround` früh zurück → Airborne-Logik (z. B. Raketen-Regen) läuft am Boden nicht.
- **JS TDZ:** `const` vor Initialisierung in heißem Pfad = Crash jeden Frame (LEASH_SOFT-Lektion) → Modul-Scope-Konstanten hochziehen.
- **Three.js r128:** `CapsuleGeometry` existiert nicht; per-Objekt-`PointLight` an Projektilen ändert die Szenen-Lichtzahl → Shader-Neukompilierung/Ruckler (entfernt).
- **PowerShell/SSH:** base64-`EncodedCommand`; Dateien per `WriteAllBytes` (kein BOM); Hintergrund nur via Scheduled Task; UTF-16-Ausgaben mit `LC_ALL=C tr` säubern.
- **Sieg-Fenster:** `winLocked` schützt den Sieg in den 2,6 s danach — nicht versehentlich entfernen.
- **maxHp:** alle STRUKTUR%-Anzeigen und Heals müssen `player.maxHp` (nicht 100) nutzen, sonst Weißwurst-Anzeigebug/Heal-Cap.

---
*Erstellt von Claude (Opus 4.8) als Übergabe. Aktuellster Stand immer im Git-Log von `DerAlo/himmelsbrand` und in den Memory-Dateien unter `~/.claude/projects/-Users-riedhammer-local-llm-test/memory/`.*
