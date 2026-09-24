# HANDOFF — Projektübergabe (HIMMELSBRAND + alo-tower Musik-KI)

> Vollständige Wissens- und Statusübergabe, damit auf anderen Geräten / mit anderen Agents nahtlos
> weitergearbeitet werden kann. Stand: nach dem großen Overhaul (Grafik, Sprachausgabe, Landung, Story,
> Bosse, UI) im September 2026, `main` auf GitHub. Zwei getrennte Projekte:
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
  - [A9. Audio (Musik + Engine + Sprachausgabe)](#a9-audio)
  - [A10. HUD, Einstellungen, Grafikstufen, Save, Juice](#a10-hud-progresssave-juice)
  - [A11. Balance-Stand](#a11-balance-stand)
  - [A12. Testen (headless Chrome via CDP, `tools/`)](#a12-testen)
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
- **Flugsim spielen:** online unter **https://deralo.github.io/himmelsbrand/** (GitHub Pages, Quelle `main` / Root).
  Lokal: `index.html` doppelklicken oder im Repo `npx serve .`. Braucht nur Internet fürs Three.js-CDN.
- **Repo:** `DerAlo/himmelsbrand` (öffentlich), Branch `main`. Aktuelle Arbeitskopie: Windows-Tower `D:\himmelsbrand`
  (früher Mac `/Users/riedhammer/local_llm_test/`).
- **Musik-KI:** Tower per `ssh alo-tower` (Windows). YuE-Web-UI: `http://192.168.178.88:7870/`. ACE-Step-Player: `http://192.168.178.88:8766/`. ACE-Step-MCP: `http://192.168.178.88:8765/mcp`.
- **Sprache:** Nutzer ist deutschsprachig → **alle Spieltexte & Kommunikation auf Deutsch**.

---

## A. HIMMELSBRAND – Flugsimulator

Arcade-Kampfflugsim: deutscher **Eurofighter** gegen die abtrünnige NATO-Drohnen-KI **HELIOS**.
**Eine HTML-Datei** (`index.html`, ~9300 Zeilen): Three.js r128 (CDN) + Web Audio API, prozedurale
unendliche Welt (Simplex Noise), keine Bild-/Modell-Assets. Dazu **`voice_clips.js`** (~6,5 MB, alle
vorgerenderten Sprachclips als data-URIs; wird nach dem Laden asynchron nachgeschoben, fehlt sie, laufen
stumme Untertitel). Repo-Dateien: `index.html`, `voice_clips.js`, `README.md`, `STORY.md` (Story-Referenz,
Stand des Codes), `B-TEAM.md` (Design-Bibel der Komödien-Kampagne), `HANDOFF.md` (diese Datei),
`tools/` (Test-Werkzeuge) und `tools/voice/` (TTS-Bake-Pipeline).

### A1. Repo, Build, Push
- **Kein Build.** Alles in `index.html`. Ändern → im Browser neu laden. Deploy = Push auf `main`
  (GitHub Pages baut automatisch, ~1 min; Status: `gh api repos/DerAlo/himmelsbrand/pages/builds/latest`).
- **Push vom Windows-Tower:** `gh` ist dort als `DerAlo` angemeldet, Git nutzt `wincred` → normales
  `git push origin main` genügt.
- **Push vom Mac (alt, zwei Konten):** Default-Konto `riedhammer_agenda` hat keinen Zugriff →
  ```bash
  gh auth switch --user DerAlo >/dev/null 2>&1
  git push "https://x-access-token:$(gh auth token)@github.com/DerAlo/himmelsbrand.git" main
  git update-ref refs/remotes/origin/main HEAD   # Token-URL-Push aktualisiert origin/main nicht
  ```
- **Pre-Commit-Gate (immer):** `node tools/jsgate.mjs index.html` → muss „JSGATE OK" melden
  (prüft alle Inline-Skripte und `voice_clips.js`).
- **Commit-Trailer:** laut Vorgabe der jeweiligen Session (`Co-Authored-By: …` + `Claude-Session: …`).

### A2. Architektur
Ein Haupt-`<script>` in `index.html`, in nummerierte Sektionen gegliedert (Kopfkommentare `N. TITEL`):
`0` CFG · `0b` HELIOS-Kampagne · `0b2` B-Team · `0c` Save · `1` Noise · `2` Audio · `2b` Voice ·
`3` Renderer/Kamera (+Auto-Qualität) · `4` Himmel/Licht · `4b` Schatten/Atmosphäre · `5` Terrain ·
`5b` Szenerie (instanziert: Wälder, Dörfer, Felsen, Fernland) · `6` Wolken · `7` Partikel · `8` Flugzeugmodelle ·
`9` Spieler · `10`–`10c` Waffen/Bodenziele · `11` Gegner · `12` Input · `13` Lock · `14` HUD ·
`15` Spielzustand/Wellen · `15a2` Einstellungen · `15b` Tageszeit · `15c` Funk/Untertitel/Ziel-HUD ·
`15d` Missions-Runtime · `15d2` Ally · `15e` Boss-Framework · `15e2` Boss-Modelle/-KI · `15f` Story-Trigger/Barks ·
`16` Update · `16a` Rollen am Boden · `16b` Landung (Aufsetzen, FX, PAPI, Lande-HUD) · `17` Kamera · `18` Hauptschleife.
Globale Infrastruktur (direkt nach `CFG`) — neue Subsysteme hängen sich hier ein, statt die Schleife zu editieren:
- `GFX` — Grafikstufe (`quality` = Wahl `auto|high|medium|low`, `level()` = effektiv, `onChange(fn)`, `autoDowngrade()`). Siehe A10.
- `HOOKS` — `update(dt)`, `always(dt,rawDt)`, `preRender(rawDt)`, `missionStart(def,i)`, `reset()`; werfende Hooks werden geloggt + entfernt.
- `EV` — Event-Bus (`EV.on/emit`): `kill`, `groundKill`, `playerHit`, `missileWarn`, `lock`, `allyHit`, `missionEnd`,
  `takeoff`, `bossSpawn/bossPart/bossPhase/bossExposed/bossHp/bossKilled`, `voiceClips` … — Barks, Voice, FX hören nur zu.
- `parseLine('SPRECHER|Text|Hinweis')` — einheitliches Zeilenformat für Funk/Story; der Hinweis (z. B. `ruhig`, `dringend`,
  `wuetend`) steuert nur die TTS-Aussprache und ändert den Clip-Key nicht.
- `disposeTree(obj)` — Geometrien entfernter Objekte freigeben (Materialien/Programme bleiben geteilt).
- `CFG` — zentrale Tunables (Geschwindigkeiten, Waffen, **Landung** ab „Ground handling"/„Landing feel").
- `CAMPAIGN[]` (20 HELIOS-Missionen) und `BTEAM_CAMPAIGN[]` (7), `CUTSCENES{}` + `BTEAM_CUTSCENES{}`.
- `player`, `enemies[]`, `missiles[]`, `enemyMissiles[]`, `bombs[]`, `bullets[]`, `groundTargets[]`, `boss`, `ally`.
- Kernschleife `loop(now)`: `rawDt` (Echtzeit; Juice/Timer/HUD/Voice) vs. `dt = rawDt*ts` (Welt/Physik; friert bei hitStop/slowmo).
- `state`: `'menu' | 'playing' | 'paused' | 'gameover' | 'cutscene'`. `gameMode`: `'menu' | 'campaign' | 'endless'`.
- Zwei Kampagnen: `activeCampaign` (Zeiger auf `CAMPAIGN` oder `BTEAM_CAMPAIGN`) + `campaignId` (`'helios' | 'bteam'`).

### A3. Flugmodell & Kamera
- **Stabilisiertes Arcade-Modell:** absolute `heading` (Gier) + `pitch` werden **jedes Frame neu** aus Eulerwinkeln aufgebaut → kann nie invertieren; `roll` ist rein kosmetisch. Pitch ungeklammert/gewrappt → volle Loopings.
- **Energie-Kampf:** Wenderate hängt von Airspeed ab. `playerTurnMultFor(sp)` lerpt **2.0→0.95** (min→boost); `TURN_RATE=1.5*mult` → 3.0 rad/s bei min, ~1.43 bei boost. Gegner: `turnMultFor` lerpt 1.5→0.5 (klar unterlegen). **Fairness-Cap:** Ass `baseTurn*turnMul ≤ 1.85` < Spieler-Langsam-Turn 3.0. Skill = bremsen (Strg) und in den Rücken ziehen.
- **Kamera:** roll-frei (Horizont bleibt waagerecht), folgt Pitch durch Loopings. Früherer Bug: Kamera-Hochachse sprang am senkrechten Scheitel → gefixt mit `leanFade` (blendet Neigung nahe senkrecht aus) + Lerp-Glättung. Yaw-Vorzeichen mit Hysterese (`player.yawSign`).
- **Start:** `start:'runway'` setzt das Flugzeug still auf eine `buildRunway()`-Piste (Ressourcen einmal gebaut, pro
  Mission wiederverwendet). Vr `CFG.rotateSpeed`, Abheben `CFG.liftoffSpeed`, danach blendet der Steigpfad über
  `liftBlend` ein. **Luftstart:** Fahrwerk eingefahren. **Jeder Missionsstart:** Lenkrakete vorausgewählt.
- **Landung (Sektion 16b):** 3°-Gleitpfad (`glideDeg`) zum Aufsetzpunkt `aimDist` hinter der Schwelle, PAPI-Lichter +
  Tower-Callouts von **KIEBITZ** (zu hoch/zu tief/zu schnell, Fahrwerk), Lande-HUD mit Gleitpfad-Anzeige.
  Auto-Flare erst unter `flareHeight` und mit begrenzter Rate (`flareRate`) → ein schlechter Anflug bleibt schlecht.
  Kosmetischer Anstellwinkel (`aoaApproach/aoaFlare`), lageabhängige Radhöhe (Hauptfahrwerk setzt zuerst auf),
  Federbein (`gearK/gearC`), Bugrad nach `noseHold` mit `derotRate` abgesenkt, Autobrake, Reifenrauch/Quietschen/
  Rumpeln. Benotung in `landingTouchdown`: butterweich / sauber / hart / Crash nach Sinkrate (`touchGood`,
  `touchHard`, `touchSoftFrac`) + Ausrichtung (`touchAlignGood`). Fahrwerk: Taste **B** (`player.gearDown`).

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
Gemeinsames Framework in **15e**, Modelle + KI pro Art in **15e2**. `spawnBoss(kind, finale)`; die Art kommt aus
`def.spawns.boss`, `BOSS_BY_MISSION = { m12:'prometheus', m13:'feuertraeger', b6:'himmelszelt' }` überschreibt.
Teile (`bossPart`-Bodenziele) zerstören → `checkBossExpose()` legt den Kern frei → `damageBoss` → `killBoss`.
Jede Phase/HP-Schwelle feuert ein EV-Event (`bossSpawn/bossPart/bossPhase/bossExposed/bossHp/bossKilled`), die
Story-`mid[]`-Tabellen und Boss-Funksprüche hängen daran. `bossGen` wird bei jedem `clearBoss` erhöht → alte
`setTimeout`s eines vorherigen Kampfes werden zu No-ops. Telegrafie-Sounds werden auf `Audio.ctx()/out()` gebaut.
- **KRONOS · Drohnenwerft** (m5): schwebende Werft, Türme = Teile, Drohnenstart mit 1,5 s Bernstein-Blink-Telegraph.
- **DAS AUGE · HELIOS-Kern** (m7): Pylonen mit SAM, „Suchblick"-Strahl (1,8 s Telegraph, dann Puls entlang der
  eingefrorenen Linie), Blende öffnet sich beim Freilegen; in Phase 3 stellt HELIOS das Feuer ein.
- **PROMETHEUS · Kern im Schwarzkar** (m12, Wahl-Mission): P1 „Der Käfig" (Kern unverwundbar), danach Zyklus aus
  Schwarmsalven (3 Raketen, `ENEMY_MSL_CAP` gilt) und „Vorausberechnung"-Markern (zielt auf die vorhergesagte Position).
- **FEUERTRÄGER · Kellers Festung** (m13, Finale): Panzerplatten fallen mit eigener Physik ab (`fallingPlates`),
  Kammer-Glüh-Telegraph, Todessequenz mit Rettungskapsel (`escapePod`).
- **HIMMELSZELT · Fliegende Festung** (b6, B-Team-Finale): Bierzelt-Dach mit weiß-blauen Rauten, nutzt ebenfalls die
  Vorausberechnung.
- Kern nimmt nur halben Gun-Schaden → Raketen-/AGM-Job. `finale`-Bonus (+25 % Kern-HP) nur für kronos/auge, die neuen
  Arten haben ihre Final-HP schon eingebaut. HP-Balken zeigt während der Schildphase den Teil-Fortschritt.
- `killBoss` hat einen Re-Entry-Guard (`boss.dead`); nicht entfernen.

### A7. Kampagnen-Runtime & Missionen
- Laufzeit: `mission` + `setupMission(i)` / `updateMission(dt)` / `checkMissionComplete` / `checkMissionFailed`. `launchMission(i)`, `startEndless(mod)`, `gotoMenu()`, `resetWorld()`.
- **Objective-Kinds:** `destroyAir`, `destroyGround` (tag), `boss`, `minHP` (Constraint: done=!failed), `takeoff`, `land`, `protect` (Ally lebt), `reach` (über einen Wegpunkt fliegen, z. B. Bierkiste).
- **Sieg-Fenster-Schutz:** Nach Sieg 2,6 s Feier; `winLocked=true` verhindert, dass Rest-Feuer den Sieg in eine Niederlage kippt. Reset in `resetWorld`.
- HELIOS = 20 Missionen: Akt I `m0..m7`, Akt II `m8, m9, m_rueckenwind, m_nachtwache, m10, m_asche, m_grenzgaenger, m_fallwind, m_versprechen, m11, m12, m13`. Ids sind stabile Strings; `SAVE.missions` ist id-gekeyt; Unlock ist **index-basiert** → Einfügen weiterer Missionen ist sicher.
- Story: moralischer Twist (PROMETHEUS ist der wahre Feind, HELIOS war ein Schild, KELLER der Strippenzieher dahinter). Charaktere: Spieler „Geier", Oberst Wagner, **Hauptmann Lärche** (eskortierbarer Ally, `ally`, `spawnAlly({name,full,color,hp})`), KELLER, KIEBITZ (Tower). `storyChoice` ('trust'|'human') wird in m12s `choice`-Cutscene gesetzt und färbt Ende/Epilog/m13-Variante. Details/volle Doku: **`STORY.md`** (Repo-Root).
- Zwischensequenzen: `showCutscene(key, after)` (liest `CUTSCENES` **und** `BTEAM_CUTSCENES`). `ending` ist dynamisch (`cs.variants[storyChoice]`, VO-ID `'ending_'+storyChoice`); `epilog` routet per `cs.route` auf `epilog_trust`/`epilog_human` (eigene Keys = eigene VO-IDs, ohne Wahl `human`). `cs.next` verkettet eine weitere Cutscene vor dem `after`-Callback (`choice` → `ending`). Kette: `m11 → helios_bitte → m12 → choice → ending → m13 → epilog`. Vor m0 läuft einmalig der Prolog (`def.cutsceneBefore`, Gate `SAVE.seenProlog`); nach der letzten Mission heißt der Debrief-Button „EPILOG ▶“. Beim Öffnen einer Cutscene wird die Funk-Queue geleert.
- **Missions-Varianten:** eine Mission kann `introVariants`/`winVariants`/`midVariants`/`spawnsVariants` (Key = `storyChoice`) neben ihren normalen Feldern tragen (aktuell nur m13). `setupMission` baut daraus ein `effDef`-Overlay (`mid` wird **angehängt**, nie ersetzt; `spawns` nur `.air` überschrieben, `.ground/.boss/.ally` bleiben unangetastet) und setzt `mission.def=effDef`. `openBriefing` zeigt entsprechend `storyVariants[storyChoice]` statt `m.story`, falls vorhanden.
- **Story-Trigger + Barks** (Sektion „15f“ direkt vor Sektion 16): ein einmalig registrierter Dispatcher liest pro Event die `mission.def.mid[]`-Tabelle und feuert **alle** passenden, noch nicht gefeuerten Zeilen (`on`: `airborne, time, progress, done, allyHp, hpLow, bossSpawn, bossPart, bossExposed, bossPhase, bossHp, bossKilled, landReady`; `delay` per `setTimeout`, gegen Altlasten per `missionGen` abgesichert). Story-Zeilen schneiden sich nie ab: ist der Kanal belegt, wird die Zeile 3,4 s später als `{t,line,mid:true}` in `mission.radioQueue` gestellt; beim Sieg fliegen diese raus und `win[]` spielt (auch über dem Debrief). Direkt gesprochene Story-Zeilen gehen als `radio(line,{prio:'crit'})`, Barks als `{prio:'bark'}` (globaler Abstand 7 s, Cooldown pro Ereignis, kein Sofort-Repeat, verworfen solange Funk läuft). Kiebitz-Startruf und -Landefreigabe sind Pflicht (`crit`); Aufsetz-Callouts gehören LANDING. `done` wird per Frame-Poll erkannt. **BOSSES emittiert** `bossSpawn {kind,name}`, `bossPart {kind,left}`, `bossExposed {kind,open}`, `bossPhase {kind,phase}`, `bossHp {kind,frac}` (genau 0.75/0.5/0.25), `bossKilled {kind}` — bis dahin bleiben die Boss-Zeilen stumm. `def.bossName` wird per Hook auf den laufenden Boss geschrieben. Details: `STORY.md`.
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
- **Sprachausgabe (`Voice`, Sektion 2b):** jede gesprochene Zeile (Funk + Cutscene-VO) läuft durch **einen**
  sequenziellen Scheduler: Untertitel und Clip starten gemeinsam, der Untertitel bleibt so lange wie der Clip
  (sonst Lesezeit-Schätzung), dazwischen eine kurze natürliche Pause. Prioritäten `crit` (nie verworfen, darf einen
  Bark unterbrechen) / `normal` (verfällt, wenn veraltet; `ttl`) / `bark` (nur in Stille, Cooldown pro Sprecher).
  Pro Sprecher eine FX-Kette (Funk-Bandpass + Squelch, kalter Synth-Chirp für HELIOS, Hall für STIMME, trocken für
  NARRATOR) + Musik-Ducking. API: `Voice.line(l, {prio, ttl, tag, delay})`, `lines([...])`, `playCutscene(body)`,
  `drop(pred)`, `stop()`, `busy()`, `setVolume()`. Standard **AN**, Toggle **V**, Lautstärke/Untertitel in den
  Einstellungen. Fehler werfen nie: ohne Clip läuft ein korrekt getimter stummer Untertitel.
- **Clips:** vorgerendert mit **Chatterbox TTS** (Resemble AI, MIT) bzw. Piper auf der RTX 3090, Pipeline in
  `tools/voice/` (README dort). Key = FNV-1a von `'SPRECHER|Text'` → **jede Textänderung braucht einen Re-Bake**
  dieser Zeile: `node tools/voice/extract_lines.mjs` (schreibt `D:/tts-bake/lines.json` selbst, nicht umleiten;
  bei `CUTSCENE_VO … DIFFERS` den `/*CVO*/`-Block aus `lines_cvo.json` übernehmen), dann
  `D:/tts-bake/venvs/cbx/Scripts/python.exe tools/voice/bake.py --only-missing --prune`. Abdeckung prüfen:
  `missingVoiceLines()` im laufenden Spiel muss leer sein. Casting (Referenzstimme, Parameter, Stimmungs-Deltas) in
  `tools/voice/casting.json`; Referenz-WAVs unter `D:/tts-bake/refs/`. Zeilen mit Laufzeitwerten (Zahlen) bleiben stumm.

### A10. HUD, Progress/Save, Juice
- HUD: DOM-Readouts (gated via `body.in-game`) + Canvas-Overlay (`drawHUD`): vorgerendertes Heading-Band,
  Pitch-Leiter an der echten Kamera, Reticle, Ziel-Boxen, LOCK/Boden-LOCK, CCIP, Radar, RWR-Raketenwarnung,
  Boss-Balken, Ally-Marker, Lande-Panel (`drawLandingHUD`, 16b). Typografie/Farben über CSS-Design-Tokens.
- **Einstellungen (15a2):** Grafikqualität (Auto/Hoch/Mittel/Niedrig), Stimme an/aus + Lautstärke, Untertitel, Musik.
  Alles in `localStorage` (`himmelsbrand_gfx`, `himmelsbrand_voice`, `himmelsbrand_voice_vol`, `himmelsbrand_subs`, …).
- **Grafikstufen (`GFX`):** Subsysteme lesen `GFX.level()` beim Bauen ihrer GPU-Ressourcen und bauen über
  `GFX.onChange` live um. Jeder Stufenwechsel kompiliert alle beleuchteten Shader neu (**~2 s Standbild** auf
  ANGLE/D3D11). **Auto-Monitor** (Sektion 3, `monitorAutoQuality`): nur bei `quality==='auto'` und `state==='playing'`,
  ignoriert die ersten 5 s jeder Mission, bewertet ein rollendes ~8-s-Fenster und schaltet erst nach 3 schlechten
  Bewertungen in Folge (p50 > 22 ms oder p90 > 40 ms) **eine** Stufe herunter. VSync-Aussetzer und Lade-Hänger dürfen
  ihn nie auslösen (siehe E).
- **Save:** `localStorage` Key `himmelsbrand_save` (`SAVE`, id-gekeyt). `rateMission` (1–3 Sterne: Struktur `hp/maxHp≥0.65`,
  Zeit `≤par` via `DEFAULT_PAR`, Finesse `hp/maxHp≥0.92` bzw. saubere Landung — ratio-basiert). Unlocks: `ace`
  (Endlos, nach Akt I) + `goldWings` (≥48/60 Sterne). `SAVE.storyChoice`, `SAVE.seenProlog`.
- **Juice:** hitStop/slowmo (via `rawDt` vs `dt`), `markHit`, `spawnDebris`/`updateDebris`, damageFlash, Kill-Combo (×2..×5).

### A11. Balance-Stand
Letzter Pass = „klare Fixes + moderate Schärfe" (Commit `952baba`). Leitidee: Überlegenheit soll sich **verdient** anfühlen → Bedrohung oben drauf (Elites/Bosse/SAMs beißen), Grunt-Sofortkills bleiben. Details siehe A4–A6 + Commit-Message. **Bewusst NICHT angefasst** (fühlt sich richtig an): Gun-TTK, aimAssist, Grunt-Kurvenvorteil. Balance ist iterativ — Nutzer wollte selbst spielen und Feinjustierung zurückmelden (mögliche Stellschrauben: Elite-`accuracy`, Boss-Kern-HP, SAM-Burst-Schaden/Kadenz, Endlos-Heal-Kurve, `playerTurnMultFor`).

### A12. Testen
Kein Playwright. Headless Chrome direkt via CDP (Node ≥ 22, eingebautes `WebSocket`/`fetch`) — fertig im Repo:
- `node tools/jsgate.mjs index.html` — Syntax-Gate (vor jedem Commit).
- `node tools/hbrun.mjs --root . --scenario <datei.mjs> --out <ordner> [--timeout s]` — startet einen statischen
  Server + Chrome headless mit **echter GPU** und `--mute-audio` (Ton läuft intern, ist aber nie hörbar), führt ein
  Szenario aus und gibt JSON aus (Exceptions, Konsolenfehler, Logs, Screenshots). Szenario-API im Dateikopf
  (`ev`, `shot`, `sleep`, `log`, `fps`, `errors`). **Achtung:** `ev(code)` läuft im globalen Scope → eigene
  Variablen in eine IIFE packen, sonst „Identifier … has already been declared" beim zweiten Aufruf.
- `SWEEP_MS=2500 SWEEP_SHOTS=1 node tools/hbrun.mjs --root . --scenario tools/sweep.mjs --out <ordner> --timeout 600`
  — Regressions-Sweep über alle 27 Missionen, Endlos, alle Cutscenes, Menü: Fehler, fps/p95, Draw-Calls, Dreiecke,
  Shader-Programme, Geometrien, Texturen, effektive Grafikstufe. `SWEEP_ONLY="helios:5,bteam:6,endless"` für Teilmengen.
  Referenz (RTX 3090, Stand Overhaul): 0 Fehler, 44–53 fps headless, ≤ ~1000 Draw-Calls, Programme stabil bei ~57,
  Stufe bleibt „high".
- `node tools/hbrun.mjs --root . --scenario tools/smoke.mjs` — schneller Rauchtest.
- Nützliche Globals: `state`, `player`, `enemies`, `groundTargets`, `boss`, `mission`, `GFX`, `Voice._debug()`,
  `Voice._trace()`, `missingVoiceLines()`, `collectVoiceLines()`, `launchMission(i)`, `startEndless()`,
  `showCutscene(k, cb)`, `damageBoss(n)`, `killEnemy(e)`, `onLanded(false)`, `onTakeoff()`.
- **Regel:** Kamera-/Gegner-/State-Fixes im **echten rAF-Loop mit Gegnern** verifizieren, nicht nur isolierte Funktionsaufrufe.
- **Review-Prozess:** größere Änderungen laufen als Multi-Agent-Workflow: Tracks in eigenen Worktrees/Branches
  (`ov/*`, `ov2/*`, `ov3/*`) → Integrationsbranch → Sweep → adversariales Review pro Track → Fixes → Sweep → `main`.

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
- Seit dem Overhaul wird direkt auf dem Tower gearbeitet (`D:\himmelsbrand`, Git Bash/PowerShell). Hat der Nutzer „freie Hand" gegeben (z. B. über Nacht): selbst entscheiden, nicht fragen, am Ende deployen und einen deutschen Bericht schreiben.
- Test-Audio **nie hörbar** abspielen (hbrun nutzt `--mute-audio`).

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
- **Shader-Neukompilierung = Standbild:** Alles, was die Zahl/Art der Lichter, Schatten oder Shader-Defines mitten in
  der Mission ändert (neue PointLights, `GFX`-Stufenwechsel, neue Material-Varianten), kompiliert alle beleuchteten
  Programme neu → ~2 s Freeze auf ANGLE/D3D11. Deshalb hält `prewarmFX()` die Flash-Lichter dauerhaft in der Szene, und
  neue Effekte nehmen Sprites/Partikel statt Lichter. Im Sweep an `progs` erkennbar (muss plateauen).
- **Auto-Qualität:** Der erste Monitor wertete Einzel-Frames und schaltete durch VSync-Aussetzer (16,7/33,3 ms-Mix) und
  Lade-Hänger mitten in der Mission herunter → genau die Freezes, die er verhindern sollte. Nur Perzentile über ein
  Fenster, Karenzzeit nach Missionsstart und mehrere Bewertungen in Folge.
- **Voice-Keys:** Clip-Key = Hash aus `SPRECHER|Text`. Tippfehler-Fix im Text = Clip weg (stummer Untertitel), bis neu
  gebacken wird. Der Sprechhinweis (3. Feld) ändert den Key nicht.
- **Zeilen mit Laufzeitwerten** (`'… '+n+' übrig'`) können nicht vorgebacken werden → bleiben stumm oder als feste
  Varianten schreiben.

---
*Erstellt von Claude (Opus 4.8), nach dem Overhaul aktualisiert von Claude (Opus 5.5). Aktuellster Stand immer im Git-Log von `DerAlo/himmelsbrand`.*
