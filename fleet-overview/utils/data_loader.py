import pandas as pd
from datetime import datetime


def parse_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse and normalize a DataFrame with proper dtypes.
    Used by both CSV and Google Sheets loaders.
    """
    # Ensure string columns have proper dtype
    string_columns = [
        'region', 'customer_id', 'customer_name', 'serial', 'model',
        'pmu_version', 'device_version', 'retriever_version',
        'power_component_version', 'ble_version', 'raw_file_upload_version',
        'device_manager_component_version', 'dock_image_version', 'dock_pmu_version',
        'components_needs_update', 'needs_update'
    ]
    for col in string_columns:
        if col in df.columns:
            df[col] = df[col].astype(str).replace('nan', '').replace('None', '')

    # Parse last_seen as datetime
    if 'last_seen' in df.columns:
        df['last_seen'] = pd.to_datetime(df['last_seen'], errors='coerce')

    # Convert boolean columns
    bool_columns = ['images_up_to_date', 'components_up_to_date']
    for col in bool_columns:
        if col in df.columns:
            df[col] = df[col].map({
                'TRUE': True, 'FALSE': False,
                'True': True, 'False': False,
                True: True, False: False,
                'true': True, 'false': False
            })

    # Fill NaN string columns with empty string
    version_columns = [
        'pmu_version', 'device_version', 'retriever_version',
        'power_component_version', 'ble_version', 'raw_file_upload_version',
        'device_manager_component_version', 'dock_image_version', 'dock_pmu_version',
        'components_needs_update', 'needs_update'
    ]
    for col in version_columns:
        if col in df.columns:
            df[col] = df[col].fillna('')

    return df


def load_csv_data(file_path_or_buffer):
    """Load and parse CSV data with proper dtypes."""
    df = pd.read_csv(
        file_path_or_buffer,
        sep='\t' if isinstance(file_path_or_buffer, str) and file_path_or_buffer.endswith('.tsv') else None,
        dtype={
            'region': str,
            'customer_id': str,
            'customer_name': str,
            'serial': str,
            'model': str,
            'pmu_version': str,
            'device_version': str,
            'retriever_version': str,
            'power_component_version': str,
            'ble_version': str,
            'raw_file_upload_version': str,
            'device_manager_component_version': str,
            'dock_image_version': str,
            'dock_pmu_version': str,
            'components_needs_update': str,
            'needs_update': str,
        }
    )

    # Parse last_seen as datetime
    if 'last_seen' in df.columns:
        df['last_seen'] = pd.to_datetime(df['last_seen'], errors='coerce')

    # Convert boolean columns
    bool_columns = ['images_up_to_date', 'components_up_to_date']
    for col in bool_columns:
        if col in df.columns:
            df[col] = df[col].map({'TRUE': True, 'FALSE': False, True: True, False: False})

    # Fill NaN string columns with empty string
    string_columns = [
        'pmu_version', 'device_version', 'retriever_version',
        'power_component_version', 'ble_version', 'raw_file_upload_version',
        'device_manager_component_version', 'dock_image_version', 'dock_pmu_version',
        'components_needs_update', 'needs_update'
    ]
    for col in string_columns:
        if col in df.columns:
            df[col] = df[col].fillna('')

    return df


def filter_by_region(df, region):
    """Filter dataframe by region. Returns all if region is 'All'."""
    if region == 'All' or not region:
        return df
    return df[df['region'] == region]


def load_from_google_sheets(sheet_url_or_id: str, credentials_path: str = None) -> pd.DataFrame:
    """
    Load data from Google Sheets and return as normalized DataFrame.

    Args:
        sheet_url_or_id: Full Google Sheets URL or sheet ID
        credentials_path: Path to service account credentials JSON

    Returns:
        Normalized pandas DataFrame
    """
    from utils.google_sheets import load_from_google_sheets as gs_load

    # Get raw data from Google Sheets
    df = gs_load(sheet_url_or_id, credentials_path)

    # Parse and normalize the DataFrame
    return parse_dataframe(df)


def load_data(source_type: str, source, credentials_path: str = None) -> pd.DataFrame:
    """
    Unified data loading function that routes to the appropriate loader.

    Args:
        source_type: Either 'csv' or 'google_sheets'
        source: File path/buffer for CSV, or URL/ID for Google Sheets
        credentials_path: Path to Google credentials (for google_sheets only)

    Returns:
        Normalized pandas DataFrame
    """
    if source_type == 'google_sheets':
        return load_from_google_sheets(source, credentials_path)
    else:
        return load_csv_data(source)
