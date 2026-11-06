---
name: session-ende
description: Session sauber abschließen und an die nächste Claude-Session übergeben – Wissen einordnen (CLAUDE.md, Skills, Memories, offene Entscheidungen) und das Handover aufräumen. Verwenden, wenn Michael die Session beenden will („Feierabend“, „Übergabe“, „Handover“, „neue Session“) oder der Kontext voll wird.
---

# Session-Ende

Das Handover wird laufend gepflegt (Skill `handover-pflegen`), eine Session darf also auch ohne diesen Skill enden. `session-ende` ist der Aufräumschritt: Er ordnet Wissen ein und prüft das Handover noch einmal als Ganzes.

## 1. Dauerhaftes Wissen einordnen

Für jede Erkenntnis der Session entscheiden, wohin sie gehört:

| Art | Ort |
| --- | --- |
| Projektregel, Konvention, Fallstrick im Code | `CLAUDE.md` |
| Regel nur für Michaels Umgebung (Austauschordner, eigene Devcontainer-Fassung) | `local/` (z. B. `local/austausch.md`), nicht `CLAUDE.md` |
| Vorgabe zur Nutzung in Michaels HA (Energie-Setup, Entity-IDs) | führt das Projekt; Änderungswunsch als Meldung ans Projekt |
| Wiederkehrender Ablauf mit mehreren Schritten | Skill unter `.claude/skills/<name>/SKILL.md` (neu oder bestehenden ergänzen; neue Skills in `CLAUDE.md` auflisten) |
| Michaels Arbeitsweise und Vorlieben | Memory (`~/.claude/projects/-workspaces-ha-easy-pv-ew/memory/`, Index `MEMORY.md`) |
| Entscheidung, die Michael treffen muss oder getroffen hat | `local/offene-entscheidungen.md` (Hintergrund, Optionen, Empfehlung, Zeitpunkt; Getroffenes mit Datum unter „Entschieden“) |
| Nur für die nächste Session relevant | `local/HANDOVER.md` |

Bestehende Einträge aktualisieren statt duplizieren, Überholtes löschen.

## 2. Handover aufräumen

Skill `handover-pflegen` anwenden und dabei das ganze Handover mit der Relevanzfrage durchgehen, nicht nur die zuletzt geänderten Abschnitte. Halbfertige, uncommittete Arbeit unter „Nächster Schritt“ beschreiben.

## 3. Commit

Mit dem Skill `commit` (Handover und offene Entscheidungen liegen in `local/` und werden nicht mitcommittet). Nicht pushen, außer Michael gibt das OK.

## 4. Abschlussmeldung an Michael

Drei bis fünf Zeilen: was erledigt ist, was als Nächstes kommt, ob etwas auf seine Entscheidung oder ein OK wartet (z. B. Push).
