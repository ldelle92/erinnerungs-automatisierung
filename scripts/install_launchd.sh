#!/usr/bin/env bash
# Richtet den täglichen automatischen Lauf über launchd ein.
# Ersetzt den Platzhalter im plist-Template durch den tatsächlichen
# Projektpfad (funktioniert also unabhängig davon, wo das Projekt auf
# diesem Mac liegt) und lädt den Job.
#
# Aufruf:
#   bash scripts/install_launchd.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.example.baumkontrolle"
TEMPLATE="$PROJECT_DIR/launchd/$LABEL.plist.template"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ ! -f "$TEMPLATE" ]; then
    echo "Fehler: Template nicht gefunden unter $TEMPLATE" >&2
    exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"
sed "s|__PROJECT_DIR__|$PROJECT_DIR|g" "$TEMPLATE" > "$TARGET"

# Falls der Job schon läuft, zuerst sauber entladen, bevor neu geladen wird
launchctl unload "$TARGET" >/dev/null 2>&1 || true
launchctl load "$TARGET"

echo "OK: launchd-Job eingerichtet und geladen ($TARGET)."
echo "Laeuft alle 15 Minuten an, solange der Mac wach ist - das Skript"
echo "selbst tut aber nichts mehr, sobald an diesem Tag schon ein"
echo "Durchlauf erfolgreich war (siehe logs/last_success.txt). Aendern:"
echo "StartInterval in $TEMPLATE anpassen und dieses Skript erneut ausfuehren."
echo ""
echo "Deaktivieren mit: launchctl unload \"$TARGET\""
