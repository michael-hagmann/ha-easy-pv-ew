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
git config user.email   # muss die Noreply-Adresse aus CLAUDE.md sein, nie eine private
```

Die Ausgabe **nicht** durch eine Pipe schicken (`scripts/lint | tail`) und nicht mit `&&` an `git commit` hängen: Die Pipe übernimmt den Exit-Code von `tail`, ein Lint-Fehler fällt dann nicht auf. Ist die Ausgabe zu lang, mit `set -o pipefail` arbeiten.

Schlägt etwas fehl: beheben, nicht committen. Hat `scripts/lint` Dateien umformatiert, die Änderungen mit in den Commit nehmen.

## 2. Diff auf vertrauliche Daten prüfen

```bash
git status --short
git diff HEAD
```

Nichts davon darf im Diff stehen, auch nicht in Tests, Fixtures, Kommentaren oder Logs:

- Easy-PV-Zugangsdaten, echte Tokens (Fixtures verwenden `test-token`)
- echte Seriennummern, Geräte- oder Stations-IDs, Standort, Adresse, Koordinaten, Kontoname, E-Mail
- Benutzernamen und persönliche Pfade des Entwicklungsrechners, z. B. unter `C:\Users\…`, `/mnt/c/Users/…` oder `/home/…` (in Beispielen `<Benutzername>`)
- Dateien aus `config/` außer `config/configuration.yaml`
- Dateien aus `local/` (OpenAPI-Beschreibung, Briefing, Handover, offene Entscheidungen); die Adresse der Beschreibung darf stehen (`openapi_url` im Vertrag)

Bei Fixtures aus echten Antworten vorher den Skill `fixture-anonymisieren` anwenden.

## 3. Handover

Ändert der Commit den Projektstand (erledigter Punkt, neuer nächster Schritt, neue offene Frage), vorher den Skill `handover-pflegen` anwenden. `local/HANDOVER.md` wird nicht mitcommittet. Beim ersten Mal in einer neuen Session archiviert er dabei den Stand der Vorsession.

## 4. Commit-Nachricht

- Deutsch, erste Zeile kurz und konkret (was und warum, Bezug zum Briefing wie „(Fehler 3)“).
- Danach eine Liste der wesentlichen Änderungen, gern mit Begründung bei nicht offensichtlichen Entscheidungen.
- Schluss mit der Attribution-Zeile aus dem System-Reminder der Session (aktuell `Co-Authored-By: Claude …`).

```bash
git add -A
git commit -F - <<'EOF'
…
EOF
```

## 5. Vor einem Push

Nur mit Michaels OK. Vorher **alle** ungepushten Commits prüfen, nicht nur den letzten, denn auch Commits aus Vorsessionen gehen mit:

```bash
git log --oneline origin/master..HEAD
git log -p origin/master..HEAD   # auf die Punkte aus Abschnitt 2 durchsehen
```

Was einmal auf GitHub liegt, bleibt per SHA abrufbar, auch nach Umschreiben der Historie.

## 6. Danach

Kurz melden: Commit-Hash, was drin ist, Teststand.
