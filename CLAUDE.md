# Easy PV (EW) – Fork von ha-easy-pv

Home-Assistant-Integration für den Balkonkraftwerk-Wechselrichter Electronic Way (EW) VN2T08EU über die Easy-PV-Cloud.

**Zuständigkeiten:** Regeln und Entscheidungen, die nur den Code betreffen, führt diese Session (diese Datei, Skills, `local/offene-entscheidungen.md`). Vorgaben zur Nutzung der Integration in Michaels HA (Energie-Setup, Entity-IDs, Installation, Korrekturfaktor) führt das claude.ai-Projekt „HA PV Konfiguration“ in der „Schnittstelle Energie-Setup“ (lokale Kopie `local/schnittstelle-energie-setup.md`, wird unten importiert; fehlt sie, gilt die Kurzfassung „Schnittstelle zum Energie-Setup“ unten). Widerspricht eine Vorgabe des Projekts dem Code: bei Michael nachfragen, nicht selbst auflösen.

- `local/referenz.md` zum **Nachschlagen**, nicht automatisch geladen: Gerätewissen, Auszug „Schnittstelle laut OpenAPI“, Rückfallebene MQTT, Quellen.
- Das frühere Briefing des Projekts ist abgeschlossen und liegt in `local/archiv/`.

@local/schnittstelle-energie-setup.md
@local/austausch.md

## Projektunterlagen nur lokal

Schnittstelle, Handover, offene Entscheidungen, Referenz und Austauschregeln betreffen Michaels Entwicklungsstand und kommen **nicht ins öffentliche Repository**. Sie liegen in `local/` (in `.gitignore`, im Container-Volume, übersteht einen Rebuild):

- `local/schnittstelle-energie-setup.md`: Kopie der Vorgaben des Projekts zur Nutzung in HA (führend im Projekt, nicht selbst ändern)
- `local/referenz.md`: Nachschlagewerk der Code-Sitzung
- `local/archiv/`: abgeschlossene Unterlagen (Briefing)
- `local/HANDOVER.md`: Übergabe an die nächste Session
- `local/handover-archiv/`: Endstände früherer Sessions
- `local/offene-entscheidungen.md`: Entscheidungen, die Michael noch treffen muss, und getroffene
- `local/austausch.md`: Regeln der Code-Sitzung für den Austauschordner zum claude.ai-Projekt

Git sichert und versioniert diese Dateien nicht. Fehlt eine davon (neues Volume, frischer Klon), Michael Bescheid sagen; die Schnittstelle gibt es auch im claude.ai-Projekt. Ältere Fassungen bis 04.11.2026 lagen unter `docs/`; seit dem Umschreiben der Historie sind sie nur noch in verwaisten Commits auf GitHub über deren SHA abrufbar (bekannt und so gewollt).

## Arbeit über mehrere Sessions

Michael arbeitet in mehreren Claude-Sessions, damit der Kontext sauber bleibt.

- **Zu Beginn jeder Session** den Skill `session-start` anwenden, bevor an Code gearbeitet wird: Memories, `local/HANDOVER.md`, `local/offene-entscheidungen.md` und Git-Log lesen, abgleichen, Session-Kennung festlegen.
- **Während der Session** das Handover laufend pflegen (Skill `handover-pflegen`, bei jedem Commit über `commit`; es wird nicht mitcommittet), damit es auch bei einem unerwarteten Ende aktuell ist. Bei der ersten Änderung in einer neuen Session wird der Stand der Vorsession nach `local/handover-archiv/` archiviert. Das Handover enthält nur, was die nächste Session braucht.
- **Am Ende einer Session** oder bei vollem Kontext den Skill `session-ende` anwenden, um Wissen einzuordnen und das Handover aufzuräumen.
- Dauerhaftes Wissen gehört in diese Datei, die Skills oder die lokalen Projektunterlagen, nicht nur in Memories. Was nur für Michaels Umgebung gilt (Austauschordner, eigene Devcontainer-Fassung), gehört nach `local/`, nicht in diese öffentliche Datei.
- Wiederkehrende Abläufe als Skill unter `.claude/skills/` ablegen. Vorhanden:
  - `session-start`: Einstieg in eine Session, Stand abgleichen und berichten
  - `commit`: Lint, Tests, Prüfung auf vertrauliche Daten, Commit-Nachricht
  - `handover-pflegen`: Handover aktuell halten, Vorsession archivieren
  - `session-ende`: Wissen einordnen, Handover aufräumen
  - `ha-testinstanz`: Test-Instanz starten, Log auswerten (Schritt 7)
  - `fixture-anonymisieren`: echte API-Antworten in Fixtures überführen (Schritt 7)
- Ein Agent für Planung, Implementierung und Tests; vor dem Release ein `/code-review` über den gesamten Diff.
- Entscheidungsfragen an Michael mit Hintergrund stellen: Ist-Zustand, Problem, Optionen mit Vor- und Nachteilen, Empfehlung. Offene Entscheidungen in `local/offene-entscheidungen.md` festhalten statt sie nur im Chat zu stellen.

## Arbeitsregeln

