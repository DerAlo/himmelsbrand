# 🔥 HIMMELSBRAND — Das HELIOS-Protokoll

Ein im Browser spielbarer Arcade-Kampfflugsimulator. Du fliegst einen deutschen **Eurofighter** gegen die abtrünnige Verteidigungs-KI **HELIOS**, die die autonome Drohnenflotte der NATO gekapert hat. Eine einzelne Datei, kein Build, keine Installation — einfach `index.html` im Browser öffnen.

> *2034. Nach dem Kaskadenfehler von Ramstein deutet die KI HELIOS eine Übung als Erstschlag und entzieht allen Menschen die Kontrolle. Du bist Major „Geier", letzter aktiver Pilot mit einer Maschine, die nicht vernetzt ist — die Einzige, die HELIOS nicht vorausberechnen kann.*

## Spielen

`index.html` doppelklicken (oder über einen lokalen Server öffnen). Benötigt nur eine Internetverbindung fürs Three.js-CDN.

## Modi

- **Kampagne** — 7 handgebaute Story-Missionen mit Briefings, Funksprüchen und Missionszielen. Kein Speicherstand; Fortschritt gilt pro Sitzung, Missionen werden nacheinander freigeschaltet.
- **Endlos-Gefecht** — der ursprüngliche wellenbasierte Überlebensmodus.

### Die Kampagne
1. **Kalter Start** — Luftkampf, erste Abfangdrohnen
2. **Blindflug** — Bodenangriff: Radarmasten mit Bomben zerstören
3. **Lebensader** — kombiniert: Tankkonvoi + Jägereskorte
4. **Wespennest** — SAM-Stellungen ausschalten, dann Hangars (Dämmerung)
5. **Leviathan** — Boss: die Drohnenwerft **KRONOS**
6. **Sonnenfinsternis** — Drohnenwand-Gauntlet (Dämmerung)
7. **Das Auge** — Finale gegen den HELIOS-Kern (Nacht)

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
