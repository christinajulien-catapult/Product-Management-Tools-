import pandas as pd
from typing import Dict, List, Tuple, Optional
from .metrics import calculate_active_docks
from .version_utils import (
    detect_version_type,
    parse_semver,
    get_latest_version_by_adoption,
    get_latest_version,
    get_display_version,
    is_on_latest,
)

# Device component mapping (single firmware version)
DEVICE_COMPONENTS = {
    'Firmware': 'fw_version',
}


def _get_device_latest_versions(df: pd.DataFrame):
    """Get latest production and beta versions for device firmware using adoption-based detection."""
    column = 'fw_version'
    if column not in df.columns:
        return None, None

    versions = df[column].dropna().tolist()
    versions = [v for v in versions if isinstance(v, str) and v.strip() != '']

    # Use adoption-based detection for production (most deployed = actual release)
    latest_prod = get_latest_version_by_adoption(versions, "production")
    # Use semver-based for beta (highest beta version)
    latest_beta = get_latest_version(versions, "beta")

    return latest_prod, latest_beta


def calculate_device_component_compliance(df: pd.DataFrame, component_name: str, column: str, full_df: pd.DataFrame = None) -> Dict:
    """
    Calculate compliance for a device component using adoption-based version detection.

    This overrides the standard calculate_component_compliance to use
    get_latest_version_by_adoption for production versions.
    """
    import math

    if column not in df.columns:
        return {
            'name': component_name, 'latest_production': 'N/A', 'latest_beta': None,
            'latest_production_full': None, 'latest_beta_full': None,
            'production_count': 0, 'production_percentage': 0,
            'beta_count': 0, 'beta_percentage': 0,
            'outdated_count': 0, 'outdated_percentage': 0,
            'unknown_count': 0, 'total': len(df),
        }

    total = len(df)
    if total == 0:
        return {
            'name': component_name, 'latest_production': 'N/A', 'latest_beta': None,
            'latest_production_full': None, 'latest_beta_full': None,
            'production_count': 0, 'production_percentage': 0,
            'beta_count': 0, 'beta_percentage': 0,
            'outdated_count': 0, 'outdated_percentage': 0,
            'unknown_count': 0, 'total': 0,
        }

    version_source = full_df if full_df is not None else df
    latest_production, latest_beta = _get_device_latest_versions(version_source)

    latest_prod_semver = parse_semver(latest_production) if latest_production else None
    latest_beta_semver = parse_semver(latest_beta) if latest_beta else None

    production_count = 0
    beta_count = 0
    outdated_count = 0
    unknown_count = 0

    for _, row in df.iterrows():
        version = row.get(column, '')
        if not version or pd.isna(version) or str(version).strip() == '':
            outdated_count += 1
            unknown_count += 1
            continue

        v_type = detect_version_type(version)
        v_semver = parse_semver(version)

        if not v_semver:
            outdated_count += 1
            unknown_count += 1
            continue

        if v_type in ("beta", "alpha"):
            beta_count += 1
        elif latest_prod_semver and v_semver >= latest_prod_semver:
            production_count += 1
        else:
            outdated_count += 1

    production_percentage = round((production_count / total) * 100) if total > 0 else 0
    beta_percentage = round((beta_count / total) * 100) if total > 0 else 0
    outdated_percentage = round((outdated_count / total) * 100) if total > 0 else 0

    if outdated_count > 0 and outdated_percentage == 0:
        outdated_percentage = 1
    if outdated_count > 0 and production_percentage == 100:
        production_percentage = 99
    if beta_count > 0 and beta_percentage == 0:
        beta_percentage = 1
    if beta_count > 0 and production_percentage == 100:
        production_percentage = 99

    return {
        'name': component_name,
        'latest_production': get_display_version(latest_production) if latest_production else 'N/A',
        'latest_production_full': latest_production,
        'latest_beta': get_display_version(latest_beta) if latest_beta else None,
        'latest_beta_full': latest_beta,
        'production_count': production_count,
        'production_percentage': production_percentage,
        'beta_count': beta_count,
        'beta_percentage': beta_percentage,
        'outdated_count': outdated_count,
        'outdated_percentage': outdated_percentage,
        'unknown_count': unknown_count,
        'total': total,
    }


def calculate_all_device_compliance(df: pd.DataFrame, full_df: pd.DataFrame = None) -> List[Dict]:
    """Calculate compliance for all device components."""
    results = []
    for name, column in DEVICE_COMPONENTS.items():
        stats = calculate_device_component_compliance(df, name, column, full_df=full_df)
        results.append(stats)
    return results


def calculate_device_fleet_compliance(df: pd.DataFrame, full_df: pd.DataFrame = None) -> Tuple[int, float]:
    """
    Calculate device fleet compliance (% of devices with firmware on latest production).
    Uses adoption-based version detection.
    """
    if len(df) == 0:
        return 0, 0.0

    column = 'fw_version'
    if column not in df.columns:
        return 0, 0.0

    version_source = full_df if full_df is not None else df
    latest_prod, latest_beta = _get_device_latest_versions(version_source)

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
    """Get devices that have outdated firmware using adoption-based version detection."""
    column = 'fw_version'
    if column not in df.columns:
        return pd.DataFrame()

    version_source = full_df if full_df is not None else df
    latest_prod, _ = _get_device_latest_versions(version_source)
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
