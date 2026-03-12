"""Setup Script: Create Google Sheets for audit and error logging.

Prerequisites:
    1. Create a Google Cloud project
    2. Enable Google Sheets API
    3. Create a service account and download JSON key
    4. Set GOOGLE_SERVICE_ACCOUNT_JSON path in .env

    python setup/setup_google_sheets.py
"""

import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")


def create_sheets():
    if not SERVICE_ACCOUNT_JSON or not os.path.exists(SERVICE_ACCOUNT_JSON):
        print("ERROR: GOOGLE_SERVICE_ACCOUNT_JSON not set or file not found.")
        print("\nTo set up Google Sheets logging:")
        print("  1. Go to console.cloud.google.com")
        print("  2. Create a project (or use existing)")
        print("  3. Enable 'Google Sheets API'")
        print("  4. Go to IAM → Service Accounts → Create")
        print("  5. Download JSON key file")
        print("  6. Set GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/key.json in .env")
        print("\nAlternatively, skip Google Sheets — logs go to logs/ directory.\n")
        return

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        print("ERROR: google-api-python-client and google-auth not installed.")
        print("  pip install google-api-python-client google-auth")
        return

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_JSON,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )

    sheets = build("sheets", "v4", credentials=creds)
    drive = build("drive", "v3", credentials=creds)

    # Read service account email for sharing info
    with open(SERVICE_ACCOUNT_JSON) as f:
        sa_info = json.load(f)
    sa_email = sa_info.get("client_email", "unknown")

    # Create Audit Log sheet
    audit_sheet = sheets.spreadsheets().create(body={
        "properties": {"title": "RPM Video Pipeline — Audit Log"},
        "sheets": [{"properties": {"title": "Sheet1"}}],
    }).execute()
    audit_id = audit_sheet["spreadsheetId"]

    # Add headers
    sheets.spreadsheets().values().update(
        spreadsheetId=audit_id,
        range="Sheet1!A1:F1",
        valueInputOption="RAW",
        body={"values": [["Timestamp", "Property", "Phase", "Status", "Details", "Extra"]]},
    ).execute()

    # Create Error Log sheet
    error_sheet = sheets.spreadsheets().create(body={
        "properties": {"title": "RPM Video Pipeline — Error Log"},
        "sheets": [{"properties": {"title": "Sheet1"}}],
    }).execute()
    error_id = error_sheet["spreadsheetId"]

    sheets.spreadsheets().values().update(
        spreadsheetId=error_id,
        range="Sheet1!A1:F1",
        valueInputOption="RAW",
        body={"values": [["Timestamp", "Property", "Phase", "Error Type", "Message", "Extra"]]},
    ).execute()

    print("Google Sheets created!\n")
    print(f"  Audit Log ID: {audit_id}")
    print(f"  Error Log ID: {error_id}")
    print(f"\nAdd these to your .env:")
    print(f"  GOOGLE_SHEETS_AUDIT_ID={audit_id}")
    print(f"  GOOGLE_SHEETS_ERROR_ID={error_id}")
    print(f"\nSheets are owned by service account ({sa_email}).")
    print(f"Share them with your personal Google account to view in browser:")
    print(f"  https://docs.google.com/spreadsheets/d/{audit_id}")
    print(f"  https://docs.google.com/spreadsheets/d/{error_id}")


if __name__ == "__main__":
    create_sheets()
