import pandas as pd
from typing import Dict, List, Tuple, Optional
from .metrics import calculate_component_compliance, calculate_active_docks
from .version_utils import (
    detect_version_type,
    parse_semver,
    get_latest_version,
    is_on_latest,
)

# Device component mapping (single firmware version)
DEVICE_COMPONENTS = {
    'Firmware': 'fw_version',
}


def calculate_device_fleet_compliance(df: pd.DataFrame, full_df: pd.DataFrame = None) -> Tuple[int, float]:
    """
    Calculate device fleet compliance (% of devices with firmware on latest production).

    Args:
        df: DataFrame with device data (possibly region-filtered)
        full_df: Optional unfiltered DataFrame for determining latest version globally

    Returns:
        Tuple of (compliant_count, compliance_percentage)
    """
    if len(df) == 0:
        return 0, 0.0

    column = 'fw_version'
    if column not in df.columns:
        return 0, 0.0

    version_source = full_df if full_df is not None else df
    versions = version_source[column].dropna().tolist()
    versions = [v for v in versions if isinstance(v, str) and v.strip() != '']

    latest_prod = get_latest_version(versions, "production")
    latest_beta = get_latest_version(versions, "beta")

    compliant_count = 0
    for _, row in df.iterrows():
        version = row.get(column, '')
        if not version or pd.isna(version) or str(version).strip() == '':
            continue

        if is_on_latest(version, latest_prod, latest_beta):
            compliant_count += 1

    compliance_percentage = round((compliant_count / len(df)) * 100) if len(df) > 0 else 0
    return compliant_count, compliance_percentage


def get_devices_needing_update(df: pd.DataFrame, full_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Get devices that have outdated firmware.

    Args:
        df: DataFrame with device data
        full_df: Optional unfiltered DataFrame for determining latest version globally

    Returns:
        Filtered DataFrame with devices needing updates
    """
    column = 'fw_version'
    if column not in df.columns:
        return pd.DataFrame()

    version_source = full_df if full_df is not None else df
    versions = version_source[column].dropna().tolist()
    versions = [v for v in versions if isinstance(v, str) and v.strip() != '']

    latest_prod = get_latest_version(versions, "production")
    latest_prod_semver = parse_semver(latest_prod) if latest_prod else None

    outdated_rows = []
    for idx, row in df.iterrows():
        version = row.get(column, '')
        if not version or pd.isna(version) or str(version).strip() == '':
            outdated_rows.append(idx)
            continue

        v_type = detect_version_type(str(version))
        if v_type in ("beta", "alpha"):
            continue

        v_semver = parse_semver(version)
        if not v_semver:
            outdated_rows.append(idx)
            continue

        if latest_prod_semver and v_semver < latest_prod_semver:
            outdated_rows.append(idx)

    return df.loc[outdated_rows] if outdated_rows else pd.DataFrame()