- Mit Michael Deutsch sprechen.
- Vor jedem schreibenden Schritt außerhalb des Repositorys (z. B. Push, Release, Änderungen an einer HA-Instanz) zeigen, was passiert, und auf Michaels OK warten. Änderungen im Repository dürfen ohne Rückfrage erfolgen; Commits mit aussagekräftiger Nachricht.
- **Nur lesend gegenüber der Cloud.** Die Integration nutzt ausschließlich die Endpunkte für das eigene Konto: Anmeldung (`passLogin`), Benutzerdaten (`selectUserInfo`), Stationsliste (`getStationList`), Geräteliste (`getPowerList`), Gerätedaten (`getDeviceDataInfo`). Nie Gerätebefehle, Leistungsbegrenzung, Firmware-Updates, Einstellungen oder Partner-/Händler-/Verwaltungs-Endpunkte („Open API“, DMP), auch wenn die OpenAPI-Beschreibung sie zeigt.
- **Abrufintervall nie unter 60 s**, auch nicht als einstellbare Option; keine Abfragen außerhalb des normalen Betriebs.
- **Die OpenAPI-Beschreibung des Herstellers kommt nie ins Repository** (der Fork ist öffentlich, die Beschreibung ist eine interne Unterlage des Herstellers). Fassungen liegen nur lokal als `local/openapi/easy-pv-JJJJ-MM-TT.json` (`local/` steht in `.gitignore`); vor jedem Commit prüfen, dass nichts aus `local/` gestaged ist. Auch keine Auszüge daraus in Code, Tests, Kommentare oder Commit-Nachrichten, die der Code nicht braucht. Die **Adresse** der Beschreibung ist kein Geheimnis und steht als `openapi_url` in `tests/api_contract.yaml`.
- **Die Beschreibung nie automatisch herunterladen**, auch nicht per Skript oder `WebFetch`: Der Server verbietet es per `robots.txt`. Neue Fassungen holt Michael von Hand im Browser.
- **Referenz für API-Fragen:** Existiert `local/openapi/`, gilt dort die neueste Datei (nach Datum im Namen). Fehlt sie, gilt der Auszug „Schnittstelle laut OpenAPI“ in `local/referenz.md`. Maßgeblich für den Code ist der Schnittstellenvertrag `tests/api_contract.yaml` (nur, was der Code liest); Abweichungen meldet `scripts/check_api`.
- Zugangsdaten der Easy-PV-App gibt Michael selbst in HA ein. Nie im Chat erfragen, nie in Code, Tests, Fixtures oder Logs ablegen. Rohantworten für Fixtures anonymisieren (Seriennummern, Standort, Konto).
- `config/` enthält Laufzeitdaten der Test-Instanz und gehört nicht ins Repository, ausgenommen `config/configuration.yaml`.
- Entwickelt und getestet wird im Devcontainer gegen die dortige Test-Instanz (siehe „Umgebung“). Die produktive HA-Instanz wird nicht angefasst.
- Vor jedem Commit `scripts/lint` und die Tests laufen lassen (Skill `commit`).

## Umgebung: Devcontainer

Claude läuft als VS-Code-Erweiterung **im Devcontainer** (`.devcontainer/devcontainer.json`), nicht auf dem Host. Der Host ist beliebig, solange er Devcontainer ausführen kann. `${localEnv:…}` in `devcontainer.json` liest die Umgebung des Rechners, auf dem Docker und die Devcontainer-Werkzeuge laufen (bei Docker direkt in WSL also die WSL-Umgebung, nicht die von Windows).

- **Image** `mcr.microsoft.com/devcontainers/python:3.14`, Benutzer `vscode` mit `sudo`. HA 2026.10.4 und die Testabhängigkeiten installiert `scripts/setup` beim Erstellen des Containers (`postCreateCommand`).
- **Repository** unter `/workspaces/ha-easy-pv-ew`, am besten auf einem Container-Volume statt in einem eingebundenen Host-Ordner (deutlich schneller, vor allem unter Windows).
- **Kein Zugriff** auf die produktive HA-Instanz oder das Heimnetz nötig, und so ist es gewollt. Gebraucht wird nur Internetzugang zur Easy-PV-Cloud.
- **Test-Instanz:** HA im Container auf Port 8123, VS Code leitet den Port an den Host weiter.
- **Commit-Adresse:** nie eine private E-Mail-Adresse, sondern die GitHub-Noreply-Adresse des eigenen Kontos, eingestellt per `git config user.email` im Repository (nicht global: VS Code übernimmt `~/.gitconfig` vom Host). Ist im Repository keine gesetzt, vor dem Commit nachfragen statt eine einzutragen.
- **Git push** läuft über den Credential-Helper von VS Code und funktioniert nur, solange VS Code mit dem Container verbunden ist. `gh` ist nicht installiert.
- **Rebuild** des Containers (nach Änderungen an `devcontainer.json`) verwirft alles außerhalb von `/workspaces` und den Volumes: installierte Pakete, Shell-Verlauf. `~/.claude` (Login, Memories) liegt auf einem eigenen Volume. Ein Rebuild ist ein Schritt außerhalb des Repositorys und braucht Michaels OK; er löst ihn selbst in VS Code aus.
- **Nicht installiert:** `bc`, `sqlite3`, `dig`. Stattdessen Python (`sqlite3`-Modul).
- **Temporäre Dateien:** `$TMPDIR` ist leer, und das Scratchpad-Verzeichnis der Session existiert anfangs nicht. Vorher `mkdir -p` und prüfen, bevor man sich auf eine Sicherungskopie verlässt. Um alten Code testweise zu prüfen, lieber `git stash` oder `git worktree` statt Kopieren.

