import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple
from .version_utils import (
    detect_version_type,
    parse_semver,
    get_latest_version,
    get_display_version,
    is_on_latest
)


# Component column mappings
GREENGRASS_COMPONENTS = {
    'BLE': 'ble_version',
    'Device Manager': 'device_manager_component_version',
    'Power': 'power_component_version',
    'Raw File Upload': 'raw_file_upload_version',
    'Retriever': 'retriever_version',
}

DOCK_IMAGE_COMPONENTS = {
    'PMU': 'pmu_version',
    'APU': 'device_version',
}


def calculate_active_docks(df: pd.DataFrame, days: int = 14) -> Tuple[pd.DataFrame, int]:
    """
    Filter docks that have been seen within the specified number of days.

    Args:
        df: DataFrame with dock data
        days: Number of days to look back (default 14)

    Returns:
        Tuple of (filtered DataFrame, count of active docks)
    """
    if 'last_seen' not in df.columns:
        return df, len(df)

    # Use timezone-aware cutoff to handle UTC timestamps
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Handle both timezone-aware and naive datetimes
    try:
        active_df = df[df['last_seen'] >= cutoff]
    except TypeError:
        # If comparison fails, try converting to timezone-naive
        cutoff_naive = datetime.now() - timedelta(days=days)
        active_df = df[df['last_seen'] >= cutoff_naive]

    return active_df, len(active_df)


def calculate_component_compliance(df: pd.DataFrame, component_name: str, column: str, full_df: pd.DataFrame = None) -> Dict:
    """
    Calculate compliance statistics for a single component.

    Args:
        df: DataFrame with dock data
        component_name: Display name of the component
        column: Column name in the DataFrame

    Returns:
        Dict with compliance stats
    """
    if column not in df.columns:
        return {
            'name': component_name,
            'latest_production': 'N/A',
            'latest_beta': None,
            'production_count': 0,
            'production_percentage': 0,
            'beta_count': 0,
            'beta_percentage': 0,
            'outdated_count': 0,
            'outdated_percentage': 0,
            'total': len(df),
        }

    total = len(df)
    if total == 0:
        return {
            'name': component_name,
            'latest_production': 'N/A',
            'latest_beta': None,
            'production_count': 0,
            'production_percentage': 0,
            'beta_count': 0,
            'beta_percentage': 0,
            'outdated_count': 0,
            'outdated_percentage': 0,
            'total': 0,
        }

    # Use full (unfiltered) dataset to determine latest versions so that
    # region filtering doesn't change what counts as "latest"
    version_source = full_df if full_df is not None else df
    all_versions = version_source[column].dropna().tolist() if column in version_source.columns else []
    all_versions = [v for v in all_versions if isinstance(v, str) and v.strip() != '']

    # Get latest versions from the full dataset
    latest_production = get_latest_version(all_versions, "production")
    latest_beta = get_latest_version(all_versions, "beta")

    latest_prod_semver = parse_semver(latest_production) if latest_production else None
    latest_beta_semver = parse_semver(latest_beta) if latest_beta else None

    production_count = 0
    beta_count = 0
    outdated_count = 0
    unknown_count = 0

    for _, row in df.iterrows():
        version = row.get(column, '')
        if not version or pd.isna(version) or str(version).strip() == '':
            # Count missing versions as outdated (needs attention)
            outdated_count += 1
            unknown_count += 1
            continue

        v_type = detect_version_type(version)
        v_semver = parse_semver(version)

        if not v_semver:
            # Count unparseable versions as outdated
            outdated_count += 1
            unknown_count += 1
            continue

        # First check if this is a beta version by type
        if v_type == "beta":
            beta_count += 1
        # Check if on latest production
        elif latest_prod_semver and v_semver >= latest_prod_semver:
            production_count += 1
        else:
            outdated_count += 1

    # Calculate percentages - ensure non-zero counts never round to 0%,
    # and incomplete counts never round to 100%
    import math
    production_percentage = round((production_count / total) * 100) if total > 0 else 0
    beta_percentage = round((beta_count / total) * 100) if total > 0 else 0
    outdated_percentage = round((outdated_count / total) * 100) if total > 0 else 0

    # If there are outdated docks, show at least 1% (don't hide them by rounding to 0)
    if outdated_count > 0 and outdated_percentage == 0:
        outdated_percentage = 1
    # If there are outdated docks, production can't be 100%
    if outdated_count > 0 and production_percentage == 100:
        production_percentage = 99
    # Same for beta
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


def calculate_all_component_compliance(df: pd.DataFrame, components: Dict[str, str], full_df: pd.DataFrame = None) -> List[Dict]:
    """
    Calculate compliance for all components in a category.

    Args:
        df: DataFrame with dock data (possibly region-filtered)
        components: Dict mapping display names to column names
        full_df: Optional unfiltered DataFrame for determining latest versions globally

    Returns:
        List of compliance dicts for each component
    """
    results = []
    for name, column in components.items():
        stats = calculate_component_compliance(df, name, column, full_df=full_df)
        results.append(stats)
    return results


def calculate_fleet_compliance(df: pd.DataFrame, full_df: pd.DataFrame = None) -> Tuple[int, float]:
    """
    Calculate overall fleet compliance (% of docks with ALL components on latest).

    Args:
        df: DataFrame with dock data (possibly region-filtered)
        full_df: Optional unfiltered DataFrame for determining latest versions globally

    Returns:
        Tuple of (compliant_count, compliance_percentage)
    """
    if len(df) == 0:
        return 0, 0.0

    all_components = {**GREENGRASS_COMPONENTS, **DOCK_IMAGE_COMPONENTS}
    version_source = full_df if full_df is not None else df

    # Get latest versions for each component from the full dataset
    latest_versions = {}
    for name, column in all_components.items():
        if column in version_source.columns:
            versions = version_source[column].dropna().tolist()
            versions = [v for v in versions if isinstance(v, str) and v.strip() != '']
            latest_prod = get_latest_version(versions, "production")
            latest_beta = get_latest_version(versions, "beta")
            latest_versions[column] = {
                'production': latest_prod,
                'beta': latest_beta
            }

    compliant_count = 0

    for _, row in df.iterrows():
        is_compliant = True

        for name, column in all_components.items():
            if column not in df.columns:
                continue

            version = row.get(column, '')
            if not version or pd.isna(version) or version.strip() == '':
                # Skip missing versions (don't count as non-compliant)
                continue

            latest = latest_versions.get(column, {})
            if not is_on_latest(version, latest.get('production'), latest.get('beta')):
                is_compliant = False
                break

        if is_compliant:
            compliant_count += 1

    compliance_percentage = round((compliant_count / len(df)) * 100) if len(df) > 0 else 0

    return compliant_count, compliance_percentage


def get_docks_needing_update(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get docks that have at least one component needing an update.

    Args:
        df: DataFrame with dock data

    Returns:
        Filtered DataFrame with docks needing updates
    """
    # Use the components_needs_update column if available
    if 'components_needs_update' in df.columns:
        needs_update = df[
            (df['components_needs_update'].notna()) &
            (df['components_needs_update'].str.strip() != '')
        ]
        return needs_update

    # Fallback: calculate manually
    return df[df['components_up_to_date'] == False] if 'components_up_to_date' in df.columns else df
