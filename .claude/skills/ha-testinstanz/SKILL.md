---
name: ha-testinstanz
description: Die Home-Assistant-Test-Instanz im Devcontainer starten, neu starten und ihr Log auswerten, um die Integration mit echten Daten zu prüfen. Verwenden für Schritt 7 des Briefings, für „starte HA“, „schau ins Log“ oder um eine Änderung in der laufenden Instanz zu prüfen.
---

# HA-Test-Instanz

Nur die Test-Instanz im Devcontainer. Die produktive Instanz wird nie angefasst.

## Starten

```bash
scripts/develop   # im Hintergrund starten (run_in_background), läuft dauerhaft
```

- Weboberfläche: http://localhost:8123 (VS Code leitet den Port weiter).
- Erster Start legt `config/` an; das dauert und lädt Abhängigkeiten.
- `config/` ist bis auf `config/configuration.yaml` per `.gitignore` ausgeschlossen. Dort liegen nach der Einrichtung Token und Kontodaten (`config/.storage/`). **Nie committen, nie ausgeben.**

## Integration einrichten

Michael richtet „Easy PV (EW)“ selbst über die Oberfläche ein und gibt die Zugangsdaten dort ein. Nie im Chat danach fragen, nie per Skript oder API eintragen.

## Nach Codeänderungen

HA lädt Python-Code nicht neu. Prozess beenden (`pkill -f "hass --config"`; der Bash-Aufruf endet dabei selbst mit Exit-Code 144, mit `pgrep -af "hass --config"` prüfen) und `scripts/develop` wieder im Hintergrund starten (oder in der Oberfläche *Einstellungen → System → Neu starten*). Der Prozess hängt an der Session; endet sie, läuft die Test-Instanz unter Umständen nicht weiter.

## Log auswerten

- Datei: `config/home-assistant.log`; der Logger `custom_components.easy_pv_ew` steht auf `debug`. Beim Neustart wird das alte Log zu `home-assistant.log.1`, eine vorhandene `.log.1` geht dabei verloren; für Zeitreihen beide lesen und vor einem Neustart auswerten oder sichern.
- Zeiten im Log sind **UTC** (der Container rechnet in UTC, Michael in MEZ/MESZ).
- Die Rohantworten stehen als Python-Dict hinter `Response GET <pfad>: `; auswerten mit `ast.literal_eval`, nicht mit `json`.
- Was HA tatsächlich anzeigt, steht in der Datenbank `config/home-assistant_v2.db`, nur lesend öffnen (Python: `sqlite3.connect("file:config/home-assistant_v2.db?mode=ro", uri=True)`; das Programm `sqlite3` ist nicht installiert), Tabellen `states` und `states_meta`. Entity-IDs des Geräts enthalten den `productCode`-Zusatz; vor der Ausgabe im Chat ersetzen.
- Gezielt filtern statt das ganze Log auszugeben, z. B.:

  ```bash
  grep -n 'easy_pv_ew' config/home-assistant.log | tail -50
  grep -n -i -E 'error|exception|traceback' config/home-assistant.log | tail -30
  ```

- Aussetzer: Die Zeile „Update failed, keeping last values: <Fehlertyp>: …“ steht nach der Zeile `Request GET <Pfad>` der hängenden Anfrage. Gelegentliche DNS- und Verbindungs-Timeouts, meist an der ersten Anfrage eines Abrufs, sind in der Test-Instanz normal (siehe `CLAUDE.md`, „Umgebung“); die 5-Minuten-Überbrückung fängt sie ab.
- Vor einem Neustart `config/home-assistant.log` nach `local/logs/` kopieren. Auswerteskripte (nicht eingecheckt, falls vorhanden) liegen in `local/tools/`.
- Das Log kann Kontodaten enthalten. Vor dem Zitieren im Chat Seriennummern, IDs, Ort und Konto unkenntlich machen. Für Fixtures den Skill `fixture-anonymisieren` verwenden.

## Prüfen mit echten Daten

Was gerade zu beobachten ist, steht im Handover („Nächster Schritt“). Allgemein:

- Einheiten (kWh, W) und Takt der Werte gegen die Easy-PV-App
- Nacht und Tageswechsel in der Zeitzone der Station: Zähler ohne Rücksprung, Leistung nachts `unavailable` (siehe `CLAUDE.md`, „Schnittstelle zum Energie-Setup“)
- kleinere Werte bei den Zählern: Debug „Cloud reports a lower energy_total/energy_month“; Warnungen „lower total energy of the station“ oder „of the inverter“
- Token-Ablauf: Reauth-Meldung in HA, Rohantwort der Ablehnung (siehe `local/offene-entscheidungen.md`)
- Entity-IDs der Sensoren für Gesamtertrag und Leistung notieren (Übergabe ans Projekt)
