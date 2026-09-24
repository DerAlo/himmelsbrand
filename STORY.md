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
„Störfall" geschrieben wurde, signiert von **Konrad Keller** — ein Name, den Wagner persönlich
kennt. HELIOS war nie der Angreifer, sondern ein Schild um **PROMETHEUS**, Kellers eigentliches
Projekt. Parallel entwickelt sich eine Slow-Burn-Romanze Geier↔Lärche (`bond1`→`bond2`→`bond3`→
`confession`), bewusst geschlechtsneutral geschrieben.

Am Kern von PROMETHEUS (Mission `m12`, `choicePoint:true`) stellt sich die titelgebende Wahl:

- **`trust`** — HELIOS die Schlüssel zurückgeben, die KI stoppt den Kamikaze-Schwarm selbst.
- **`human`** — den Schwarm eigenhändig, Maschine für Maschine, vom Himmel holen.

Die Wahl (`storyChoice`, persistiert in `SAVE.storyChoice`) färbt die `ending`-Cutscene, m13
(„Feuerträger", Kellers letzte Festung — komplett per `introVariants`/`winVariants`/`midVariants`/
`spawnsVariants` umgeschrieben statt eine zweite Mission zu duplizieren), den Kampagnen-Debrief-Text
und den `epilog`.

Parallel dazu läuft **Das B-Team** (`B-TEAM.md`), eine eigenständige Komödien-Kampagne mit Sepp und
Wiggerl, thematisch verzahnt („kein Rechenkern sieht so viel Blödsinn kommen"), aber ohne
Abhängigkeit von der Haupthandlung.

**Offenlegung:** die Cutscene-Texte (Prolog, Keller-Anruf, Reveal, Wahl, beide Enden, Epilog,
bt_kiste/bt_ende) und die meisten Funk-Barks in diesem Dokument sind originale Kompositionen des
STORY-Tracks im Sinn der bestehenden Erzähl-Bibel/`narrative_design.md`-Beatliste — keine
wortwörtliche Abschrift eines vorgegebenen Skripts. Wo eine Zeile eine bereits vorhandene, generische
Funkzeile textlich ersetzt (siehe §5), ist das einzeln aufgeführt.

## 2. Speaker-Roster

`WAGNER, LÄRCHE, HELIOS, STIMME, SEPP, WIGGERL, NARRATOR, ?, KELLER, KIEBITZ` — genau diese 10.
`KELLER` und `KIEBITZ` sind neue Sprecher dieses Tracks; ihre TTS-Stimmen (`Voice.CH`) wurden
gemeinsam mit VOICE koordiniert (siehe `contracts`/Commit-Historie) auf freie `slot`-Werte gelegt
(`KELLER: pitch 0.92, slot 3, männlich`; `KIEBITZ: pitch 1.08, slot 1, weiblich`), um keine
Kollision mit den bereits vergebenen Slots zu erzeugen.

Erlaubte Sprechhinweise (drittes `|`-Feld): `ruhig, dringend, wuetend, fluestern, froehlich, traurig,
spoettisch, panisch, kalt, erschoepft, triumphierend` — keine weiteren.

## 3. Cutscene-Flow

`CUTSCENES` (HELIOS-Kampagne) + `BTEAM_CUTSCENES` (B-Team) sind zwei getrennte Objekte;
`showCutscene(key, after)` schlägt in beiden nach.

- **Prolog/Epilog-Hooks:** eine Mission kann `cutsceneBefore` (läuft beim ersten `openBriefing`-Aufruf
  vor dem eigentlichen Start, gated durch `SAVE.seenProlog` — läuft also nur einmal pro Save) und
  `cutsceneAfter` (läuft nach dem Sieg-Debrief, vor der nächsten Mission bzw. als „EPILOG ▶"-Button
  nach der letzten Mission einer Kampagne) tragen.
- **Verkettung:** `cs.next` hängt automatisch eine weitere Cutscene an, bevor der reale `after`-Callback
  läuft — genutzt für `choice` → `ending` (der Spieler trifft die Wahl, sieht sofort die passende
  Ending-Cutscene, danach erst geht es zurück ins Debrief/Menü).
  Kein anderer Track sollte `cs.next` ohne Rücksprache in bestehende Ketten einfügen — es ist reine
  Ablauflogik dieses Tracks.
- **Dynamische Varianten:** `cs.dynamic:true` + `cs.variants:{trust:{...}, human:{...}}` wählt Titel/
  Body nach `storyChoice`; die Voice-Over-Lookup-ID ist dabei `key+'_'+storyChoice` (z. B.
  `ending_trust`) — das ist der gemeinsame Berührungspunkt mit VOICE (`CUTSCENE_VO`-Tabelle), unverändert
  in ihrer Zuständigkeit, aber die ID-Konvention gehört zu diesem Vertrag.
- **Missionsvarianten (`effDef`-Overlay):** `introVariants`/`winVariants`/`midVariants`/
  `spawnsVariants` (Key = `storyChoice`) neben den normalen Feldern einer Mission. `setupMission`
  baut daraus zur Laufzeit ein Overlay (`mid` wird **angehängt**, nie ersetzt; `spawns` nur `.air`
  überschrieben — `.ground/.boss/.ally` bleiben immer die des Basis-`def`) und arbeitet danach
  ausschließlich mit `mission.def = effDef`. Aktuell nur bei `m13` genutzt. `openBriefing` zeigt
  passend dazu `m.storyVariants[storyChoice]` statt `m.story`, wenn vorhanden.

## 4. Story-Trigger + Barks (Sektion „15f", vor Sektion 16 „UPDATE")

Ein **einmalig registrierter** Dispatcher (kein Re-Register pro Mission — das würde `EV`-Handler
stapeln, da der Bus kein `off()` kennt). Er liest bei jedem relevanten Event live `mission.def.mid`
und `mission._midFired` (ein `Set`, pro Missionsstart geleert) und spricht die erste noch nicht
gefeuerte, passende Zeile; ohne Treffer fällt er auf einen kontextabhängigen Bark zurück
(`BARK_LANDREADY`, `BARK_DONE`; Cooldown 7 s, kein sofortiges Wiederholen, keine Wiederholung des
zuletzt gepickten Satzes bei Pools mit mehreren Optionen).

**Unterstützte `mid[]`-`on`-Typen:** `airborne, time, progress, done, allyHp, hpLow, bossSpawn,
bossPart, bossExposed, bossPhase, bossHp, bossKilled, landReady`. `delay:N` verzögert eine Zeile um
N Sekunden per `setTimeout`, abgesichert durch einen `missionGen`-Zähler (wird bei jedem
Missionsstart/-reset hochgezählt), damit ein Timer aus einer bereits verlassenen Mission nicht mehr
spricht.

**Kontext (`barkCtx()`):** `BT` (B-Team), `EN` (Endlos/Nicht-Kampagne), `H2` (HELIOS Akt II), `H1`
(HELIOS Akt I) — steuert, welcher Bark-Pool-Eintrag gezogen wird.

**EV-Vertrag für BOSSES** (Kommentar direkt im Code, Sektion 15f): damit die bereits geschriebenen
`bossSpawn`/`bossPart`/`bossExposed`/`bossHp`-Zeilen in `m5`/`m7`/`m12`/`m13`/`b6` überhaupt sprechen,
muss der BOSSES-Track aus `updateBoss`/`checkBossExpose` (oder wo immer die Boss-Logik jetzt sitzt)
diese Events feuern:

```js
EV.emit('bossSpawn',   {})            // einmal, wenn ein Boss erscheint
EV.emit('bossPart',    {left:N})      // jedes Mal, wenn ein Panzerungs-/Schwachpunkt-Teil stirbt
EV.emit('bossExposed', {open:bool})   // jedes Mal, wenn die Kernabdeckung auf-/zugeht
EV.emit('bossPhase',   {phase:N})     // bei jedem Phasenwechsel
EV.emit('bossHp',      {ratio:0..1})  // bei jeder Boss-HP-Änderung
EV.emit('bossKilled',  {})            // einmal, beim Bosstod
```

**Bestätigt per `grep`:** keines dieser sechs Events wird im aktuellen Code irgendwo emittiert — das
ist erwartete Integrations-Restarbeit für BOSSES, kein Bug. Bis dahin bleiben alle boss-bezogenen
`mid[]`-Zeilen inert (sie werden nie gefunden, `findMid` gibt `null` zurück, kein Fallback-Bark
springt für sie ein, weil `bossHp`/`bossPart` etc. keine Fallback-Pools haben).

**Bereits genutzte, vorbestehende Events** (keine Änderung nötig): `takeoff` (aus `onTakeoff`),
`landReady` (aus `updateMission`s landReady-Block, jetzt hier statt einer festen `radio(...)`-Zeile),
`done` (`onGroundDestroyed`, jetzt ohne String-Konkatenation), `allyHit`/`playerHit` (bereits vorher
vorhanden, nur konsumiert, nicht verändert).

## 5. `boss:`/`bossName`-Feld-Entscheidung (dokumentierte Konfliktlösung)

Die projektweite Design-Bibel (§4.5) weist `bossName` (den Anzeige-String am Bosslebensbalken)
explizit STORY zu, während eine allgemeinere Harness-Anweisung nahelegt, gar keine
Boss-bezogenen Felder anzufassen. Entschieden: **Bibel schlägt generische Anweisung.** Ich habe
`bossName:` bei `m5`, `m7`, `m12`, `m13`, `b6` gesetzt (Anzeige-Strings wie `'KRONOS · DROHNENWERFT'`,
`'PROMETHEUS · KERN IM SCHWARZKAR'`, `'FEUERTRÄGER · KELLERS FESTUNG'`, `'HIMMELSZELT · FLIEGENDE
FESTUNG'`). Das `boss:`-Kind-Feld (welcher Bosstyp gebaut wird, z. B. `'kronos'`/`'auge'`) und alle
`spawns.boss`/`spawns.air`-Felder außerhalb meiner eigenen `spawnsVariants` habe ich **nicht**
angefasst — das bleibt vollständig BOSSES' Territorium.

## 6. Radio-Zeilen, die als reiner Text ersetzt wurden (Lizenz „Text ja, Logik nein")

Alle folgenden Änderungen sind **nur** Text-/Konkatenations-Fixes an bestehenden Aufrufstellen, keine
neue Logik, keine verschobenen Verantwortlichkeiten:

- `onGroundDestroyed`: `radio('WAGNER|'+o.label+' — erledigt.')` → jetzt ein `EV.emit('done',{obj})`,
  gesprochen wird die passende `mid[]`-Zeile oder ein `BARK_DONE`-Fallback (keine generische
  Konkatenation mehr).
- `updateMission`s landReady-Block: die feste `'WAGNER|Auftrag erfüllt — bring sie nach Hause...'`
  wurde durch `EV.emit('landReady',{})` ersetzt (→ `mid[]`/`BARK_LANDREADY`).
- `spawnAce`: `radio('HELIOS|'+e.aceName+' übernimmt.')` (Konkatenation, Ass-Name gehörte da nie
  gesprochen rein) → feste Zeile `'WAGNER|Ass im Anflug. Der fliegt anders als die anderen.|dringend'`.
  Der Ass-Name bleibt weiterhin im Banner (`banner(...)`, unverändert, nicht meine Zuständigkeit).
- `maybeCoordinate` (Zangenangriff-Ansage): `radio('HELIOS|Zangenangriff — sie teilen sich auf.')` →
  kontextabhängig über `barkCtx()`: `SEPP`-Zeile im B-Team, `LÄRCHE`-Zeile in Akt II, sonst `WAGNER`.
- `KeyB`-Fahrwerk-Toggle: `radio('WAGNER|Fahrwerk '+(...)+'.')` → zwei feste Literale (ausgefahren/
  eingefahren) statt Laufzeit-Konkatenation. **Dies ist eine generische Gameplay-Statuszeile, keine
  STORY-Daten** — als Fremd-Edit aufgeführt, weil sie außerhalb der Sektion-0b/15f-Kerndaten liegt,
  aber unter der Lizenz „Radio-String-Literale überall reparieren dürfen" gedeckt ist.

**Bewusst UNVERÄNDERT gelassen** (Übergangsregel — gehört BOSSES): `destroyGround`s
Boss-Teil-Zerstörungszeile `radio('WAGNER|'+(boss.kind==='auge'?'Pylon':'Turm')+' zerstört — '+left+'
übrig.')` ist noch die alte, hartcodierte Konkatenation. Sie sollte durch
`EV.emit('bossPart',{left})` (→ dann automatisch von Sektion 15f gesprochen, siehe §4) ersetzt
werden — das ist BOSSES' Umbau, nicht meiner, um keine Boss-Logik-Datei fremd anzufassen.

## 7. Bekannte Lücken

- Alle boss-bezogenen `mid[]`-Zeilen (m5/m7/m12/m13/b6) sind geschrieben, aber **stumm**, bis BOSSES
  die sechs `EV.emit('boss...')`-Aufrufe ergänzt (§4).
- `destroyGround`s alte Boss-Teil-Zeile (§6) dupliziert sich NICHT mit meinen neuen `bossPart`-Zeilen
  (weil letztere noch nie feuern) — sobald BOSSES den Emit ergänzt, sollte die alte Zeile entfernt
  werden, sonst spricht das Spiel den Teil-Verlust doppelt an.

## 8. Tests

- `node tools/jsgate.mjs index.html` — grün nach jeder Änderung.
- Voller Sweep (alle Missionen + Cutscenes, HELIOS + B-Team + Endlos + Menü): 0 Exceptions/Console-
  Errors, vor und nach dem `openBriefing`-Fix.
- Zwei gezielte Szenarien (`story_test.mjs`, korrigiert `story_test2.mjs`): Prolog-Gate (einmalig via
  `SAVE.seenProlog`), m13-Variantenlader unter `trust`/`human`/`null` (korrekte `win[0]`-Sprecher,
  `mid`-Länge Basis+Variante, `spawns.air`-Zusammensetzung, `intro[0]`-Text), `choice`→`ending`
  `cs.next`-Verkettung, Epilog-Button nach letzter Mission, choiceabhängiger Debrief-Text, sowie der
  Mid-Runner selbst: skriptete `done`-Zeile hat Vorrang vor Fallback-Bark, Fallback-Bark respektiert
  das globale Cooldown.
- Screenshots (Prolog, Keller, beide Enden, beide Epiloge, m13-Briefing unter Basis und `human`) —
  alle sauber gerendert, kein Textüberlauf.

## 9. Relevante Querverweise

- `HANDOFF.md` §A7 „Kampagnen-Runtime & Missionen" — Kurzfassung für Neueinsteiger.
- `B-TEAM.md` §11 „Umsetzung: Cutscenes & Story-Trigger" — B-Team-spezifische Cutscenes/Mid-Tabellen.
