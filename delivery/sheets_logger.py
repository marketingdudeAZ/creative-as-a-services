"""Google Sheets Logger — audit log and error log."""

import json
import logging
from datetime import datetime

from config import GOOGLE_SHEETS_AUDIT_ID, GOOGLE_SHEETS_ERROR_ID, GOOGLE_SERVICE_ACCOUNT_JSON

logger = logging.getLogger(__name__)

_sheets_service = None


def _get_sheets_service():
    """Lazy-init Google Sheets API service."""
    global _sheets_service
    if _sheets_service:
        return _sheets_service

    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        logger.warning("Google Sheets service account not configured — logging to stdout only")
        return None

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_JSON,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        _sheets_service = build("sheets", "v4", credentials=creds)
        return _sheets_service
    except Exception as e:
        logger.error("Failed to init Google Sheets service: %s", e)
        return None


def _append_row(sheet_id: str, values: list) -> bool:
    """Append a row to a Google Sheet."""
    service = _get_sheets_service()
    if not service:
        return False

    try:
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="Sheet1!A:Z",
            valueInputOption="RAW",
            body={"values": [values]},
        ).execute()
        return True
    except Exception as e:
        logger.error("Failed to append to sheet %s: %s", sheet_id, e)
        return False


def log_audit(
    property_name: str,
    phase: str,
    status: str,
    details: str = "",
    **extra,
) -> None:
    """Log an audit entry (successful operations)."""
    timestamp = datetime.now().isoformat()
    row = [timestamp, property_name, phase, status, details, json.dumps(extra) if extra else ""]

    logger.info("AUDIT | %s | %s | %s | %s", property_name, phase, status, details)

    if GOOGLE_SHEETS_AUDIT_ID:
        _append_row(GOOGLE_SHEETS_AUDIT_ID, row)


def log_error(
    property_name: str,
    phase: str,
    error_type: str,
    error_message: str,
    **extra,
) -> None:
    """Log an error entry."""
    timestamp = datetime.now().isoformat()
    row = [timestamp, property_name, phase, error_type, error_message, json.dumps(extra) if extra else ""]

    logger.error("ERROR | %s | %s | %s | %s", property_name, phase, error_type, error_message)

    if GOOGLE_SHEETS_ERROR_ID:
        _append_row(GOOGLE_SHEETS_ERROR_ID, row)


def log_video_credit(
    property_name: str,
    script_id: str,
    platform: str,
    video_length: int,
) -> None:
    """Track video generation credits usage."""
    log_audit(
        property_name,
        "video_generation",
        "credit_used",
        f"{script_id} | {platform} | {video_length}s",
    )


def write_run_summary(summary: dict) -> None:
    """Write end-of-run summary to logs/run_summary.json and sheets."""
    import os

    os.makedirs("logs", exist_ok=True)
    with open("logs/run_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    logger.info("Run summary written to logs/run_summary.json")

    if GOOGLE_SHEETS_AUDIT_ID:
        _append_row(GOOGLE_SHEETS_AUDIT_ID, [
            datetime.now().isoformat(),
            "PIPELINE",
            "run_summary",
            "COMPLETE",
            json.dumps(summary, default=str),
        ])
