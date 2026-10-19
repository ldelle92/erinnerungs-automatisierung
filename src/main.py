#!/usr/bin/env python3
"""Tägliche Prüfung der Baumkontroll-Tabelle und Erstellung von
Erinnerungs-Entwürfen in Apple Mail.

Aufruf:
    python3 main.py             # normaler Lauf
    python3 main.py --dry-run   # nur anzeigen, nichts schreiben/senden
"""

from __future__ import annotations

import argparse
import time
import warnings
from datetime import date, datetime
from pathlib import Path

# Unterdrueckt harmlose Bibliotheks-Warnungen (z.B. "Python 3.8 EOL" von
# google-auth), damit die Fehler-Log-Datei sauber bleibt und ein echter
# Fehler dort sofort auffaellt statt in Rauschen unterzugehen. Muss vor
# den betroffenen Imports (dateutil/gspread/google-auth) stehen.
warnings.filterwarnings("ignore")

from dateutil.relativedelta import relativedelta

import templates
from config import load_config
from mail_applescript import create_draft, has_been_sent, has_reply_since

# Deckt kurze Internet-Aussetzer ab (z.B. Mac wacht aus dem Ruhezustand
# auf und braucht noch ein paar Minuten, bis er sich mit einem Hotspot
# verbindet): 21 Versuche im Abstand von 30 Sekunden = bis zu 10 Minuten
# Wartezeit pro Versuch, bevor dieser eine Versuch aufgibt. Der launchd-Job
# selbst laeuft alle 15 Minuten erneut an (siehe launchd/*.plist.template),
# solange der Mac wach ist - erst wenn an einem Tag ein Durchlauf wirklich
# erfolgreich war (siehe LAST_SUCCESS_MARKER), tut das Skript an diesem Tag
# nichts mehr. Damit sind auch laengere Internet-Ausfaelle abgedeckt, ohne
# bis zum naechsten Tag zu warten.
SHEETS_CONNECT_RETRIES = 21
SHEETS_CONNECT_RETRY_DELAY_SECONDS = 30
LAST_SUCCESS_MARKER = Path(__file__).resolve().parent.parent / "logs" / "last_success.txt"
from sheets_client import SheetsClient


def read_last_success_date() -> date | None:
    try:
        return datetime.strptime(LAST_SUCCESS_MARKER.read_text().strip(), "%Y-%m-%d").date()
    except (FileNotFoundError, ValueError):
        return None


def write_last_success_date(d: date) -> None:
    LAST_SUCCESS_MARKER.parent.mkdir(parents=True, exist_ok=True)
    LAST_SUCCESS_MARKER.write_text(d.isoformat())


def parse_date(value: str, fmt: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, fmt).date()
    except ValueError:
        return None


def format_date(d: date, fmt: str) -> str:
    return d.strftime(fmt)


def get(row: list[str], columns: dict, key: str) -> str:
    idx = columns[key] - 1
    return row[idx].strip() if idx < len(row) else ""


