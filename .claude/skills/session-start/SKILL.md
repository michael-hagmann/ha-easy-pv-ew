---
name: session-start
description: Neue Claude-Session in diesem Projekt beginnen – Memories, Handover, offene Entscheidungen und Git-Stand lesen, abgleichen und Michael den Einstieg zusammenfassen. Zu Beginn jeder Session anwenden, bevor an Code gearbeitet wird, auch wenn Michael direkt mit einer Aufgabe einsteigt.
---

# Session-Start

Die neue Session kennt nur, was im Repository und in den Memories steht. Erst lesen und abgleichen, dann arbeiten.

## 1. Lesen

1. **Memories:** Das Verzeichnis `~/.claude/projects/-workspaces-ha-easy-pv-ew/memory/` mit `MEMORY.md` und den verlinkten Dateien. Ist es leer (z. B. nach einem Rebuild ohne Volume), das im Bericht erwähnen; die Arbeitsregeln stehen auch in `CLAUDE.md`.
2. **Handover:** `local/HANDOVER.md`, vollständig.
3. **Offene Entscheidungen:** `local/offene-entscheidungen.md`.
3a. **Austauschordner** (Regeln in `local/austausch.md`): Existiert `/workspaces/austausch`, `LIESMICH.md` lesen und `an-code/` ansehen, neue Dateien nach den Regeln abarbeiten. Existiert nur der Ordner oder nur `local/austausch.md`, das im Bericht nennen (Mount oder lokale Datei fehlt). Fehlt beides, ist es keine Umgebung mit Austauschordner.
4. **Git-Stand:**

   ```bash
   git status --short --branch
   git log --oneline -15
   git log --oneline origin/master..HEAD   # ungepushte Commits
   git stash list
   ```

5. **Fehlt eine der Dateien in `local/`** (Handover, offene Entscheidungen, Schnittstelle Energie-Setup), ist das der erste Punkt im Bericht: Sie sind nicht eingecheckt (siehe `CLAUDE.md`, „Projektunterlagen nur lokal“). Kam eine neue Vorgabe des Projekts (Schritt 3a), mit Handover und Code abgleichen und Widersprüche im Bericht nennen.

## 2. Abgleichen

- **Handover gegen Git:** Das Handover ist nicht eingecheckt und wird vor jedem Commit gepflegt. Commits nach seiner letzten Änderung bedeuten, dass es veraltet ist:

  ```bash
  git log --oneline --since="$(date -r local/HANDOVER.md --iso-8601=seconds)"
  ```

  Ist die Ausgabe nicht leer, Michael darauf hinweisen und aus den Commit-Nachrichten den tatsächlichen Stand ableiten. Zur Kontrolle dient auch `**Aktualisiert:**` im Kopf des Handovers.
- **Arbeitsverzeichnis:** Uncommittete Änderungen oder Stashes bedeuten halbfertige Arbeit aus der letzten Session. Nicht verwerfen, im Bericht nennen.
- **Umgebung, kurz:** `python --version` (erwartet 3.14) und `scripts/test` (läuft schnell). Scheitert etwas, ist das der erste Punkt im Bericht.

## 3. Session-Kennung festlegen

```bash
date +%Y-%m-%d_%H%M
```

Diese Kennung gilt für die ganze Session. Der Skill `handover-pflegen` braucht sie, um bei der ersten Änderung des Handovers den Stand der Vorsession zu archivieren. Jetzt noch **nichts archivieren und das Handover nicht ändern**: Eine Session, die nur liest, hinterlässt kein Archiv.

## 4. Bericht an Michael

Kurz und auf Deutsch, höchstens etwa zehn Zeilen:

- Session-Kennung
- wo wir stehen (Schritt laut Statusübersicht im Handover, letzter Commit)
- was laut Handover als Nächstes kommt
- was auf Michael wartet: offene Entscheidungen, deren Zeitpunkt gekommen ist; ungepushte Commits (Push nur mit OK)
- Auffälligkeiten aus dem Abgleich (veraltetes Handover, halbfertige Arbeit, rote Tests)

Dann fragen, ob es mit dem nächsten Schritt losgehen soll, außer Michael hat schon eine Aufgabe genannt. In dem Fall nach dem Bericht direkt damit anfangen.
