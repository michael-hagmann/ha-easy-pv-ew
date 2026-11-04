# Easy PV (EW) – Fork von ha-easy-pv

Home-Assistant-Integration für den Balkonkraftwerk-Wechselrichter Electronic Way (EW) VN2T08EU über die Easy-PV-Cloud.

**Auftrag, Anforderungen und Ablauf: `docs/briefing-ew.md`** (wird unten importiert und damit in jeder Session geladen).

- Das Briefing im Repository ist eine **Kopie**. Die führende Fassung liegt im claude.ai-Projekt „HA PV Konfiguration“ (`claude/ew-integration-briefing.md`); Michael erneuert die Kopie bei Änderungen. Die Kopie nicht selbst inhaltlich ändern, sondern Änderungswünsche an Michael melden.
- Bei Widersprüchen zwischen dieser Datei und dem Briefing: bei Michael nachfragen, nicht selbst auflösen.

@docs/briefing-ew.md

## Arbeit über mehrere Sessions

Michael arbeitet in mehreren Claude-Sessions, damit der Kontext sauber bleibt.

- **Zu Beginn jeder Session** den Skill `session-start` anwenden, bevor an Code gearbeitet wird: Memories, `docs/HANDOVER.md`, `docs/offene-entscheidungen.md` und Git-Log lesen, abgleichen, Session-Kennung festlegen.
- **Während der Session** das Handover laufend pflegen (Skill `handover-pflegen`, bei jedem Commit über `commit`), damit es auch bei einem unerwarteten Ende aktuell ist. Bei der ersten Änderung in einer neuen Session wird der Stand der Vorsession nach `docs/handover-archiv/` archiviert. Das Handover enthält nur, was die nächste Session braucht.
- **Am Ende einer Session** oder bei vollem Kontext den Skill `session-ende` anwenden, um Wissen einzuordnen und das Handover aufzuräumen.
- Dauerhaftes Wissen gehört ins Repository (diese Datei, Handover, Skills), nicht nur in Memories. `~/.claude` liegt erst seit dem Volume in `.devcontainer/devcontainer.json` außerhalb des Containers.
- Wiederkehrende Abläufe als Skill unter `.claude/skills/` ablegen. Vorhanden:
  - `session-start`: Einstieg in eine Session, Stand abgleichen und berichten
  - `commit`: Lint, Tests, Prüfung auf vertrauliche Daten, Commit-Nachricht
  - `handover-pflegen`: Handover aktuell halten, Vorsession archivieren
  - `session-ende`: Wissen einordnen, Handover aufräumen
  - `ha-testinstanz`: Test-Instanz starten, Log auswerten (Schritt 6)
  - `fixture-anonymisieren`: echte API-Antworten in Fixtures überführen (Schritt 6)
- Ein Agent für Planung, Implementierung und Tests; vor dem Release ein `/code-review` über den gesamten Diff.
- Entscheidungsfragen an Michael mit Hintergrund stellen: Ist-Zustand, Problem, Optionen mit Vor- und Nachteilen, Empfehlung. Offene Entscheidungen in `docs/offene-entscheidungen.md` festhalten statt sie nur im Chat zu stellen.

## Arbeitsregeln

- Mit Michael Deutsch sprechen.
- Vor jedem schreibenden Schritt außerhalb des Repositorys (z. B. Push, Release, Änderungen an einer HA-Instanz) zeigen, was passiert, und auf Michaels OK warten. Änderungen im Repository dürfen ohne Rückfrage erfolgen; Commits mit aussagekräftiger Nachricht.
- **Nur lesend gegenüber der Cloud.** Die Integration nutzt ausschließlich die Endpunkte für das eigene Konto: Anmeldung (`passLogin`), Benutzerdaten (`selectUserInfo`), Stationsliste (`getStationList`), Geräteliste (`getPowerList`), Gerätedaten (`getDeviceDataInfo`). Nie Gerätebefehle, Leistungsbegrenzung, Firmware-Updates, Einstellungen oder Partner-/Händler-/Verwaltungs-Endpunkte („Open API“, DMP), auch wenn die OpenAPI-Beschreibung sie zeigt.
- **Abrufintervall nie unter 60 s**, auch nicht als einstellbare Option; keine Abfragen außerhalb des normalen Betriebs.
- **Die OpenAPI-Beschreibung des Herstellers kommt nicht ins Repository** (der Fork ist öffentlich, die Beschreibung ist eine interne Unterlage des Herstellers). Maßgeblich ist der Auszug im Briefing. Legt Michael sie lokal im Arbeitsverzeichnis ab, den Pfad vor dem nächsten Commit in `.gitignore` aufnehmen und prüfen, dass sie nicht gestaged ist.
- Zugangsdaten der Easy-PV-App gibt Michael selbst in HA ein. Nie im Chat erfragen, nie in Code, Tests, Fixtures oder Logs ablegen. Rohantworten für Fixtures anonymisieren (Seriennummern, Standort, Konto).
- `config/` enthält Laufzeitdaten der Test-Instanz und gehört nicht ins Repository, ausgenommen `config/configuration.yaml`.
- Entwickelt und getestet wird im Devcontainer gegen die dortige Test-Instanz (siehe „Umgebung“). Die produktive HA-Instanz auf der NAS wird nicht angefasst.
- Vor jedem Commit `scripts/lint` und die Tests laufen lassen (Skill `commit`).

