# Easy PV (EW) – Fork von ha-easy-pv

Home-Assistant-Integration für den Balkonkraftwerk-Wechselrichter Electronic Way (EW) VN2T08EU über die Easy-PV-Cloud.

**Auftrag, Anforderungen und Ablauf: `docs/briefing-ew.md`.** Vor der Arbeit lesen; bei Widersprüchen gilt das Briefing.

## Arbeit über mehrere Sessions

Michael arbeitet in mehreren Claude-Sessions, damit der Kontext sauber bleibt.

- **Zu Beginn jeder Session** den Skill `session-start` anwenden, bevor an Code gearbeitet wird: Memories, `docs/HANDOVER.md`, `docs/offene-entscheidungen.md` und Git-Log lesen und abgleichen.
- **Am Ende einer Session** oder bei vollem Kontext den Skill `session-ende` anwenden. Er archiviert das alte Handover in `docs/handover-archiv/` und schreibt es neu; das Handover enthält nur, was die nächste Session braucht.
- Dauerhaftes Wissen gehört ins Repository (diese Datei, Handover, Skills), nicht nur in Memories. `~/.claude` liegt erst seit dem Volume in `.devcontainer/devcontainer.json` außerhalb des Containers.
- Wiederkehrende Abläufe als Skill unter `.claude/skills/` ablegen. Vorhanden:
  - `session-start`: Einstieg in eine Session, Stand abgleichen und berichten
  - `commit`: Lint, Tests, Prüfung auf vertrauliche Daten, Commit-Nachricht
  - `session-ende`: Wissen einordnen, Handover archivieren und neu schreiben
  - `ha-testinstanz`: Test-Instanz starten, Log auswerten (Schritt 6)
  - `fixture-anonymisieren`: echte API-Antworten in Fixtures überführen (Schritt 6)
- Ein Agent für Planung, Implementierung und Tests; vor dem Release ein `/code-review` über den gesamten Diff.
- Entscheidungsfragen an Michael mit Hintergrund stellen: Ist-Zustand, Problem, Optionen mit Vor- und Nachteilen, Empfehlung. Offene Entscheidungen in `docs/offene-entscheidungen.md` festhalten statt sie nur im Chat zu stellen.

## Arbeitsregeln

- Mit Michael Deutsch sprechen.
- Vor jedem schreibenden Schritt außerhalb des Repositorys (z. B. Push, Release, Änderungen an einer HA-Instanz) zeigen, was passiert, und auf Michaels OK warten. Änderungen im Repository dürfen ohne Rückfrage erfolgen; Commits mit aussagekräftiger Nachricht.
- Zugangsdaten der Easy-PV-App gibt Michael selbst in HA ein. Nie im Chat erfragen, nie in Code, Tests, Fixtures oder Logs ablegen. Rohantworten für Fixtures anonymisieren (Seriennummern, Standort, Konto).
- `config/` enthält Laufzeitdaten der Test-Instanz und gehört nicht ins Repository, ausgenommen `config/configuration.yaml`.
- Entwickelt und getestet wird im Devcontainer gegen die dortige Test-Instanz. Die produktive HA-Instanz auf der NAS wird nicht angefasst.
- Vor jedem Commit `scripts/lint` und die Tests laufen lassen (Skill `commit`).

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

- Gesamtertrag des EW: kWh, `device_class: energy`, `state_class: total_increasing`, absolut seit Inbetriebnahme, nie ein Rücksprung, stabile Entity-ID.
- Leistung des EW: W, `device_class: power`, `state_class: measurement`.
- Bei Cloud-Ausfall lieber `unavailable` als falsche Werte.

Details und Hintergrund im Briefing.
