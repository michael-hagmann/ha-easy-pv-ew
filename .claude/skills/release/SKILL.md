---
name: release
description: Neue Version der Integration veröffentlichen – Version im Manifest, Tag, Push, Prüfung auf GitHub, Release durch Michael, Meldung ans Projekt. Verwenden, wenn Michael ein Release, eine neue Version oder ein Tag will.
---

# Release

Push, Tag und Release sind Schritte außerhalb des Repositorys: jeweils vorher zeigen, was passiert, und auf Michaels OK warten.

## 1. Vorbereiten

- `an-code/` im Austauschordner ansehen (`local/austausch.md`).
- Version festlegen (Michael fragen), Schema `0.x.y` bis nach dem ersten Winter; in `custom_components/easy_pv_ew/manifest.json` setzen. Die Schlüssel dort bleiben in der Reihenfolge `domain`, `name`, dann alphabetisch (Hassfest, Test in `tests/test_manifest.py`).
- Zusammengehörige Änderungen vor dem Push zu einem Commit zusammenfassen, wenn Michael das will (`git reset --soft <Basis>`, neuer Commit, vorher prüfen, dass der Baum gleich bleibt: `git rev-parse HEAD^{tree}`).
- Skill `commit`, danach alle ungepushten Commits durchsehen (`git log -p origin/master..HEAD`).

## 2. Push und Tag (mit OK)

```bash
git push origin master
git tag -a vX.Y.Z <sha> -m "Easy PV (EW) X.Y.Z"
timeout 60 git push origin vX.Y.Z
```

Ein Push kann am Credential-Helper von VS Code hängen bleiben; deshalb mit `timeout` und bei Bedarf wiederholen. Ein Tag nur verschieben (`git tag -f`, `git push --force`), solange es kein Release dazu gibt und Michael zustimmt; sonst neue Version.

## 3. Prüfung auf GitHub (Michael)

`gh` ist nicht installiert. Michael startet *Actions → Validate → Run workflow* (Lint läuft beim Push). Bekannte Voraussetzungen der HACS-Action: Beschreibung, Topics und Issues im Repository gesetzt; `hacs.json` nur mit gültigen Schlüsseln (Test vorhanden). Repository-Einstellungen lassen sich ohne Anmeldung prüfen:

```bash
curl -s https://api.github.com/repos/michael-hagmann/ha-easy-pv-ew | python3 -c "import json,sys;d=json.load(sys.stdin);print({k:d.get(k) for k in ('description','topics','has_issues')})"
```

Ein Fork führt Workflows erst aus, wenn Michael sie im Reiter *Actions* freigegeben hat (seit 08.11.2026 erledigt).

## 4. Release (Michael, im Browser)

Releases legt Michael unter *Releases → Draft a new release* zum vorhandenen Tag an; HACS zeigt Versionen nur bei Releases. Text auf Englisch vorschlagen, kurz, nur was sich für Nutzer ändert. Prüfen: `curl -s https://api.github.com/repos/michael-hagmann/ha-easy-pv-ew/releases/latest`.

## 5. Danach

- Meldung nach `an-projekt/` (`JJJJ-MM-TT-HHMM-thema.md`, Uhrzeit in MEZ, erste Zeile „EW-Integration:“): Version, Link, Wirkung auf Werte und Entity-IDs. Michael gibt sie weiter.
- Michael aktualisiert im produktiven HA per HACS (⋮ → Informationen aktualisieren → Herunterladen → HA neu starten).
- Handover pflegen.
