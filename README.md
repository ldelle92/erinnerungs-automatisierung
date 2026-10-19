# Erinnerungs-Automatisierung für wiederkehrende Kontrolltermine

Ein Python-Tool für einen Betrieb, der Baumkontrollen und Baumgutachten in festen Abständen wiederholt. Bisher wurden die fälligen Termine von Hand in einer Google-Tabelle gesucht und die Kunden einzeln angeschrieben. Das Skript übernimmt diese Arbeit auf dem Mac des Betriebs:

- Es liest täglich die **Google-Tabelle** und ermittelt die fälligen Kontrollen.
- Für jeden fälligen Termin legt es einen **Erinnerungs-Entwurf in Apple Mail** an. Das Senden bleibt beim Menschen, nichts geht ungeprüft raus.
- Es prüft im Gesendet-Postfach, ob die Mail **tatsächlich verschickt** wurde, und trägt das Datum in die Tabelle ein.
- Nach einer Wartezeit sucht es in allen Postfächern nach einer **Antwort des Kunden**. Kommt keine, folgt eine zweite Erinnerung.
- Findet eine neue Kontrolle statt, setzt es den Status zurück, und der Zyklus beginnt von vorn.

> Hinweis: Dies ist eine anonymisierte Fassung des Projekts. Kundendaten, die echte Tabelle und interne Dokumentation sind entfernt.

## Ablauflogik

1. **Fälligkeit:** Wenn die Spalte „nächster Termin“ gefüllt ist, gilt dieses Datum. Sonst wird die Fälligkeit aus „letzte Kontrolle“ plus „Intervall (Monate)“ berechnet.
2. **Entwurf 1:** Ist ein Termin fällig, legt das Skript einen Entwurf an und vermerkt „Entwurf 1 erstellt am“. Fehlt die E-Mail-Adresse, entsteht stattdessen ein interner Hinweis-Entwurf, damit die Adresse nachgetragen wird.
3. **Versand bestätigen:** Erst wenn die Mail im Gesendet-Postfach auftaucht, trägt das Skript „Erinnerung 1 gesendet am“ mit dem echten Sendedatum ein.
4. **Antwort erkennen:** Nach der Wartezeit (Standard: 14 Tage) durchsucht das Skript die Postfächer nach einer Antwort. Findet es eine, trägt es das Antwortdatum ein. Sonst legt es Entwurf 2 an, mit einem internen Prüfhinweis ganz oben.
5. **Manuelles Nachfassen:** Bleibt auch Erinnerung 2 unbeantwortet, vermerkt das Skript das in der Tabelle. Ab hier fasst ein Mensch nach.
6. **Neuer Zyklus:** Wird eine neue Kontrolle eingetragen, setzt das Skript alle Status-Spalten automatisch zurück.

## Technische Umsetzung

| Datei | Aufgabe |
|---|---|
| `src/main.py` | Ablauflogik, Kommandozeile (`--dry-run`, `--only-row`), Wiederholversuche bei Netzwerkfehlern |
| `src/sheets_client.py` | Zugriff auf Google Sheets über einen Service Account (`gspread`), Schreibvorgänge gebündelt |
| `src/mail_applescript.py` | Steuerung von Apple Mail per AppleScript: Entwürfe anlegen, Gesendet-Postfach und Antworten durchsuchen |
| `src/templates.py` | Mail-Vorlagen und interne Hinweise |
| `scripts/setup_mac.sh` | Einrichtung mit einem Befehl: prüft und installiert Python, Homebrew und die Abhängigkeiten |
| `scripts/install_launchd.sh` | Richtet den zeitgesteuerten Lauf über `launchd` ein, mit automatisch eingetragenem Projektpfad |

**Robust im Alltag:**
- Der Job startet alle 15 Minuten, arbeitet aber nur einmal pro Tag erfolgreich. Nach Internet-Ausfällen oder Ruhezustand holt er den Lauf so zügig nach.
- Alle Schritte landen in einem Protokoll, damit nachvollziehbar ist, an wen wann was ging.
- `--dry-run` zeigt, was passieren würde, ohne zu schreiben oder zu senden. Mit `--only-row` lässt sich eine einzelne Zeile kontrolliert testen.
- Die Spaltenzuordnung steht vollständig in der Konfiguration. Das Tool passt so auch zu anderen Tabellen, ohne dass der Code geändert werden muss.

## Einrichtung

```bash
bash scripts/setup_mac.sh          # Python-Umgebung + Abhängigkeiten
cp config.example.yaml config.yaml # Tabellen-ID, Blattname, Spalten eintragen
```

1. Lege in der Google Cloud Console einen Service Account an, aktiviere die Sheets API und speichere den JSON-Schlüssel als `credentials/service_account.json`. Diese Datei ist per `.gitignore` ausgeschlossen.
2. Teile die Tabelle mit der `client_email` des Service Accounts (Bearbeitungsrechte).
3. Testen und einrichten:

```bash
.venv/bin/python3 src/main.py --dry-run   # nur anzeigen
.venv/bin/python3 src/main.py             # Entwürfe anlegen
bash scripts/install_launchd.sh           # automatischen Lauf einrichten
```

Beim ersten echten Lauf fragt macOS nach der Erlaubnis, Apple Mail zu steuern. Diese Erlaubnis ist nötig.

## Ideen für später

- **Kundenantworten mit KI einordnen** (Ja / Nein / Unklar, plus Kurzfassung) und als Hinweis in eine eigene Spalte schreiben, ohne automatisch etwas auszulösen.
- Weitere wiederkehrende Fristen nach demselben Muster automatisieren.

`Python` · `Google Sheets API` · `AppleScript` · `launchd`
