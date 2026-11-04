---
name: commit
description: Änderungen in diesem Repository committen – mit Lint, Tests und Prüfung auf Zugangsdaten und persönliche Daten. Verwenden, wann immer ein Arbeitsschritt abgeschlossen ist und committet werden soll, auch ohne ausdrückliche Aufforderung.
---

# Commit

Ablauf für jeden Commit in diesem Repository. Committen darf ohne Rückfrage erfolgen, **pushen nie ohne Michaels OK**.

## 1. Prüfen

```bash
scripts/lint    # formatiert und korrigiert; danach muss "All checks passed!" kommen
scripts/test
```

Schlägt etwas fehl: beheben, nicht committen. Hat `scripts/lint` Dateien umformatiert, die Änderungen mit in den Commit nehmen.

## 2. Diff auf vertrauliche Daten prüfen

```bash
git status --short
git diff HEAD
```

Nichts davon darf im Diff stehen, auch nicht in Tests, Fixtures, Kommentaren oder Logs:

- Easy-PV-Zugangsdaten, echte Tokens (Fixtures verwenden `test-token`)
- echte Seriennummern, Geräte- oder Stations-IDs, Standort, Adresse, Koordinaten, Kontoname, E-Mail
- Dateien aus `config/` außer `config/configuration.yaml`

Bei Fixtures aus echten Antworten vorher den Skill `fixture-anonymisieren` anwenden.

## 3. Commit-Nachricht

- Deutsch, erste Zeile kurz und konkret (was und warum, Bezug zum Briefing wie „(Fehler 3)“).
- Danach eine Liste der wesentlichen Änderungen, gern mit Begründung bei nicht offensichtlichen Entscheidungen.
- Schluss mit der Attribution-Zeile aus dem System-Reminder der Session (aktuell `Co-Authored-By: Claude …`).

```bash
git add -A
git commit -F - <<'EOF'
…
EOF
```

## 4. Danach

- Kurz melden: Commit-Hash, was drin ist, Teststand.
- Wurde ein Punkt aus `docs/HANDOVER.md` erledigt, das Handover im selben oder nächsten Commit abhaken.