def process_row(row, sheet_row, columns, fmt, today, zweite_erinnerung_tage,
                 account_name, updates, log, dry_run, nur_faellig_ab=None):
    vorname = get(row, columns, "vorname")
    name = get(row, columns, "name")
    strasse = get(row, columns, "strasse")
    plz_ort = get(row, columns, "plz_ort")
    ort = ", ".join(p for p in [strasse, plz_ort] if p)
    email = get(row, columns, "email")
    projekt_nr = get(row, columns, "projekt_nr")
    anmerkungen = get(row, columns, "anmerkungen")
    werkvertrag = get(row, columns, "werkvertrag")
    werkvertrag_hinweis = templates.WERKVERTRAG_HINWEIS.format(werkvertrag=werkvertrag) if werkvertrag else ""

    letzte_kontrolle = parse_date(get(row, columns, "letzte_kontrolle_datum"), fmt)
    intervall_monate = get(row, columns, "kontrollintervall_monate")
    naechster_termin = parse_date(get(row, columns, "naechster_termin_datum"), fmt)
    entwurf1_erstellt = parse_date(get(row, columns, "erinnerung1_entwurf_erstellt_am"), fmt)
    erinnerung1 = parse_date(get(row, columns, "erinnerung1_gesendet_am"), fmt)
    antwort = parse_date(get(row, columns, "antwort_erhalten_am"), fmt)
    entwurf2_erstellt = parse_date(get(row, columns, "erinnerung2_entwurf_erstellt_am"), fmt)
    erinnerung2 = parse_date(get(row, columns, "erinnerung2_gesendet_am"), fmt)

    anrede_name = f"{vorname} {name}".strip()
    # Fuer Log-Zeilen mit Empfaenger-Adresse, damit sich im Zweifel genau
    # nachvollziehen laesst, an wen eine Mail ging bzw. von wem eine
    # Antwort kam - nicht nur der Name aus der Tabelle.
    wer = f"{anrede_name} <{email}>" if email else anrede_name

    # Zyklus-Reset: Es wurde eine neue Kontrolle eingetragen, nachdem zuletzt
    # eine Erinnerung angestoßen wurde -> Automatisierungs-Status leeren.
    fruehester_marker = entwurf1_erstellt or erinnerung1
    if fruehester_marker and letzte_kontrolle and letzte_kontrolle > fruehester_marker:
        log.append(f"Zeile {sheet_row} ({wer}): neue Kontrolle erkannt, Status wird zurückgesetzt.")
        if not dry_run:
            for key in ("erinnerung1_gesendet_am", "antwort_erhalten_am", "erinnerung2_gesendet_am",
                        "erinnerung1_entwurf_erstellt_am", "erinnerung2_entwurf_erstellt_am"):
                updates.append({"row": sheet_row, "col": columns[key], "value": ""})
        return

    due_date = naechster_termin
    if due_date is None and letzte_kontrolle and intervall_monate:
        try:
            due_date = letzte_kontrolle + relativedelta(months=int(intervall_monate))
        except ValueError:
            due_date = None

    if due_date is None or due_date > today:
        return  # nicht fällig oder nicht berechenbar

    if nur_faellig_ab and due_date < nur_faellig_ab:
        return  # TEMPORÄR: alter Rückstau wird vorerst ausgeblendet

    # --- Erinnerung 1: Entwurf anlegen, dann tatsächlichen Versand bestätigen ---
    if not entwurf1_erstellt and not erinnerung1:
        if not email:
            log.append(f"Zeile {sheet_row} ({anrede_name}): fällig, aber keine E-Mail-Adresse hinterlegt.")
            if not dry_run:
                create_draft(
                    subject=templates.MISSING_EMAIL_SUBJECT.format(ort=ort, name=anrede_name),
                    body=templates.MISSING_EMAIL_BODY.format(
                        name=name, vorname=vorname, ort=ort, projekt_nr=projekt_nr
                    ),
                    to_email=None,
                    account=account_name,
                )
            return

        log.append(f"Zeile {sheet_row} ({wer}): Erinnerung 1 fällig -> Entwurf wird erstellt.")
        if not dry_run:
            create_draft(
                subject=templates.ERINNERUNG_1_SUBJECT.format(ort=ort),
                body=werkvertrag_hinweis + templates.ERINNERUNG_1_BODY.format(
                    anrede_name=anrede_name,
                    letzte_kontrolle=format_date(letzte_kontrolle, fmt) if letzte_kontrolle else "unbekannt",
                    ort=ort,
                ),
                to_email=email,
                account=account_name,
            )
            updates.append({"row": sheet_row, "col": columns["erinnerung1_entwurf_erstellt_am"], "value": format_date(today, fmt)})
        return

    if entwurf1_erstellt and not erinnerung1:
        sent_date = has_been_sent(ort, entwurf1_erstellt) if (ort and not dry_run) else None
        if sent_date:
            log.append(f"Zeile {sheet_row} ({wer}): Erinnerung 1 tatsächlich versendet am {format_date(sent_date, fmt)}.")
            if not dry_run:
                updates.append({"row": sheet_row, "col": columns["erinnerung1_gesendet_am"], "value": format_date(sent_date, fmt)})
        else:
            log.append(f"Zeile {sheet_row} ({wer}): Entwurf 1 (seit {format_date(entwurf1_erstellt, fmt)}) noch nicht als gesendet erkannt.")
        return

    if antwort:
        return  # bereits beantwortet, nichts zu tun

    tage_seit = (today - erinnerung1).days
    if tage_seit < zweite_erinnerung_tage:
        return  # noch innerhalb der Wartezeit

    replied_date = None
    if email and not dry_run:
        replied_date = has_reply_since(email, erinnerung1)

    if replied_date:
        log.append(f"Zeile {sheet_row} ({wer}): Antwort erkannt (eingegangen am {format_date(replied_date, fmt)}).")
        if not dry_run:
            updates.append({"row": sheet_row, "col": columns["antwort_erhalten_am"], "value": format_date(replied_date, fmt)})
        return

    # --- Erinnerung 2: analog Entwurf anlegen, dann Versand bestätigen ---
    if not entwurf2_erstellt and not erinnerung2:
        log.append(f"Zeile {sheet_row} ({wer}): keine Antwort nach {tage_seit} Tagen -> 2. Erinnerung wird erstellt.")
        if not dry_run:
            create_draft(
                subject=templates.ERINNERUNG_2_SUBJECT.format(ort=ort),
                body=templates.INTERNAL_NOTE + werkvertrag_hinweis + templates.ERINNERUNG_2_BODY.format(anrede_name=anrede_name, ort=ort),
                to_email=email,
                account=account_name,
            )
            updates.append({"row": sheet_row, "col": columns["erinnerung2_entwurf_erstellt_am"], "value": format_date(today, fmt)})
        return

    if entwurf2_erstellt and not erinnerung2:
        sent_date = has_been_sent(ort, entwurf2_erstellt) if (ort and not dry_run) else None
        if sent_date:
            log.append(f"Zeile {sheet_row} ({wer}): Erinnerung 2 tatsächlich versendet am {format_date(sent_date, fmt)}.")
            if not dry_run:
                updates.append({"row": sheet_row, "col": columns["erinnerung2_gesendet_am"], "value": format_date(sent_date, fmt)})
        else:
            log.append(f"Zeile {sheet_row} ({wer}): Entwurf 2 (seit {format_date(entwurf2_erstellt, fmt)}) noch nicht als gesendet erkannt.")
        return

    marker = "Automatisierung: keine Antwort nach 2. Erinnerung"
    if marker not in anmerkungen:
        log.append(f"Zeile {sheet_row} ({wer}): auch nach 2. Erinnerung keine Antwort -> manuelle Prüfung nötig.")
        if not dry_run:
            neue_anmerkung = f"{anmerkungen} | {marker} (Stand {format_date(today, fmt)})".strip(" |")
            updates.append({"row": sheet_row, "col": columns["anmerkungen"], "value": neue_anmerkung})


