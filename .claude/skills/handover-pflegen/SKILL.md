---
name: handover-pflegen
description: local/HANDOVER.md laufend aktuell halten und beim ersten Ändern in einer neuen Session den Stand der Vorsession archivieren. Bei jedem Commit anwenden, der den Projektstand ändert (über den Skill commit), außerdem bei neuen offenen Fragen, Fallstricken oder geändertem nächsten Schritt und in session-ende.
---

# Handover pflegen

Das Handover ist zu jedem Zeitpunkt die Übergabe an die nächste Session. Endet eine Session unerwartet (voller Kontext, Fenster zu, Rebuild), ist es höchstens einen Commit alt.

Handover und Archiv liegen in `local/` und sind **nicht eingecheckt** (siehe `CLAUDE.md`, „Projektunterlagen nur lokal“). Nie nach `docs/` oder an einen anderen eingecheckten Ort schreiben.

## 1. Archivieren, falls neue Session

Im Kopf von `local/HANDOVER.md` steht `**Session:** JJJJ-MM-TT_HHMM`. Die aktuelle Session-Kennung hat `session-start` zu Beginn festgelegt und Michael genannt.

- **Kennung gleich der aktuellen Session:** nicht archivieren, weiter mit 2.
- **Kennung abweichend:** Das Handover ist der Endstand der Vorsession. Erst archivieren, dann ändern:

  ```bash
  alt=$(grep -oP '^\*\*Session:\*\* \K[0-9_-]+' local/HANDOVER.md)
  mkdir -p local/handover-archiv
  [ -e "local/handover-archiv/$alt.md" ] || cp local/HANDOVER.md "local/handover-archiv/$alt.md"
  ```

  Danach die Kennung im Handover auf die aktuelle Session setzen. Existiert die Archivdatei schon, wird nichts überschrieben; der Schritt ist also wiederholbar.

Ist die aktuelle Kennung nicht mehr bekannt (z. B. nach Zusammenfassung des Kontexts), gilt: Existiert im Archiv schon eine Datei mit der Kennung der Vorsession und ist `**Aktualisiert:**` im Handover von heute, ist die Kennung im Handover die aktuelle.

Das Archiv wird nicht mehr bearbeitet und von `session-start` nicht gelesen. Es dient nur zum Nachschlagen.

## 2. Aktualisieren

Betroffene Abschnitte **ersetzen, nicht ergänzen**. Erledigtes streichen, statt es als erledigt stehen zu lassen. Ausnahme ist die Statusübersicht der Schritte.

Für jede Zeile gilt: **Braucht die nächste Session das, um sicher weiterzuarbeiten?** Wenn nein, kommt sie nicht hinein.

Struktur:

- **Kopf:** `**Session:**` (siehe oben) und `**Aktualisiert:**` mit Datum und Uhrzeit.
- **Wo wir stehen:** die Schritte laut Briefing als kompakte Statusübersicht; Details nur für den laufenden Schritt.
- **Nächster Schritt:** so konkret, dass die nächste Session ohne Rückfrage anfangen kann (Datei, Ziel, offene Teilaufgabe). Bei halbfertiger Arbeit: was schon steht und was fehlt.
- **Offene Fragen und Annahmen**, die die anstehende Arbeit betreffen.
- **Hinweise:** ungepushte Commits, einmalige Fallstricke für die nächste Session.

Nicht hinein gehört:

- Verlauf der Session, Begründungen vergangener Änderungen (steht in `git log`)
- dauerhafte Regeln (gehören in `CLAUDE.md`), Entscheidungsfragen (gehören in `local/offene-entscheidungen.md`), Arbeitsvorlieben (Memory)
- Hinweise, die sich erledigt haben

Ziel: eine Bildschirmseite.

## 3. Zeitpunkt

Das Handover vor jedem Commit aktualisieren, der den Projektstand ändert (Skill `commit`), damit Code und Handover nie auseinanderlaufen. Es wird nicht mitcommittet. Ändert sich nur das Handover (z. B. neue offene Frage), genügt das Speichern.
