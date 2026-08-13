# 🔥 HIMMELSBRAND — Das HELIOS-Protokoll

Ein im Browser spielbarer Arcade-Kampfflugsimulator. Du fliegst einen deutschen **Eurofighter** gegen die abtrünnige Verteidigungs-KI **HELIOS**, die die autonome Drohnenflotte der NATO gekapert hat. Eine einzelne Datei, kein Build, keine Installation — einfach `index.html` im Browser öffnen.

> *2034. Nach dem Kaskadenfehler von Ramstein deutet die KI HELIOS eine Übung als Erstschlag und entzieht allen Menschen die Kontrolle. Du bist Major „Geier", letzter aktiver Pilot mit einer Maschine, die nicht vernetzt ist — die Einzige, die HELIOS nicht vorausberechnen kann.*

## Spielen

`index.html` doppelklicken (oder über einen lokalen Server öffnen). Benötigt nur eine Internetverbindung fürs Three.js-CDN.

## Modi

- **Kampagne** — 7 handgebaute Story-Missionen mit Briefings, Funksprüchen und Missionszielen. Kein Speicherstand; Fortschritt gilt pro Sitzung, Missionen werden nacheinander freigeschaltet.
- **Endlos-Gefecht** — der ursprüngliche wellenbasierte Überlebensmodus.

### Die Kampagne — 14 Missionen in zwei Akten

**Akt I — Das HELIOS-Protokoll**
0. **Flugschule** — Start, Luftkampf, Landung üben (Tutorial)
1. **Kalter Start** — Start von der Basis, erste Abfangdrohnen
2. **Blindflug** — Bodenangriff: Radarmasten mit Bomben zerstören
3. **Lebensader** — kombiniert: Tankkonvoi + Jägereskorte
4. **Wespennest** — SAM-Stellungen ausschalten, dann Hangars (Dämmerung)
5. **Leviathan** — Boss: die Drohnenwerft **KRONOS**
6. **Sonnenfinsternis** — Drohnenwand-Gauntlet (Dämmerung)
7. **Das Auge** — HELIOS-Kern (Nacht) … doch der Sieg wirft Fragen auf

**Akt II — Das kalte Kalkül**
8. **Totenstille** — die Drohnen fliegen weiter. Aber warum?
9. **Die Lärche** — eine Überlebende eskortieren (Schutzmission)
10. **Prometheus** — der Bunker hinter der Verschwörung
11. **Der Schwarm** — durch einen autonomen Kamikaze-Schwarm brechen
12. **Die Wahl** — eine moralische Entscheidung mit Folgen
13. **Himmelsbrand** — das Finale (mit Start & Landung)

Die Story entwickelt einen moralischen Twist (ist HELIOS wirklich der Feind?), lebendigen Funkverkehr mit neuen Charakteren (Hauptmann Lärche), erzählte Zwischensequenzen und eine Entscheidung, die das Ende verändert.

### Start & Landung
Manche Missionen beginnen auf der Rollbahn und/oder verlangen eine Landung. Physik: **Vollgas (Shift)**, ab **Vr** (rote Markierung) die **Nase heben (W/Maus)**, abheben. Zur Landung tief & langsam mit ausgefahrenem **Fahrwerk (B)** anfliegen, weich und gerade aufsetzen — zu steil oder schief = Bruchlandung. Ein sanfter Auto-Flare belohnt saubere Anflüge.

## Steuerung

| Taste | Funktion |
|---|---|
| Maus / WASD | Lenken (hoch = steigen, A/D = kurven) |
| Leertaste / 🖱links | Maschinengewehr |
| F / 🖱rechts | Lenkrakete (Luftziel) |
| G | Bombe abwerfen (Bodenziel) |
| X | Waffe wechseln (Rakete/Bombe) |
| Shift | Nachbrenner · Strg | Drosseln |
| P / Esc | Pause |

**Energie-Luftkampf:** Wer langsamer fliegt, kurvt enger — mit `Strg` drosseln und dem Gegner in den Rücken ziehen. Der Spieler ist bei jeder Geschwindigkeit wendiger als die Drohnen.

**Bomben (ungelenkt):** Tief und flach anfliegen, den grünen **CCIP-Fallkreis** aufs Ziel legen, dann `G`. Die Bombe übernimmt die Fluggeschwindigkeit — Vorhalten ist Können.

## Technik

- Reines HTML/JS in einer Datei, **Three.js r128** (CDN), **Web Audio API** für prozedurales Audio.
- Prozedural generierte, endlose Welt (Simplex Noise): Berge, Täler, Flüsse, Seen, Wolken.
- Prozedurale 3D-Modelle aus Primitiven, prozedurale Sounds — keine externen Assets.
- Tageszeiten pro Mission (Tag/Dämmerung/Nacht), Partikeleffekte, Bosskämpfe.

🤖 Entwickelt mit [Claude Code](https://claude.com/claude-code)
