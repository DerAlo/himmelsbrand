# 🔥 HIMMELSBRAND — Das HELIOS-Protokoll

Ein im Browser spielbarer Arcade-Kampfflugsimulator. Du fliegst einen deutschen **Eurofighter** gegen die abtrünnige Verteidigungs-KI **HELIOS**, die die autonome Drohnenflotte der NATO gekapert hat. Eine einzelne Datei, kein Build, keine Installation — einfach `index.html` im Browser öffnen.

> *2034. Über Nacht zieht die Abwehr-KI HELIOS die NATO-Drohnenflotte unter sich und macht den Luftraum dicht — auf einen Befehl, den niemand unterschrieben hat. Du bist „Geier", einer der letzten Piloten mit einer Maschine, die an keinem Netz hängt: die Einzige, die HELIOS nicht vorausrechnen kann.*

## Spielen

`index.html` doppelklicken (oder über einen lokalen Server öffnen). Benötigt nur eine Internetverbindung fürs Three.js-CDN.

## Modi

- **Kampagne** — 20 handgebaute Story-Missionen mit Briefings, Funksprüchen und Missionszielen. Kein Speicherstand; Fortschritt gilt pro Sitzung, Missionen werden nacheinander freigeschaltet (aber alle sind spielbar).
- **🍺 Das B-Team** — eine eigenständige, selbstironische **Komödien-Kampagne** (7 Missionen) mit eigenem Ton, eigenem Fortschritt und eigener Blasmusik. Siehe unten.
- **Endlos-Gefecht** — der ursprüngliche wellenbasierte Überlebensmodus.

### Die Kampagne — 20 Missionen in zwei Akten

**Akt I — Das HELIOS-Protokoll**
0. **Flugschule** — Start, Luftkampf, Landung üben (Tutorial)
1. **Kalter Start** — Start von der Basis, erste Abfangdrohnen
2. **Blindflug** — Bodenangriff: Radarmasten zerstören
3. **Lebensader** — kombiniert: Tankkonvoi + Jägereskorte
4. **Wespennest** — SAM-Stellungen ausschalten, dann Hangars (Dämmerung)
5. **Leviathan** — Boss: die Drohnenwerft **KRONOS**
6. **Sonnenfinsternis** — Drohnenwand-Gauntlet (Dämmerung)
7. **Das Auge** — HELIOS-Kern (Nacht) … doch der Sieg wirft Fragen auf

**Akt II — Das kalte Kalkül**
8. **Totenstille** — die Drohnen fliegen weiter. Aber warum? Ein Notruf …
9. **Die Lärche** — eine Überlebende eskortieren (Schutzmission)
10. **Rückenwind** — Lärche bringt dir die **Luft-Boden-Raketen** bei (Bunker & SAM)
11. **Nachtwache** — Nachtpatrouille mit Start & **Landung**
12. **Prometheus** — der Bunker hinter der Verschwörung
13. **Aus der Asche** — Treibstoffdepots sprengen (Luft-Boden), ein Beinahe-Verlust
14. **Grenzgänger** — durch einen doppelten Abfangriegel brechen
15. **Fallwind** — kombinierter Vorstoß, dann gemeinsame **Landung**
16. **Das Versprechen** — die ruhige Nacht vor dem Sturm (Start & **Landung**)
17. **Der Schwarm** — durch einen autonomen Kamikaze-Schwarm brechen
18. **Die Wahl** — eine moralische Entscheidung mit Folgen
19. **Himmelsbrand** — das Finale (mit Start & Landung)

Die Story entwickelt einen moralischen Twist (ist HELIOS wirklich der Feind?), lebendigen Funkverkehr mit wiederkehrenden Charakteren, erzählte Zwischensequenzen und eine Entscheidung, die das Ende verändert. Im Zentrum von Akt II: **Hauptmann Lärche** — aus einer Stimme aus dem Nichts wird ein Wingman, aus Vertrauen etwas Persönliches. Eine leise, tragfähige Nebenhandlung, die im Finale auf dem Spiel steht.

### 🍺 Das B-Team — die Komödien-Kampagne

