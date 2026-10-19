"""Steuerung von Apple Mail per AppleScript.

Legt Entwürfe an (die der Nutzer selbst prüft und sendet) und durchsucht
die Postfächer nach Antworten eines Absenders seit einem bestimmten Datum.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from datetime import date, datetime

# Liefert das Datum eines AppleScript-"date"-Objekts als eindeutigen
# "YYYY-MM-DD"-String zurueck (unabhaengig von Sprach-/Locale-Einstellungen
# des Mac, im Gegensatz zu z.B. "short date string").
_APPLESCRIPT_ISO_DATE = (
    '(year of {var} as string) & "-" & '
    'text -2 thru -1 of ("0" & (month of {var} as integer)) & "-" & '
    'text -2 thru -1 of ("0" & (day of {var}))'
)


def _esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _run_applescript(script: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".applescript", delete=False, encoding="utf-8") as f:
        f.write(script)
        path = f.name
    try:
        result = subprocess.run(
            ["osascript", path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"AppleScript-Fehler: {result.stderr.strip()}")
        return result.stdout.strip()
    finally:
        os.unlink(path)


def create_draft(subject: str, body: str, to_email: str | None = None, account: str | None = None) -> None:
    """Legt einen sichtbaren Entwurf in Mail.app an, sendet NICHTS automatisch."""
    props = [f'subject:"{_esc(subject)}"', f'content:"{_esc(body)}"', "visible:true"]
    if account:
        props.append(f'sender:"{_esc(account)}"')
    props_str = ", ".join(props)

    to_block = ""
    if to_email:
        to_block = f'''
        make new to recipient at end of to recipients with properties {{address:"{_esc(to_email)}"}}'''

    script = f'''
tell application "Mail"
    set newMessage to make new outgoing message with properties {{{props_str}}}
    tell newMessage{to_block}
    end tell
    save newMessage
    activate
end tell
'''
    _run_applescript(script)


def _find_message_date(mailbox_expr: str, where_clause: str, date_property: str, since: date) -> date | None:
    """Sucht in `mailbox_expr` (z.B. "inbox" oder "sent mailbox" - beides
    aggregiert automatisch ueber alle Mail.app-Konten) nach einer
    Nachricht, die `where_clause` erfuellt und deren `date_property"
    nach `since` liegt. Gibt das echte Datum der ersten gefundenen
    Nachricht zurueck, oder None.
    """
    days_ago = max((date.today() - since).days, 0)
    date_str_expr = _APPLESCRIPT_ISO_DATE.format(var="foundDate")

    script = f'''
set sinceDate to (current date) - ({days_ago} * days)
tell application "Mail"
    set targetMailbox to {mailbox_expr}
    set matchingMessages to (messages of targetMailbox whose {where_clause} and {date_property} > sinceDate)
    if (count of matchingMessages) = 0 then return "KEIN_TREFFER"
    set foundDate to {date_property} of item 1 of matchingMessages
    return {date_str_expr}
end tell
'''
    output = _run_applescript(script).strip()
    if not output or output == "KEIN_TREFFER":
        return None
    return datetime.strptime(output, "%Y-%m-%d").date()


def has_reply_since(from_email: str, since: date) -> date | None:
    """Prüft, ob seit `since` eine Nachricht von `from_email` eingegangen ist.

    Durchsucht das aggregierte Posteingangs-Postfach ueber alle in
    Mail.app eingerichteten Konten hinweg (Mail.app-Postfachnamen wie
    "INBOX" sind je nach Konto/Anbieter unterschiedlich benannt - die
    aggregierte Referenz umgeht das). Gibt das tatsächliche Empfangsdatum
    der ersten gefundenen Nachricht zurück, oder None.
    """
    return _find_message_date(
        mailbox_expr="inbox",
        where_clause=f'sender contains "{_esc(from_email)}"',
        date_property="date received",
        since=since,
    )


def has_been_sent(subject_contains: str, since: date) -> date | None:
    """Prüft, ob seit `since` tatsächlich eine Nachricht mit passendem
    Betreff im Gesendet-Postfach liegt (bestätigt, dass ein zuvor
    angelegter Entwurf wirklich abgeschickt wurde statt nur erstellt).

    Durchsucht aggregiert alle Konten. Gibt das tatsächliche Sendedatum
    der ersten gefundenen Nachricht zurück, oder None.
    """
    return _find_message_date(
        mailbox_expr="sent mailbox",
        where_clause=f'subject contains "{_esc(subject_contains)}"',
        date_property="date sent",
        since=since,
    )
