import re
import pandas as pd
from typing import Optional, Tuple, List


def detect_version_type(version_string: str) -> str:
    """
    Determine if version is production, beta, or unknown.

    Args:
        version_string: Version string like "1.0.4+9de1e872" or "3.7.0-production.20251201.051918.3ac2d6e"

    Returns:
        "production", "beta", or "unknown"
    """
    if not version_string or pd.isna(version_string) or version_string.strip() == '':
        return "unknown"

    version_lower = version_string.lower()

    if "-beta" in version_lower:
        return "beta"
    if "-production" in version_lower:
        return "production"
    if "-alpha" in version_lower:
        return "alpha"

    # Short versions like "1.0.4+hash" are considered production
    if re.match(r'^\d+\.\d+\.\d+', version_string):
        return "production"

    return "unknown"


def parse_semver(version_string: str) -> Optional[Tuple[int, int, int]]:
    """
    Extract semantic version (major, minor, patch) from version string.

    Args:
        version_string: Version string like "1.0.4+9de1e872" or "3.7.0-production.20251201"

    Returns:
        Tuple of (major, minor, patch) or None if parsing fails
    """
    if not version_string or pd.isna(version_string):
        return None

    # Match X.Y.Z at the beginning
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)', version_string)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))

    return None


def get_display_version(version_string: str) -> str:
    """
    Get a clean display version (X.Y.Z) from full version string.

    Args:
        version_string: Full version string

    Returns:
        Clean version like "1.0.4" or original string if parsing fails
    """
    semver = parse_semver(version_string)
    if semver:
        return f"{semver[0]}.{semver[1]}.{semver[2]}"
    return version_string if version_string else "N/A"


def get_latest_version(versions: List[str], version_type: str = "production") -> Optional[str]:
    """
    Find the latest version of specified type from a list of versions.

    Args:
        versions: List of version strings
        version_type: "production" or "beta"

    Returns:
        The latest version string or None
    """
    # Filter by version type
    filtered = [v for v in versions if v and detect_version_type(v) == version_type]

    if not filtered:
        return None

    # Sort by semver (descending)
    def sort_key(v):
        semver = parse_semver(v)
        return semver if semver else (0, 0, 0)

    sorted_versions = sorted(filtered, key=sort_key, reverse=True)
    return sorted_versions[0] if sorted_versions else None


def get_latest_version_by_adoption(versions: List[str], version_type: str = "production") -> Optional[str]:
    """
    Find the latest version by adoption count (most deployed) rather than semver.

    This is useful for device firmware where internal/test builds may have
    higher semver numbers but very low deployment counts. The actual production
    release is the one deployed to the most devices.

    Args:
        versions: List of version strings (one per device, so duplicates represent adoption)
        version_type: "production" or "beta"

    Returns:
        The most widely deployed version string of the given type, or None
    """
    from collections import Counter

    filtered = [v for v in versions if v and detect_version_type(v) == version_type]
    if not filtered:
        return None

    counts = Counter(filtered)
    # Return the version with the highest count
    most_common = counts.most_common(1)[0][0]
    return most_common


def is_on_latest(current_version: str, latest_production: str, latest_beta: str = None) -> bool:
    """
    Check if current version is on latest (production or beta).

    Args:
        current_version: The version to check
        latest_production: The latest production version
        latest_beta: The latest beta version (optional)

    Returns:
        True if on latest production or beta
    """
    if not current_version or pd.isna(current_version) or current_version.strip() == '':
        return False

    current_semver = parse_semver(current_version)
    if not current_semver:
        return False

    # Check against latest production
    if latest_production:
        prod_semver = parse_semver(latest_production)
        if prod_semver and current_semver >= prod_semver:
            return True

    # Check against latest beta
    if latest_beta:
        beta_semver = parse_semver(latest_beta)
        if beta_semver and current_semver >= beta_semver:
            return True

    return False


def get_version_stats(df: pd.DataFrame, column: str) -> dict:
    """
    Get version statistics for a component column.

    Args:
        df: DataFrame with dock data
        column: Column name for the component version

    Returns:
        Dict with latest_production, latest_beta, version_counts, etc.
    """
    if column not in df.columns:
        return {
            'latest_production': None,
            'latest_beta': None,
            'version_counts': {},
            'total': 0
        }

    versions = df[column].dropna().tolist()
    versions = [v for v in versions if v.strip() != '']

    latest_production = get_latest_version(versions, "production")
    latest_beta = get_latest_version(versions, "beta")

    # Count versions
    version_counts = {}
    for v in versions:
        display_v = get_display_version(v)
        v_type = detect_version_type(v)
        key = f"{display_v} ({v_type})"
        version_counts[key] = version_counts.get(key, 0) + 1

    return {
        'latest_production': latest_production,
        'latest_beta': latest_beta,
        'version_counts': version_counts,
        'total': len(df)
    }
