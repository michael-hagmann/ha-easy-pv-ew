---
name: session-start
description: Neue Claude-Session in diesem Projekt beginnen – Memories, Handover, offene Entscheidungen und Git-Stand lesen, abgleichen und Michael den Einstieg zusammenfassen. Zu Beginn jeder Session anwenden, bevor an Code gearbeitet wird, auch wenn Michael direkt mit einer Aufgabe einsteigt.
---

# Session-Start

Die neue Session kennt nur, was im Repository und in den Memories steht. Erst lesen und abgleichen, dann arbeiten.

## 1. Lesen

1. **Memories:** Das Verzeichnis `~/.claude/projects/-workspaces-ha-easy-pv-ew/memory/` mit `MEMORY.md` und den verlinkten Dateien. Ist es leer (z. B. nach einem Rebuild ohne Volume), das im Bericht erwähnen; die Arbeitsregeln stehen auch in `CLAUDE.md`.
2. **Handover:** `docs/HANDOVER.md`, vollständig.
3. **Offene Entscheidungen:** `docs/offene-entscheidungen.md`.
4. **Git-Stand:**

   ```bash
   git status --short --branch
   git log --oneline -15
   git log --oneline origin/master..HEAD   # ungepushte Commits
   git stash list
   ```

5. Das Briefing (`docs/briefing-ew.md`) nur lesen, wenn der nächste Schritt es braucht oder das Handover darauf verweist.

## 2. Abgleichen

- **Handover gegen Git:** Der „Stand“ nennt den letzten Commit vor dem Handover. Danach wird genau ein Commit erwartet, der das Handover schreibt (`git log --oneline <hash>..HEAD`). Gibt es weitere, ist das Handover veraltet. Michael darauf hinweisen und aus den Commit-Nachrichten den tatsächlichen Stand ableiten.
- **Arbeitsverzeichnis:** Uncommittete Änderungen oder Stashes bedeuten halbfertige Arbeit aus der letzten Session. Nicht verwerfen, im Bericht nennen.
- **Umgebung, kurz:** `python --version` (erwartet 3.14) und `scripts/test` (läuft schnell). Scheitert etwas, ist das der erste Punkt im Bericht.

## 3. Bericht an Michael

Kurz und auf Deutsch, höchstens etwa zehn Zeilen:

- wo wir stehen (Schritt laut Briefing, letzter Commit)
- was laut Handover als Nächstes kommt
- was auf Michael wartet: offene Entscheidungen, deren Zeitpunkt gekommen ist; ungepushte Commits (Push nur mit OK)
- Auffälligkeiten aus dem Abgleich (veraltetes Handover, halbfertige Arbeit, rote Tests)

Dann fragen, ob es mit dem nächsten Schritt losgehen soll, außer Michael hat schon eine Aufgabe genannt. In dem Fall nach dem Bericht direkt damit anfangen.
