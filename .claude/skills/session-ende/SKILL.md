---
name: session-ende
description: Session sauber abschließen und an die nächste Claude-Session übergeben – Handover, offene Entscheidungen, Memories, CLAUDE.md und Skills aktualisieren. Verwenden, wenn Michael die Session beenden will („Feierabend“, „Übergabe“, „Handover“, „neue Session“) oder der Kontext voll wird.
---

# Session-Ende

Michael arbeitet über mehrere Sessions, damit der Kontext sauber bleibt. Die nächste Session kennt nur, was im Repository und in den Memories steht.

## 1. Dauerhaftes Wissen einordnen

Zuerst, damit beim Neuschreiben des Handovers nichts verloren geht. Für jede Erkenntnis der Session entscheiden, wohin sie gehört:

| Art | Ort |
| --- | --- |
| Projektregel, Konvention, Fallstrick im Code | `CLAUDE.md` |
| Wiederkehrender Ablauf mit mehreren Schritten | Skill unter `.claude/skills/<name>/SKILL.md` (neu oder bestehenden ergänzen; neue Skills in `CLAUDE.md` auflisten) |
| Michaels Arbeitsweise und Vorlieben | Memory (`~/.claude/projects/-workspaces-ha-easy-pv-ew/memory/`, Index `MEMORY.md`) |
| Entscheidung, die Michael treffen muss oder getroffen hat | `docs/offene-entscheidungen.md` |
| Nur für die nächste Session relevant | `docs/HANDOVER.md` |

Bestehende Einträge aktualisieren statt duplizieren, Überholtes löschen.

## 2. Alten Stand archivieren

```bash
mkdir -p docs/handover-archiv
cp docs/HANDOVER.md "docs/handover-archiv/$(date +%Y-%m-%d_%H%M).md"
```

Das Archiv wird nicht mehr bearbeitet und von `session-start` nicht gelesen. Es dient nur zum Nachschlagen.

## 3. Handover neu schreiben: `docs/HANDOVER.md`

Neu schreiben, nicht fortschreiben. Für jede Zeile gilt der Test: **Braucht die nächste Session das, um sicher weiterzuarbeiten?** Wenn nein, kommt sie nicht hinein.

Hinein gehört:

- **Stand:** heutiges Datum und Hash des letzten Commits vor dem Handover-Commit (`git rev-parse --short HEAD` vor Schritt 5); ein Commit kann seinen eigenen Hash nicht enthalten.
- **Wo wir stehen:** die Schritte laut Briefing als kompakte Statusübersicht; Details nur für den laufenden Schritt.
- **Nächster Schritt:** so konkret, dass die nächste Session ohne Rückfrage anfangen kann (Datei, Ziel, offene Teilaufgabe).
- **Offene Fragen und Annahmen**, die die anstehende Arbeit betreffen.
- **Hinweise:** ungepushte Commits, halbfertige Arbeit (uncommittete Änderungen, Stash), einmalige Fallstricke für die nächste Session.

Nicht hinein gehört:

- erledigte Punkte mit Details, Verlauf der Session, Begründungen vergangener Änderungen (steht in `git log`)
- dauerhafte Regeln (stehen in `CLAUDE.md`), Entscheidungsfragen (stehen in `docs/offene-entscheidungen.md`)
- Hinweise, die sich erledigt haben (z. B. ein einmaliger Rebuild, der inzwischen gelaufen ist)

Ziel: eine Bildschirmseite.

## 4. Offene Entscheidungen: `docs/offene-entscheidungen.md`

Neue Fragen an Michael ergänzen (Hintergrund, Optionen mit Vor- und Nachteilen, Empfehlung, wann zu entscheiden). Getroffene Entscheidungen mit Datum unter „Entschieden“ verschieben.

## 5. Commit

Mit dem Skill `commit`, inklusive Archivdatei. Nicht pushen, außer Michael gibt das OK.

## 6. Abschlussmeldung an Michael

Drei bis fünf Zeilen: was erledigt ist, was als Nächstes kommt, ob etwas auf seine Entscheidung oder ein OK wartet (z. B. Push).