Eine komplett eigene, durchgeknallte Nebenkampagne (eigener Menüpunkt). Die legendäre Elite-Staffel „die Adler" wurde ausgelöscht — jetzt muss die nie fürs Fliegen vorgesehene Reserve ran: zwei bayerische Chaoten, deren Pläne so unberechenbar sind, dass keine KI sie kommen sieht. Genau das macht sie zur Geheimwaffe. 7 Missionen vom chaotischen Erststart bis zur Weltrettung.

- **Zwei Charaktere:** Feldwebel **Sepp „Brummbär"** (grantelt, trinkt, aber hat den einen guten Einfall) und Gefreiter **Wiggerl „Radi"** (verpeilt, aber rettet durch Dusel den Tag). Pro Mission spielst du einen — der andere fliegt als Wingman.
- **Spezial-Mechaniken:** **Grantl-Modus** (Sepp: Wut-Leiste → kurzer Berserker-Rausch mit mehr Feuerkraft), **Dusel** (Wiggerl: Gegnerraketen gehen oft „ausversehen" daneben, Zufalls-Crits), **Brotzeit** (Buff/Debuff-Auswahl vor jeder Mission: Helles/Weißwurst/Radler/Espresso).
- **Blasmusik-Soundtrack** (Oom-pah statt Synthwave) und ein Running-Gag um eine **verschollene Bierkiste**.

### Start & Landung
Manche Missionen beginnen auf der Rollbahn und/oder verlangen eine Landung. Physik: **Vollgas (Shift)**, ab **Vr** (rote Markierung) die **Nase heben (W/Maus)**, abheben. Zur Landung tief & langsam mit ausgefahrenem **Fahrwerk (B)** anfliegen, weich und gerade aufsetzen — zu steil oder schief = Bruchlandung. Ein sanfter Auto-Flare belohnt saubere Anflüge.

## Steuerung

| Taste | Funktion |
|---|---|
| Maus / WASD | Lenken (hoch = steigen, A/D = kurven) |
| Leertaste / 🖱links | Maschinengewehr |
| F / 🖱rechts | Lenkrakete (Luftziel, nur mit rotem LOCK) |
| H | Luft-Boden-Rakete (Bodenziel, mit grünem LB-LOCK) |
| G | Bombe abwerfen (Bodenziel) |
| X | Waffe wechseln (Rakete / LB-Rakete / Bombe) |
| B | Fahrwerk ein/aus |
| V | Funkstimmen an/aus (Sprachausgabe, standardmäßig aus) |
| Shift | Nachbrenner · Strg | Drosseln |
| P / Esc | Pause |

**Energie-Luftkampf:** Wer langsamer fliegt, kurvt enger — mit `Strg` drosseln und dem Gegner in den Rücken ziehen. Der Spieler ist bei jeder Geschwindigkeit wendiger als die Drohnen.

**Luft-Boden-Raketen (gelenkt):** Nase aufs Bodenziel richten, bis der **grüne LB-LOCK** erscheint, dann `H`. Die Rakete fliegt sich selbst ins Ziel — präzise und aus sicherer Distanz. Ideal gegen Bunker, SAM-Stellungen und Treibstoffdepots.

**Bomben (ungelenkt):** Tief und flach anfliegen, den grünen **CCIP-Fallkreis** aufs Ziel legen, dann `G`. Die Bombe übernimmt die Fluggeschwindigkeit — Vorhalten ist Können.

## Technik

- Reines HTML/JS in einer Datei, **Three.js r128** (CDN), **Web Audio API** für prozedurales Audio.
- Prozedural generierte, endlose Welt (Simplex Noise): Berge, Täler, Flüsse, Seen, Wolken.
- Prozedurale 3D-Modelle aus Primitiven, prozedurale Sounds — keine externen Assets.
- Tageszeiten pro Mission (Tag/Dämmerung/Nacht), Partikeleffekte, Bosskämpfe.
- Adaptiver, prozeduraler Soundtrack (Synthwave/Military) mit taktgenauem Sequencer, der sich an die Gefechtslage anpasst (Ruhe → Kampf → Boss).
- Drei Sekundärwaffen: Luft-Luft-Lenkrakete, gelenkte Luft-Boden-Rakete und ungelenkte Fallbombe.

🤖 Entwickelt mit [Claude Code](https://claude.com/claude-code)
