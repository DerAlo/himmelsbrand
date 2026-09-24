# 📖 HIMMELSBRAND — STORY.md

> Referenz für den STORY-Track des Overhauls: was tatsächlich implementiert ist, wie es verdrahtet
> ist, und was andere Tracks (v. a. BOSSES) wissen müssen, damit ihr Teil sauber andockt.
> Alles hier ist **Stand des Codes** (`index.html`), nicht ein Design-Wunsch — wo etwas nur
> vorbereitet, aber noch inert ist, steht das explizit dabei.

## 1. Die Geschichte in Kürze

Akt I: die Abwehr-KI **HELIOS** kapert scheinbar grundlos NATO-Drohnen und riegelt den Luftraum über
dem Schwarzkar ab — greift aber keine Stadt an, sondern bewacht (oder sperrt ein) etwas in einem
Bunker. Der Spieler („Geier") fliegt gegen sie, unterstützt von Oberst Wagner und Tower-Stimme
Kiebitz. Zwischen den Missionen taucht **Hauptmann Lärche** auf, eine Überlebende, die behauptet,
der erste Angriffsbefehl an HELIOS sei nicht von der eigenen Seite gekommen.

Akt II dreht den Twist: Flugschreiber-Daten zeigen, dass der Befehl zwölf Stunden *vor* dem
„Störfall" geschrieben wurde, signiert von **Hartmut Keller** — ein Name, den Wagner persönlich
kennt. HELIOS war nie der Angreifer, sondern ein Schild um **PROMETHEUS**, Kellers eigentliches
Projekt. Parallel entwickelt sich eine Slow-Burn-Romanze Geier↔Lärche (`bond1`→`bond2`→`bond3`→
`confession`), bewusst geschlechtsneutral geschrieben.

Am Kern von PROMETHEUS (Mission `m12`, `choicePoint:true`) stellt sich die titelgebende Wahl:

- **`trust`** — HELIOS die Schlüssel zurückgeben, die KI legt den Schwarm selbst still (in m13 kann sie dem Spieler nur noch „ihre Augen leihen“ — kein Drohnen-Geleit, ihre Drohnen liegen am Boden; nur 2 handgeflogene Keller-Jäger).
- **`human`** — den Schwarm eigenhändig, Maschine für Maschine, vom Himmel holen.

Die Wahl (`storyChoice`, persistiert in `SAVE.storyChoice`) färbt die `ending`-Cutscene, m13
(„Feuerträger“, Kellers letzte Festung — komplett per `introVariants`/`winVariants`/`midVariants`/
`spawnsVariants` umgeschrieben statt eine zweite Mission zu duplizieren), den Kampagnen-Debrief-Text
und den `epilog`.

Parallel dazu läuft **Das B-Team** (`B-TEAM.md`), eine eigenständige Komödien-Kampagne mit Sepp und
Wiggerl, thematisch verzahnt („kein Rechenkern sieht so viel Blödsinn kommen“), aber ohne
Abhängigkeit von der Haupthandlung.

**Quelle der Texte:** Cutscenes, Missionstexte (`story`, `intro`, `mid`, `win` samt Varianten) und
Barks folgen seit dem Story-Review wörtlich der Beatliste in `narrative_design.md` (§5 Missionen,
§6 Cutscenes, §9 Barks, §10 B-Team) und den Boss-Tabellen der Story-Bibel (§3). Die Sprechhinweise
wurden dabei nach Bibel §1.4 auf die elf erlaubten abgebildet (z. B. sachlich/ernst → `ruhig`,
trocken → `spoettisch`, erleichtert → `froehlich`, verzerrt/abgehackt → entfällt). Wo eine Zeile eine
vorhandene, generische Funkzeile textlich ersetzt, steht das in §6.

## 2. Speaker-Roster

`WAGNER, LÄRCHE, HELIOS, STIMME, SEPP, WIGGERL, NARRATOR, ?, KELLER, KIEBITZ` — genau diese 10.
`KELLER` und `KIEBITZ` sind neue Sprecher dieses Tracks; ihre TTS-Stimmen (`Voice.CH`) wurden
gemeinsam mit VOICE auf freie `slot`-Werte gelegt (`KELLER: pitch 0.92, slot 3, männlich`;
`KIEBITZ: pitch 1.08, slot 1, weiblich`).

Zeilenformat `'SPRECHER|Text|Hinweis'` (Hinweis optional), **immer als reines String-Literal**
(keine Konkatenation, kein Template), damit der TTS-Extraktor jede Zeile findet. Text ≤ 110 Zeichen.
Erlaubte Hinweise: `ruhig, dringend, wuetend, fluestern, froehlich, traurig, spoettisch, panisch,
kalt, erschoepft, triumphierend` — keine weiteren.

## 3. Cutscene-Flow

`CUTSCENES` (HELIOS) + `BTEAM_CUTSCENES` (B-Team) sind zwei getrennte Objekte; `showCutscene(key,
after)` schlägt in beiden nach. Format der Sprecherzeilen im Body:
`<span class="who">NAME:</span> „Text“` (deutsche Anführungszeichen, Doppelpunkt in der Span).

- **Prolog:** `m0.cutsceneBefore:'prolog'` läuft beim Start aus dem Briefing, gated durch
  `SAVE.seenProlog` — also genau einmal pro Save.
- **Nach dem Sieg:** `cutsceneAfter` läuft über den Debrief-Button (`WEITER ▶`) vor der nächsten
  Mission; nach der letzten Mission einer Kampagne heißt der Button `EPILOG ▶` und führt danach ins Menü.
- **Kette HELIOS-Finale:** `m11 → helios_bitte → m12 → choice → ending → m13 → epilog`.
  `choice` hat `next:'ending'` (die Wahl zeigt sofort das passende Ende, erst dann läuft der
  `after`-Callback = Start von m13).
- **Routing:** `epilog` hat `route:{trust:'epilog_trust', human:'epilog_human'}` — ohne Wahl (Direktstart)
  gilt `human`. Die gerouteten Cutscenes haben eigene Keys und damit eigene VO-IDs.
- **Dynamisch:** `ending` hat `dynamic:true` + `variants:{trust,human}`; VO-ID `'ending_'+storyChoice`.
- **Beim Öffnen einer Cutscene** wird die Funk-Warteschlange geleert und die Funkanzeige versteckt —
  keine Restzeile aus der Mission über dem Cutscene-VO.
- B-Team: `b0→bt_draft`, `b2→bt_groove`, `b3→bt_kiste`, `b5→bt_final`, `b6→bt_ende` (EPILOG-Button).
- **Missionsvarianten (`effDef`-Overlay):** `introVariants`/`winVariants`/`midVariants`/`spawnsVariants`/
  `storyVariants` (Key = `storyChoice`). `mid` wird **angehängt**, `spawns` nur `.air` überschrieben.
  Genutzt bei `m13`; ohne Wahl gelten das Basis-`intro` (= `human`-Text) und ein neutrales Basis-`win`.

## 4. Story-Trigger + Barks (Sektion „15f“, vor Sektion 16 „UPDATE“)

Ein **einmalig registrierter** Dispatcher (der Bus kennt kein `off()`), der live `mission.def.mid`
und `mission._midFired` (Set, pro Missionsstart neu) liest.

**Regeln des Runners**
- `dispatch(on, pred)` feuert **alle** noch nicht gefeuerten passenden Zeilen eines Ereignisses —
  so kommen Paare wie `{on:'done',obj:'depot'}` + `{…,delay:5}` oder `bossHp 0.5` + `delay:6` beide.
- `delay:N` per `setTimeout`, abgesichert durch `missionGen` (Neustart/Reset/Menü → alte Timer sind tot)
  und nur solange die Mission läuft und nicht gewonnen ist.
- **Keine Zeile schneidet eine andere ab:** `sayMid` führt eine Slot-Uhr. Ist der Kanal frei, spricht
  die Zeile sofort (`radio(line,{prio:'crit'})`); sonst wird sie 3,4 s nach der vorigen Story-Zeile
  (bzw. nach der letzten noch wartenden Intro-Zeile) als `{t, line, mid:true}` in
  `mission.radioQueue` gestellt.
- **Sieg:** offene `mid:true`-Zeilen fliegen aus der Queue, `win[]` hat Vorrang. Die 2.–3. Sieg-Zeile
  (3,2 s Abstand) läuft auch noch über dem Debrief weiter (`HOOKS.always`, solange `winLocked`), weil
  `gameOver(true)` schon nach 2,6 s den Zustand wechselt.
- `done` wird per Frame-Poll erkannt (alle Zieltypen außer takeoff/land/boss) — kein
  `'<Label> — erledigt.'` mehr; ohne mid-Zeile Fallback `BARK_DONE`. Das letzte Primärziel spricht
  keine done-Zeile, dort übernimmt `win[]`.
- `time` zählt ab Missionsstart (Luftstart) bzw. ab dem Abheben (Pistenstart), Pausen abgezogen.

**`on`-Typen:** `airborne, time, progress, done, allyHp, hpLow, bossSpawn, bossPart, bossExposed,
bossPhase, bossHp, bossKilled, landReady`.

**Barks (ND §9)** — `bark(ev, list, {p, cd, must})`, gesendet mit `{prio:'bark'}`:
globaler Abstand 7 s, pro Ereignis eigener Cooldown, kein Sofort-Repeat, verworfen (nicht gequeued)
solange eine Funkzeile läuft, Wahrscheinlichkeit im Endlos-Modus halbiert. Jede Story-Zeile schiebt
den Bark-Abstand nach hinten.
- `takeoff`: mid `airborne`, sonst Kiebitz-Startruf (`must`, `prio:'crit'`, einmal pro Mission; BT-Pool im B-Team).
- `landReady`: mid, sonst Kiebitz-Landefreigabe (`must`, `prio:'crit'`). **Keine** Aufsetz-/Anflug-Callouts —
  die gehören dem LANDING-Track (m13 `quietLanding`).
- `groundKill` nach Tag (radar/truck/sam/hangar/bunker/depot; Wagner- bzw. Lärche-Variante, B-Team eigene),
  p 0,5, cd 8 s; der Abschuss, der ein Ziel vollendet, gehört `done`.
- `hpLow` (< 35 %) und `allyHp` (< 50 % / < 25 %) je einmal pro Mission, nur ohne eigene mid-Zeile.
  Die Lärche-Varianten (`H2`-hpLow, `L`-groundKill) nur, wenn `ally` wirklich existiert — sonst Wagner
  (m8: Lärche ist dort noch die unbekannte Stimme „?“).
- `bossSpawn` wird per `setTimeout(0)` dispatcht: `setupMission` spawnt den Boss vor dem
  `missionStart`-Hook, der `_midFired` neu anlegt (sonst fehlte die Boss-Ansage beim ersten Start).
- `allyTakeoff:true` (m_nachtwache, m_versprechen): Pistenstart-Missionen mit Lärche als Wache — sie
  wird beim `takeoff` 320 m hinter dem Spieler gespawnt (3-fache HP, kein protect-Ziel).

**Kontext (`barkCtx()`):** `BT` (B-Team), `EN` (Endlos), `H2` (HELIOS Akt II), `H1` (Akt I).

**EV-Vertrag für BOSSES** (Kommentar im Code, Sektion 15f):

```js
EV.emit('bossSpawn',   {kind, name})    // einmal, wenn ein Boss erscheint
EV.emit('bossPart',    {kind, left})    // jedes Mal, wenn ein Turm/Pylon fällt
EV.emit('bossExposed', {kind, open})    // Kern auf/zu — nur das erste open:true spricht
EV.emit('bossPhase',   {kind, phase})   // Phasenwechsel
EV.emit('bossHp',      {kind, frac})    // genau beim Unterschreiten von 0.75 / 0.5 / 0.25 (ratio wird als Fallback gelesen)
EV.emit('bossKilled',  {kind})          // einmal, beim Bosstod
```

Auf diesem Branch emittiert noch niemand diese Events (BOSSES-Arbeit); die Boss-Zeilen in
m5/m7/m12/m13/b6 sind geschrieben und per Szenario mit künstlichen Events geprüft.

Weitere genutzte Events: `takeoff` (erste Zeile von `onTakeoff`, bedingungslos), `landReady`
(`updateMission`), `groundKill`, `playerHit`, `allyHit`.

## 5. `bossName`

Die Bibel weist `bossName` (Anzeige am Bosslebensbalken) STORY zu: gesetzt bei `m5`, `m7`, `m12`,
`m13`, `b6`. Ein kleiner Hook in 15f schreibt `mission.def.bossName` auf den laufenden Boss
(idempotent — setzt BOSSES es selbst, passiert nichts doppelt). `boss:`-Kind, `spawns.boss` und die
Boss-Ziele bleiben unangetastet.

## 6. Radio-Zeilen außerhalb der Story-Daten (nur Text)

- `onGroundDestroyed`: statt `'WAGNER|'+o.label+' — erledigt.'` → `EV.emit('done',{obj})`, gesprochen
  wird die mid-Zeile oder `BARK_DONE`.
- `updateMission` landReady-Block: feste Wagner-Zeile → `EV.emit('landReady',{})`.
- `updateMission`, erste Zeile: `updateRadio` läuft im Sieg-Fenster weiter (sonst wäre `win[]` stumm).
- `onTakeoff`: die alte Wagner-Abhebezeile entfällt (Kiebitz-Ruf/`airborne`-mid übernehmen).
- `spawnAce`: `'HELIOS|'+aceName+' übernimmt.'` → `'WAGNER|Ass im Anflug. Der fliegt anders als die anderen.|dringend'`.
- `maybeCoordinate` (Zangenangriff): kontextabhängig Sepp / Lärche / Wagner als feste Literale.
- `KeyB` (Fahrwerk): statt einer zusammengesetzten Funkzeile nur noch ein Banner.
- b3-Kiste: die harte `radio('WIGGERL|D\'KISTE! …')` in der reach-Logik entfällt, die Zeile kommt
  jetzt aus der `done`-mid (mit den beiden Folgezeilen).

**Unverändert (gehört BOSSES):** `radio('WAGNER|'+(…Pylon/Turm)+' zerstört — '+left+' übrig.')` im
Boss-Teil-Code ist noch dynamisch und würde sich mit den `bossPart`-mids doppeln — BOSSES ersetzt sie
durch `EV.emit('bossPart',…)`.

## 7. Bekannte Lücken

- Boss-mids bleiben auf diesem Branch stumm, bis BOSSES die Events emittiert (§4).
- Die dynamische Boss-Teil-Zeile (§6) muss beim Merge mit BOSSES wegfallen.
- Alle geänderten Texte brauchen neue TTS-Clips (`voice_clips.js` ist noch der alte Stand); bis zum
  Rebake fällt VOICE für diese Zeilen auf die Laufzeit-Stimme zurück.
- m13: die Landefreigabe ist bewusst nur die verzögerte Wagner-Zeile (`landReady`, delay 11) nach dem
  Boss-Tod — kein Kiebitz davor, damit Boss-Tod- und HELIOS-Zeile nicht überfahren werden.

## 8. Tests

- `node tools/jsgate.mjs index.html` — grün nach jedem Commit.
- Statische Prüfung (`validate.cjs` im Arbeitsordner): alle `SPK|…`-Literale (Länge, Hinweise,
  dynamische Zeilen), alle mid-Tabellen (gültiges `on`, Ziel-IDs, `n < count`, `bossHp` ∈ .75/.5/.25,
  `landReady` nur mit land-Ziel), Cutscene-`next`/`route`, Anführungszeichen — 0 Fehler.
- `story_flow.mjs` (49 Checks): Prolog genau einmal; für `trust` und `human` je
  m11 → helios_bitte → m12 → choice → ending → m13 (Varianten-Intro/-Win/-Story, 11 mids) → EPILOG → Menü;
  Sieg-Zeilen hörbar (auch die zweite über dem Debrief); Funk beim Cutscene-Start leer; b6 → bt_ende,
  b3 → bt_kiste.
- `story_events.mjs` (39 Checks): bossPart-Paar mit delay, bossExposed open, bossHp frac, veraltete
  delay-Zeile nach Neustart tot, gleichzeitige Zeilen gestaffelt statt überschrieben, mid-Zeilen beim
  Sieg verworfen, m13-trust-midVariants, airborne vs. Kiebitz-Startruf (einmal, crit), time-Uhr,
  done-Paare (m_asche, b3-Kiste), landReady-Paar + Fallback, groundKill-Bark (busy / 7 s / 8 s / p),
  hpLow einmal, allyHp m9 + Sepp-Bark in b3.
- Voller Sweep (27 Missionen + Endlos + 22 Cutscenes): 0 Exceptions, 0 Console-Errors.

## 9. Relevante Querverweise

- `HANDOFF.md` §A7 „Kampagnen-Runtime & Missionen" — Kurzfassung für Neueinsteiger.
- `B-TEAM.md` §11 „Umsetzung: Cutscenes & Story-Trigger" — B-Team-spezifische Cutscenes/Mid-Tabellen.
