---
name: ha-testinstanz
description: Die Home-Assistant-Test-Instanz im Devcontainer starten, neu starten und ihr Log auswerten, um die Integration mit echten Daten zu prüfen. Verwenden für Schritt 6 des Briefings, für „starte HA“, „schau ins Log“ oder um eine Änderung in der laufenden Instanz zu prüfen.
---

# HA-Test-Instanz

Nur die Test-Instanz im Devcontainer. Die produktive Instanz auf der NAS wird nie angefasst.

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

HA lädt Python-Code nicht neu. Prozess beenden und `scripts/develop` neu starten (oder in der Oberfläche *Einstellungen → System → Neu starten*).

## Log auswerten

- Datei: `config/home-assistant.log`; der Logger `custom_components.easy_pv_ew` steht auf `debug`.
- Gezielt filtern statt das ganze Log auszugeben, z. B.:

  ```bash
  grep -n 'easy_pv_ew' config/home-assistant.log | tail -50
  grep -n -i -E 'error|exception|traceback' config/home-assistant.log | tail -30
  ```

- Das Log kann Kontodaten enthalten. Vor dem Zitieren im Chat Seriennummern, IDs, Ort und Konto unkenntlich machen. Für Fixtures den Skill `fixture-anonymisieren` verwenden.

## Prüfen für Schritt 6

- Einheiten und Datentypen der Felder (W, kWh oder Wh; Zahl oder String)
- Gibt es in `getDeviceDataInfo` einen Gesamtzähler pro Gerät?
- Aktualisiert sich der Wert bei jedem Abruf, wie oft ändert die Cloud ihn?
- Entity-IDs der Sensoren für Gesamtertrag und Leistung notieren (Übergabe an „HA PV Konfiguration“)
- Zeitpunkt der Einrichtung notieren (Token-Laufzeit, siehe `docs/offene-entscheidungen.md`)