## Befehle

- `scripts/test`: pytest mit `pytest-homeassistant-custom-component`; Argumente gehen an pytest durch
- `scripts/lint`: `ruff format` und `ruff check --fix`
- `scripts/develop`: Test-Instanz auf Port 8123 starten (Skill `ha-testinstanz`)
- `scripts/check_api`: `tests/api_contract.yaml` mit der neuesten Fassung in `local/openapi/` vergleichen (ohne Netzwerk; ohne lokale Fassung nur ein Hinweis). Nach jeder neuen Fassung laufen lassen und Abweichungen in Vertrag, Code und Tests übernehmen.
- `scripts/setup`: Abhängigkeiten aus `requirements_test.txt` installieren (läuft beim Erstellen des Containers)

## Code-Konventionen

- Code: `custom_components/easy_pv_ew/`, API-Client in `easy_pv/__init__.py`. Kommentare und Docstrings auf Englisch wie im Original, Commit-Nachrichten und Dokumentation auf Deutsch.
- Der API-Client bekommt die Session von `async_get_clientsession(hass)` und legt nie eine eigene an.
- Fehlertypen des Clients: `LoginError` (Anmeldung/Token) → im Coordinator `ConfigEntryAuthFailed`; alle anderen `BaseError` (`ApiError`, `InvalidResponseError`, `CommunicationError` für Netzwerk/DNS/Timeout) → `UpdateFailed`. `LoginError` nie unterwegs abfangen oder in `UpdateFailed` umwandeln, sonst startet kein Reauth.
- Nie Tokens, E-Mail, Seriennummern, IDs oder Standort loggen, auch nicht auf Debug. Auch `productCode` nicht: Bei echten Geräten trägt er einen gerätebezogenen Zusatz (`VN2T08EU-<code>`), der Teil der Seriennummer sein kann; er steht deshalb auch im Gerätenamen und in den Entity-IDs des Geräts. Der Debug-Logger der Integration ist in der Test-Instanz aktiv. Rohantworten nur anonymisiert loggen.
- Tests: Fixtures in `tests/fixtures/` (nachgebaut bzw. anonymisiert, feste Platzhalter wie `test-token`, Station `1001`, Gerät `2001`). Messwerte in Fixtures dürfen keinem Platzhalter gleichen (z. B. Frequenz 49.98 statt 50.0, weil der Breitengrad 50.0 ist), sonst schlagen die Anonymisierungstests fehl. Dasselbe gilt für Zeitstempel: Mikrosekunden können zufällig einen Platzhalter enthalten (`…12.100123` enthält `1001`); in Leck-Tests feste Zeiten setzen. HTTP über `aioclient_mock`; die Fixture `mock_api` in `tests/conftest.py` registriert alle Endpunkte erfolgreich. `*_real.json` sind anonymisierte echte Antworten (Typen und `null`-Felder wie in der Cloud), die übrigen Fixtures füllen alle Felder. Standardmäßig deaktivierte Entitäten (Temperatur, Frequenz je Eingang) brauchen in Tests die Fixture `enable_all_entities` vor `setup_integration`.
- Für jede Fehlerbehebung einen Test, der den Fehler zeigt.

## Schnittstelle zum Energie-Setup (Kurzfassung)

- Gesamtertrag des EW: kWh aus `powerTotals` der Station (`getStationList`), nicht `genPowerTotal` des Geräts (der fällt bei einer Neuregistrierung in der App auf 0). `device_class: energy`, `state_class: total_increasing`, nie ein Rücksprung, stabile Entity-ID.
- Alle Energiefelder sind kWh (an echten Daten geprüft), auch die von `getDeviceDataInfo`, für die die OpenAPI-Beschreibung Wh nennt (`spec_unit: Wh` im Vertrag). Nicht durch 1000 teilen.
- Leistung des EW: W, `device_class: power`, `state_class: measurement`. Nachts schaltet sich der EW ab; meldet die Cloud ihn offline (`status` 2), ist die Leistung `unavailable`, nicht 0 W.
- Um Mitternacht (Zeitzone der Station, `timeZone`) meldet die Cloud einige Minuten falsche Zähler (Station minus Tagesertrag, Monat 0) und danach den Stationszähler 0,01 kWh zu niedrig. Stationszähler übernimmt nie einen kleineren Wert, Gerätezähler erst nach 24 Stunden, Ertrag Monat nur am Monatsersten oder nach einem Monatswechsel.
- Bei Cloud-Ausfall lieber `unavailable` als falsche Werte.

Rückfall für frische Klone; maßgeblich ist die Schnittstelle des Projekts. Begründungen in `local/offene-entscheidungen.md`.
