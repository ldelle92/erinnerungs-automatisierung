#!/usr/bin/env bash
# Prüft, ob alle auf dem Mac benötigten Programme installiert sind, und
# installiert fehlende Teile nach. Danach ist die Python-Umgebung fertig
# eingerichtet.
#
# Aufruf:
#   bash scripts/setup_mac.sh

set -euo pipefail

echo "== Baumkontrolle-Automatisierung: Setup-Check =="

# 1. Xcode Command Line Tools (liefert u.a. das python3-Grundgerüst)
if ! xcode-select -p >/dev/null 2>&1; then
    echo "Xcode Command Line Tools fehlen -> Installationsdialog wird geöffnet."
    xcode-select --install
    echo "Bitte die Installation im geöffneten Fenster abschließen und"
    echo "dieses Skript danach erneut ausführen: bash scripts/setup_mac.sh"
    exit 1
else
    echo "OK: Xcode Command Line Tools vorhanden."
fi

# 2. Homebrew (wird genutzt, um Python nachzuinstallieren, falls nötig)
if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew fehlt -> wird installiert (fragt eventuell nach dem Mac-Login-Passwort) ..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [ -x /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -x /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
else
    echo "OK: Homebrew vorhanden."
fi

# 3. Python 3 (irgendeine Version reicht, das Skript ist kompatibel)
if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 fehlt -> wird über Homebrew installiert ..."
    brew install python@3.12
else
    echo "OK: python3 vorhanden ($(python3 --version))."
fi

# 4. Projekt-Umgebung: virtuelles Environment + Python-Abhängigkeiten
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
    echo "Lege virtuelle Python-Umgebung an ..."
    python3 -m venv .venv
else
    echo "OK: virtuelle Python-Umgebung existiert bereits."
fi

echo "Installiere/aktualisiere Python-Abhängigkeiten ..."
"./.venv/bin/pip" install --quiet --upgrade pip
"./.venv/bin/pip" install --quiet -r requirements.txt

echo ""
echo "== Setup abgeschlossen =="
echo "Nächste Schritte (siehe README.md):"
echo "  1. Service-Account-JSON unter credentials/service_account.json ablegen"
echo "  2. spreadsheet_id und worksheet_name in config.yaml eintragen"
echo "  3. Testen mit: ./.venv/bin/python3 src/main.py --dry-run"