## Umgebung: Devcontainer

Claude läuft als VS-Code-Erweiterung **im Devcontainer** (`.devcontainer/devcontainer.json`), nicht auf Michaels Windows-Rechner. Der Host ist Windows mit Docker Desktop (WSL2).

- **Image** `mcr.microsoft.com/devcontainers/python:3.14`, Benutzer `vscode` mit `sudo`. HA 2026.10.4 und die Testabhängigkeiten installiert `scripts/setup` beim Erstellen des Containers (`postCreateCommand`).
- **Repository** unter `/workspaces/ha-easy-pv-ew` auf einem Container-Volume (ext4), nicht auf einem Windows-Laufwerk.
- **Kein Zugriff** auf die NAS, das Laufwerk `Z:` oder das Heimnetz, und das ist so gewollt. Ins Internet kommt der Container, die Easy-PV-Cloud ist erreichbar.
- **Test-Instanz:** HA im Container auf Port 8123, VS Code leitet den Port an den Windows-Rechner weiter.
- **Git push** läuft über den Credential-Helper von VS Code und funktioniert nur, solange VS Code mit dem Container verbunden ist. `gh` ist nicht installiert.
- **Rebuild** des Containers (nach Änderungen an `devcontainer.json`) verwirft alles außerhalb von `/workspaces` und den Volumes: installierte Pakete, Shell-Verlauf. `~/.claude` (Login, Memories) liegt auf einem eigenen Volume. Ein Rebuild ist ein Schritt außerhalb des Repositorys und braucht Michaels OK; er löst ihn selbst in VS Code aus.
- **Temporäre Dateien:** `$TMPDIR` ist leer, und das Scratchpad-Verzeichnis der Session existiert anfangs nicht. Vorher `mkdir -p` und prüfen, bevor man sich auf eine Sicherungskopie verlässt. Um alten Code testweise zu prüfen, lieber `git stash` oder `git worktree` statt Kopieren.

## Befehle

- `scripts/test`: pytest mit `pytest-homeassistant-custom-component`; Argumente gehen an pytest durch
- `scripts/lint`: `ruff format` und `ruff check --fix`
- `scripts/develop`: Test-Instanz auf Port 8123 starten (Skill `ha-testinstanz`)
- `scripts/setup`: Abhängigkeiten aus `requirements_test.txt` installieren (läuft beim Erstellen des Containers)

## Code-Konventionen

- Code: `custom_components/easy_pv_ew/`, API-Client in `easy_pv/__init__.py`. Kommentare und Docstrings auf Englisch wie im Original, Commit-Nachrichten und Dokumentation auf Deutsch.
- Der API-Client bekommt die Session von `async_get_clientsession(hass)` und legt nie eine eigene an.
- Fehlertypen des Clients: `LoginError` (Anmeldung/Token) → im Coordinator `ConfigEntryAuthFailed`; alle anderen `BaseError` (`ApiError`, `InvalidResponseError`, `CommunicationError` für Netzwerk/DNS/Timeout) → `UpdateFailed`. `LoginError` nie unterwegs abfangen oder in `UpdateFailed` umwandeln, sonst startet kein Reauth.
- Nie Tokens, E-Mail, Seriennummern, IDs oder Standort loggen, auch nicht auf Debug. Der Debug-Logger der Integration ist in der Test-Instanz aktiv. Rohantworten nur anonymisiert loggen.
- Tests: Fixtures in `tests/fixtures/` (nachgebaut bzw. anonymisiert, feste Platzhalter wie `test-token`, Station `1001`, Gerät `2001`). HTTP über `aioclient_mock`; die Fixture `mock_api` in `tests/conftest.py` registriert alle Endpunkte erfolgreich.
- Für jede Fehlerbehebung aus dem Briefing einen Test, der den Fehler zeigt.

## Schnittstelle zum Energie-Setup (Kurzfassung)

- Gesamtertrag des EW: kWh aus `genPowerTotal` von `getDeviceDataInfo` (laut Beschreibung Wh, also / 1000; die Einheit an echten Daten prüfen, im MQTT-Telegramm des Geräts ist es kWh), `device_class: energy`, `state_class: total_increasing`, absolut seit Inbetriebnahme, nie ein Rücksprung, stabile Entity-ID.
- Leistung des EW: W, `device_class: power`, `state_class: measurement`.
- Bei Cloud-Ausfall lieber `unavailable` als falsche Werte.

Details und Hintergrund im Briefing.