def main():
    parser = argparse.ArgumentParser(description="Baumkontrolle-Erinnerungen prüfen")
    parser.add_argument("--dry-run", action="store_true", help="Nichts schreiben/senden, nur anzeigen was passieren würde")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent.parent / "config.yaml"))
    parser.add_argument("--only-row", type=int, default=None, help="Nur diese eine Tabellenzeile verarbeiten (zum kontrollierten Testen)")
    args = parser.parse_args()

    cfg = load_config(args.config)
    columns = cfg["columns"]
    fmt = cfg["automation"]["datumsformat"]
    zweite_erinnerung_tage = cfg["automation"]["zweite_erinnerung_nach_tagen"]
    account_name = cfg["mail"].get("von_konto") or None
    nur_faellig_ab = parse_date(cfg["automation"].get("nur_faellig_ab") or "", fmt)
    aktiv_bis = parse_date(cfg["automation"].get("aktiv_bis") or "", fmt)

    # Der launchd-Job laeuft alle 15 Minuten an (siehe launchd/*.plist.template),
    # damit auch nach laengeren Internet-Ausfaellen zuegig ein Versuch
    # nachgeholt wird. War heute aber schon ein Durchlauf erfolgreich,
    # braucht es keinen erneuten - stiller, sofortiger Abbruch (nur beim
    # normalen unbeaufsichtigten Lauf, --dry-run/--only-row immer ausfuehren).
    if not args.dry_run and args.only_row is None:
        if read_last_success_date() == date.today():
            return
        # Optional: automatischer Lauf pausiert ab einem Stichtag (siehe
        # config.yaml "aktiv_bis"), z.B. weil eine andere Person parallel
        # dieselbe Tabelle von einem anderen Mac aus testet. Manuelle
        # Laeufe sind davon nicht betroffen.
        if aktiv_bis and date.today() > aktiv_bis:
            return

    client = None
    rows = None
    last_error = None
    for attempt in range(1, SHEETS_CONNECT_RETRIES + 1):
        try:
            client = SheetsClient(
                service_account_json=cfg["google"]["service_account_json"],
                spreadsheet_id=cfg["google"]["spreadsheet_id"],
                worksheet_name=cfg["google"]["worksheet_name"],
            )
            rows = client.get_all_rows(cfg["google"]["data_start_row"])
            break
        except Exception as exc:
            last_error = exc
            if attempt < SHEETS_CONNECT_RETRIES:
                time.sleep(SHEETS_CONNECT_RETRY_DELAY_SECONDS)

    if client is None:
        print(f"--- Lauf {datetime.now().isoformat(timespec='seconds')} ---")
        print(f"FEHLER: Google Sheet nach {SHEETS_CONNECT_RETRIES} Versuchen "
              f"(je {SHEETS_CONNECT_RETRY_DELAY_SECONDS}s Abstand) nicht "
              f"erreichbar (z.B. kein Internet) - {last_error}")
        print("Nichts wurde veraendert. Faellige Zeilen bleiben faellig und werden beim naechsten erfolgreichen Lauf verarbeitet.")
        return

    today = date.today()
    updates: list[dict] = []
    log: list[str] = []

    for i, row in enumerate(rows):
        sheet_row = cfg["google"]["data_start_row"] + i
        if args.only_row is not None and sheet_row != args.only_row:
            continue
        projekt_nr = get(row, columns, "projekt_nr")
        name = get(row, columns, "name")
        if not projekt_nr and not name:
            continue  # leere Zeile

        try:
            process_row(row, sheet_row, columns, fmt, today, zweite_erinnerung_tage,
                        account_name, updates, log, dry_run=args.dry_run,
                        nur_faellig_ab=nur_faellig_ab)
        except Exception as exc:
            log.append(f"Zeile {sheet_row}: FEHLER – {exc}")

    if updates and not args.dry_run:
        client.batch_update(updates)
    elif updates and args.dry_run:
        log.append(f"[DRY-RUN] {len(updates)} Zell-Update(s) würden geschrieben, es wurde nichts gesendet.")

    # Nur der vollstaendige, unbeaufsichtigte Lauf zaehlt als "heutiger
    # Check erledigt" - ein gezielter --only-row-Test soll den naechsten
    # echten Lauf desselben Tages nicht versehentlich unterdruecken.
    if not args.dry_run and args.only_row is None:
        write_last_success_date(today)

    print(f"--- Lauf {datetime.now().isoformat(timespec='seconds')} ---")
    for line in log:
        print(line)
    if not log:
        print("Keine fälligen Zeilen.")


if __name__ == "__main__":
    main()
