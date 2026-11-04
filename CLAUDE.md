# Easy PV (EW) – Fork von ha-easy-pv

Home-Assistant-Integration für den Balkonkraftwerk-Wechselrichter Electronic Way (EW) VN2T08EU über die Easy-PV-Cloud.

**Auftrag, Anforderungen und Ablauf: `docs/briefing-ew.md`.** Vor der Arbeit lesen; bei Widersprüchen gilt das Briefing.

## Arbeitsregeln

- Mit Michael Deutsch sprechen.
- Vor jedem schreibenden Schritt außerhalb des Repositorys (z. B. Push, Release, Änderungen an einer HA-Instanz) zeigen, was passiert, und auf Michaels OK warten. Änderungen im Repository dürfen ohne Rückfrage erfolgen; Commits mit aussagekräftiger Nachricht.
- Zugangsdaten der Easy-PV-App gibt Michael selbst in HA ein. Nie im Chat erfragen, nie in Code, Tests, Fixtures oder Logs ablegen. Rohantworten für Fixtures anonymisieren (Seriennummern, Standort, Konto).
- `config/` enthält Laufzeitdaten der Test-Instanz und gehört nicht ins Repository, ausgenommen `config/configuration.yaml`.
- Entwickelt und getestet wird im Devcontainer gegen die dortige Test-Instanz. Die produktive HA-Instanz auf der NAS wird nicht angefasst.
- Vor jedem Commit `scripts/lint` und die Tests laufen lassen.

## Schnittstelle zum Energie-Setup (Kurzfassung)

- Gesamtertrag des EW: kWh, `device_class: energy`, `state_class: total_increasing`, absolut seit Inbetriebnahme, nie ein Rücksprung, stabile Entity-ID.
- Leistung des EW: W, `device_class: power`, `state_class: measurement`.
- Bei Cloud-Ausfall lieber `unavailable` als falsche Werte.

Details und Hintergrund im Briefing.
