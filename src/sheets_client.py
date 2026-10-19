"""Dünner Wrapper um die Google Sheets API (via gspread)."""

from __future__ import annotations

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class SheetsClient:
    def __init__(self, service_account_json: str, spreadsheet_id: str, worksheet_name: str):
        creds = Credentials.from_service_account_file(service_account_json, scopes=SCOPES)
        self._gc = gspread.authorize(creds)
        self._sheet = self._gc.open_by_key(spreadsheet_id)
        self._worksheet = self._sheet.worksheet(worksheet_name)

    def get_all_rows(self, data_start_row: int) -> list[list[str]]:
        """Liefert alle Datenzeilen (ohne Kopfzeilen) als Liste von Zellwert-Listen."""
        all_values = self._worksheet.get_all_values()
        return all_values[data_start_row - 1:]

    def batch_update(self, updates: list[dict]) -> None:
        """updates: Liste von {"row": int, "col": int, "value": str}."""
        if not updates:
            return
        data = [
            {
                "range": gspread.utils.rowcol_to_a1(u["row"], u["col"]),
                "values": [[u["value"]]],
            }
            for u in updates
        ]
        self._worksheet.batch_update(data)
