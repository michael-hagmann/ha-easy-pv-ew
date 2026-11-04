---
name: fixture-anonymisieren
description: Echte Antworten der Easy-PV-Cloud-API (aus dem Debug-Log der Test-Instanz oder dem Diagnose-Download) in anonymisierte Test-Fixtures unter tests/fixtures/ überführen. Verwenden, sobald echte Rohantworten vorliegen und Fixtures angelegt oder an echte Daten angeglichen werden sollen.
---

# Fixture anonymisieren

Echte Antworten enthalten Seriennummern, Standort und Kontodaten. Sie dürfen weder ins Repository noch ungefiltert in den Chat gelangen.

## 1. Quelle

- Debug-Log der Test-Instanz: `config/home-assistant.log` (Logger `custom_components.easy_pv_ew` steht auf `debug`), siehe Skill `ha-testinstanz`.
- Rohantworten nicht vollständig in den Chat kopieren lassen oder ausgeben; gezielt mit `grep`/`python` die betreffende Zeile in eine Datei im Scratchpad extrahieren und dort bearbeiten.

## 2. Ersetzen

Werte durch die festen Platzhalter ersetzen, die die vorhandenen Fixtures schon verwenden. So bleiben die Tests konsistent:

| Feld (Beispiele) | Platzhalter |
| --- | --- |
| Token | `test-token` |
| Stations-ID (`id` in `getStationList`, `stationId`, `powerId`) | `1001` |
| Geräte-ID (`id` in `getPowerList`, `deviceId`) | `2001` (weitere: `2002` …) |
| Seriennummer (`deviceNum`, `sn`, MAC, IMEI o. ä.) | `SN0000000000` |
| Stationsname | `Gartenhaus` |
| Adresse, Ort (`address`, `plantLocation`) | `Musterstraße 1, 12345 Musterstadt` / `Musterstadt` |
| Koordinaten (`latitude`, `longitude`) | `50.0` / `8.0` |
| Benutzername, Kontoname | `Testkonto` |
| E-Mail | `test@example.com` |
| Telefonnummer, Nutzer-ID, Avatar-URL, Zeitzone mit Ortsbezug | neutral ersetzen oder Feld entfernen |

**Nicht** ändern: Feldnamen, Datentypen (Zahl bleibt Zahl, String bleibt String – genau das wollen wir an echten Daten lernen), Messwerte, Einheiten, Firmware-Versionen, Produktcode (`VN2T08EU`), Struktur und Verschachtelung.

Unbekannte Felder, die identifizierend sein könnten (lange Zahlen, Hex-Strings, Namen), im Zweifel ersetzen und Michael fragen.

## 3. Prüfen

```bash
# Darf nichts finden – echte Werte aus der Rohantwort einsetzen, nicht ins Repo schreiben:
grep -rn -e '<echte Seriennummer>' -e '<echte Stations-ID>' -e '<Ort>' tests/
```

Dann `scripts/test`. Schlagen Tests fehl, weil echte Daten anders aussehen (z. B. Zahl als String, Wh statt kWh), ist das ein Befund: Code anpassen, nicht die Fixture verfälschen. Befund im Handover unter „Offene Fragen und Annahmen“ auflösen.

## 4. Scratchpad aufräumen

Die Datei mit der Rohantwort im Scratchpad löschen.
