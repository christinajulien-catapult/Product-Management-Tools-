"""Google Sheets integration for Fleet Overview Dashboard."""

import os
import pandas as pd
import streamlit as st

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


def get_credentials_path() -> str:
    """Get the path to the credentials file from environment or default."""
    return os.environ.get('GOOGLE_CREDENTIALS_PATH', 'credentials.json')


def get_gspread_client(credentials_path: str = None):
    """
    Initialize authenticated gspread client using service account.
    Supports both Streamlit secrets (for cloud) and local credentials file.
    """
    import gspread
    from google.oauth2.service_account import Credentials

    # Try Streamlit secrets first (for cloud deployment)
    try:
        if 'gcp_service_account' in st.secrets:
            creds_dict = dict(st.secrets['gcp_service_account'])
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            return gspread.authorize(creds)
    except Exception:
        pass

    # Fall back to credentials file (for local development)
    if credentials_path is None:
        credentials_path = get_credentials_path()

    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            f"Credentials file not found at '{credentials_path}'. "
            "Please set up a Google Cloud service account and download the credentials JSON file. "
            "See: https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account"
        )

    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return gspread.authorize(creds)


def load_from_google_sheets(sheet_url_or_id: str, credentials_path: str = None) -> pd.DataFrame:
    """
    Load data from a Google Sheet and return as DataFrame.
    """
    import gspread

    client = get_gspread_client(credentials_path)

    try:
        # Open by URL or ID
        if sheet_url_or_id.startswith('http'):
            sheet = client.open_by_url(sheet_url_or_id)
        else:
            sheet = client.open_by_key(sheet_url_or_id)
    except gspread.exceptions.SpreadsheetNotFound:
        raise Exception(
            "Google Sheet not found. Please check that:\n"
            "1. The URL/ID is correct\n"
            "2. The sheet is shared with the service account email"
        )
    except gspread.exceptions.APIError as e:
        if 'PERMISSION_DENIED' in str(e):
            raise Exception(
                "Permission denied. Please share the Google Sheet with "
                "the service account email"
            )
        raise

    # Get first worksheet
    worksheet = sheet.sheet1

    # Get all data as DataFrame
    data = worksheet.get_all_records()

    if not data:
        raise Exception("The Google Sheet appears to be empty or has no header row.")

    return pd.DataFrame(data)


def check_credentials_exist(credentials_path: str = None) -> bool:
    """Check if credentials are available (either secrets or file)."""
    # Check Streamlit secrets first
    try:
        if 'gcp_service_account' in st.secrets:
            return True
    except Exception:
        pass

    # Check local file
    if credentials_path is None:
        credentials_path = get_credentials_path()
    return os.path.exists(credentials_path)


def get_service_account_email(credentials_path: str = None) -> str:
    """Extract the service account email from credentials."""
    import json

    # Try Streamlit secrets first
    try:
        if 'gcp_service_account' in st.secrets:
            return st.secrets['gcp_service_account'].get('client_email')
    except Exception:
        pass

    # Fall back to file
    if credentials_path is None:
        credentials_path = get_credentials_path()

    if not os.path.exists(credentials_path):
        return None

    try:
        with open(credentials_path, 'r') as f:
            creds_data = json.load(f)
            return creds_data.get('client_email')
    except Exception:
        return None
