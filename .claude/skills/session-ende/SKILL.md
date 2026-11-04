---
name: session-ende
description: Session sauber abschließen und an die nächste Claude-Session übergeben – Handover, offene Entscheidungen, Memories, CLAUDE.md und Skills aktualisieren. Verwenden, wenn Michael die Session beenden will („Feierabend“, „Übergabe“, „Handover“, „neue Session“) oder der Kontext voll wird.
---

# Session-Ende

Michael arbeitet über mehrere Sessions, damit der Kontext sauber bleibt. Die nächste Session kennt nur, was im Repository und in den Memories steht.

## 1. Handover aktualisieren: `docs/HANDOVER.md`

- **Stand** auf das heutige Datum setzen.
- Tabelle und Checkliste abhaken; nur den aktuellen Stand festhalten, die Historie steht in `git log`.
- **Nächster Schritt:** so konkret, dass die nächste Session ohne Rückfrage anfangen kann (Datei, Ziel, offene Teilaufgabe).
- **Offene Fragen und Annahmen:** neue ergänzen, geklärte entfernen.
- **Hinweise:** ungepushte Commits, halbfertige Arbeit, Fallstricke, die Zeit gekostet haben.
- Kurz halten. Was dauerhaft gilt, gehört nicht ins Handover, sondern in `CLAUDE.md`.

## 2. Offene Entscheidungen: `docs/offene-entscheidungen.md`

Neue Fragen an Michael ergänzen (mit Optionen, Vor- und Nachteilen, wann zu entscheiden). Getroffene Entscheidungen mit Datum unter „Entschieden“ verschieben.

## 3. Dauerhaftes Wissen einordnen

Für jede Erkenntnis der Session entscheiden, wohin sie gehört:

| Art | Ort |
| --- | --- |
| Projektregel, Konvention, Fallstrick im Code | `CLAUDE.md` |
| Wiederkehrender Ablauf mit mehreren Schritten | Skill unter `.claude/skills/<name>/SKILL.md` (neu oder bestehenden ergänzen) |
| Michaels Arbeitsweise und Vorlieben | Memory (`~/.claude/projects/-workspaces-ha-easy-pv-ew/memory/`) |
| Aktueller Stand, nächster Schritt | `docs/HANDOVER.md` |

Bestehende Einträge aktualisieren statt duplizieren, Überholtes löschen.

## 4. Commit

Mit dem Skill `commit`. Nicht pushen, außer Michael gibt das OK.

## 5. Abschlussmeldung an Michael

Drei bis fünf Zeilen: was erledigt ist, was als Nächstes kommt, ob etwas auf seine Entscheidung oder ein OK wartet (z. B. Push).
