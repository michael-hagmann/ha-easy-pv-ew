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

- Datei: `config/home-assistant.log`; der Logger `custom_components.easy_pv_ew` steht auf `debug`. Beim Neustart wird das alte Log zu `home-assistant.log.1`; für Zeitreihen beide lesen.
- Zeiten im Log sind **UTC** (der Container rechnet in UTC, Michael in MEZ/MESZ).
- Die Rohantworten stehen als Python-Dict hinter `Response GET <pfad>: `; auswerten mit `ast.literal_eval`, nicht mit `json`.
- Was HA tatsächlich anzeigt, steht in der Datenbank: `sqlite3` auf `config/home-assistant_v2.db` nur lesend (`?mode=ro`), Tabellen `states` und `states_meta`. Entity-IDs des Geräts enthalten den `productCode`-Zusatz; vor der Ausgabe im Chat ersetzen.
- Gezielt filtern statt das ganze Log auszugeben, z. B.:

  ```bash
  grep -n 'easy_pv_ew' config/home-assistant.log | tail -50
  grep -n -i -E 'error|exception|traceback' config/home-assistant.log | tail -30
  ```

- Das Log kann Kontodaten enthalten. Vor dem Zitieren im Chat Seriennummern, IDs, Ort und Konto unkenntlich machen. Für Fixtures den Skill `fixture-anonymisieren` verwenden.

## Prüfen für Schritt 7

Geprüft am 05.11.2026: Einheiten (alles kWh bzw. W), Gesamtzähler je Gerät und Station, Takt (Leistung jede Minute, Zähler etwa alle 5 Minuten in Schritten von 0,01 kWh). Weiter beobachten:

- Verhalten nachts (offline? leere Eingänge?) und Tageswechsel von `genpowerTodayTotals`/`todayPowerTotals`
- kleinere Werte beim Gesamtzähler (Warnung „lower total energy“)
- Token-Ablauf (Einrichtung 05.11.2026 11:18 UTC, siehe `local/offene-entscheidungen.md`)
- Entity-IDs der Sensoren für Gesamtertrag und Leistung notieren (Übergabe an „HA PV Konfiguration“)
