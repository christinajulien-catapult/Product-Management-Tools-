import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict, Optional

from utils.version_utils import parse_semver, get_latest_version, get_latest_version_by_adoption, detect_version_type
from utils.metrics import GREENGRASS_COMPONENTS, DOCK_IMAGE_COMPONENTS, VERSION_OVERRIDES
from utils.device_metrics import DEVICE_COMPONENTS


def _get_component_map(table_id: str):
    """Get the component map for a given table_id."""
    if table_id == "greengrass":
        return GREENGRASS_COMPONENTS
    elif table_id == "devices":
        return DEVICE_COMPONENTS
    else:
        return DOCK_IMAGE_COMPONENTS


def get_compliance_color(percentage: float) -> str:
    """Get color based on compliance percentage."""
    if percentage >= 75:
        return "#22c55e"  # Green
    elif percentage >= 50:
        return "#eab308"  # Yellow
    else:
        return "#ef4444"  # Red


def create_distribution_bar(production_pct: float, beta_pct: float) -> go.Figure:
    """Create a clean stacked horizontal bar for fleet distribution."""
    outdated_pct = max(0, 100 - production_pct - beta_pct)

    # Minimum percentage to show text (below this, text won't fit)
    min_pct_for_text = 15

    fig = go.Figure()

    # Production/Latest (green)
    if production_pct > 0:
        fig.add_trace(go.Bar(
            y=[''],
            x=[production_pct],
            orientation='h',
            marker=dict(
                color='#22c55e',
                line=dict(width=0)
            ),
            name='Latest',
            text=f'{production_pct}%' if production_pct >= min_pct_for_text else '',
            textposition='inside',
            insidetextanchor='middle',
            textfont=dict(color='white', size=12, family='Montserrat, sans-serif', weight=600),
            hovertemplate='Latest: %{x}%<extra></extra>'
        ))

    # Beta (blue)
    if beta_pct > 0:
        fig.add_trace(go.Bar(
            y=[''],
            x=[beta_pct],
            orientation='h',
            marker=dict(
                color='#3b82f6',
                line=dict(width=0)
            ),
            name='Beta',
            text=f'{beta_pct}%' if beta_pct >= min_pct_for_text else '',
            textposition='inside',
            insidetextanchor='middle',
            textfont=dict(color='white', size=12, family='Montserrat, sans-serif', weight=600),
            hovertemplate='Beta: %{x}%<extra></extra>'
        ))

    # Outdated (red)
    if outdated_pct > 0:
        fig.add_trace(go.Bar(
            y=[''],
            x=[outdated_pct],
            orientation='h',
            marker=dict(
                color='#ef4444',
                line=dict(width=0)
            ),
            name='Outdated',
            text=f'{outdated_pct}%' if outdated_pct >= min_pct_for_text else '',
            textposition='inside',
            insidetextanchor='middle',
            textfont=dict(color='white', size=12, family='Montserrat, sans-serif', weight=600),
            hovertemplate='Outdated: %{x}%<extra></extra>'
        ))

    fig.update_layout(
        barmode='stack',
        height=40,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        xaxis=dict(
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            range=[0, 100]
        ),
        yaxis=dict(
            showticklabels=False,
            showgrid=False,
            zeroline=False
        ),
        bargap=0,
        bargroupgap=0
    )

    # Round the bar corners
    fig.update_traces(marker_cornerradius=5)

    return fig


def get_outdated_docks_for_component(df: pd.DataFrame, component_name: str, table_id: str) -> pd.DataFrame:
    """Get docks that have an outdated version of a specific component."""
    column_map = _get_component_map(table_id)
    column = column_map.get(component_name)
    if not column or column not in df.columns:
        return pd.DataFrame()

    override = VERSION_OVERRIDES.get(column)

    if override:
        latest_prod_semver = override['latest_production']
        latest_beta_semver = override.get('latest_beta')
    else:
        versions = df[column].dropna().tolist()
        versions = [v for v in versions if isinstance(v, str) and v.strip() != '']

        # Use adoption-based detection for devices, semver for docks
        if table_id == "devices":
            latest_production = get_latest_version_by_adoption(versions, "production")
        else:
            latest_production = get_latest_version(versions, "production")
        latest_beta = get_latest_version(versions, "beta")

        latest_prod_semver = parse_semver(latest_production) if latest_production else None
        latest_beta_semver = parse_semver(latest_beta) if latest_beta else None

    outdated_rows = []
    for idx, row in df.iterrows():
        version = row.get(column, '')

        # Missing/empty versions count as outdated
        if not version or pd.isna(version) or str(version).strip() == '':
            outdated_rows.append(idx)
            continue

        v_semver = parse_semver(version)
        if not v_semver:
            outdated_rows.append(idx)
            continue

        if override:
            # With overrides: only exact beta semver match is beta, production must be >= prod semver
            if latest_beta_semver and v_semver == latest_beta_semver:
                continue  # This is beta, not outdated
            elif latest_prod_semver and v_semver >= latest_prod_semver:
                continue  # On latest production, not outdated
            else:
                outdated_rows.append(idx)
        else:
            v_type = detect_version_type(str(version))

            # For devices: beta/alpha at or below latest production are outdated
            if v_type in ("beta", "alpha"):
                if table_id == "devices":
                    if not latest_prod_semver or v_semver <= latest_prod_semver:
                        outdated_rows.append(idx)
                continue

            is_outdated = True
            if latest_prod_semver and v_semver >= latest_prod_semver:
                is_outdated = False
            if is_outdated:
                outdated_rows.append(idx)

    return df.loc[outdated_rows] if outdated_rows else pd.DataFrame()


def get_beta_docks_for_component(df: pd.DataFrame, component_name: str, table_id: str) -> pd.DataFrame:
    """Get docks that are on a beta version of a specific component."""
    column_map = _get_component_map(table_id)
    column = column_map.get(component_name)
    if not column or column not in df.columns:
        return pd.DataFrame()

    override = VERSION_OVERRIDES.get(column)

    if override:
        # With overrides: only exact beta semver match counts as beta
        latest_beta_semver = override.get('latest_beta')
        if not latest_beta_semver:
            return pd.DataFrame()

        beta_rows = []
        for idx, row in df.iterrows():
            version = row.get(column, '')
            if not version or pd.isna(version) or str(version).strip() == '':
                continue
            v_semver = parse_semver(version)
            if v_semver and v_semver == latest_beta_semver:
                beta_rows.append(idx)
        return df.loc[beta_rows] if beta_rows else pd.DataFrame()

    # For devices, determine latest prod to filter out old betas
    latest_prod_semver = None
    if table_id == "devices":
        versions = df[column].dropna().tolist()
        versions = [v for v in versions if isinstance(v, str) and v.strip() != '']
        latest_production = get_latest_version_by_adoption(versions, "production")
        latest_prod_semver = parse_semver(latest_production) if latest_production else None

    beta_rows = []
    for idx, row in df.iterrows():
        version = row.get(column, '')
        if not version or pd.isna(version) or str(version).strip() == '':
            continue
        if detect_version_type(str(version)) in ("beta", "alpha"):
            # For devices: only betas strictly above latest production count as beta
            if table_id == "devices" and latest_prod_semver:
                v_semver = parse_semver(version)
                if v_semver and v_semver > latest_prod_semver:
                    beta_rows.append(idx)
            else:
                beta_rows.append(idx)

    return df.loc[beta_rows] if beta_rows else pd.DataFrame()


def format_relative_time(dt) -> str:
    """Format a datetime as relative time like '2 days 1 hour 34 min'."""
    if pd.isna(dt):
        return ""

    from datetime import datetime, timezone

    # Handle timezone-aware and naive datetimes
    now = datetime.now(timezone.utc)
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = now - dt
    except:
        return ""

    total_seconds = int(diff.total_seconds())
    if total_seconds < 0:
        return "just now"

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0 or not parts:
        parts.append(f"{minutes} min")

    return " ".join(parts)


def render_dock_table(dock_df: pd.DataFrame, column: str, version_label: str):
    """Render a dataframe of docks."""
    from datetime import datetime, timezone

    # Build display dataframe with all needed columns upfront
    cols_to_copy = ['serial', 'customer_name', 'customer_id', 'region', 'last_seen']
    if column and column in dock_df.columns:
        cols_to_copy.append(column)

    # Only include columns that exist in the dataframe
    cols_to_copy = [c for c in cols_to_copy if c in dock_df.columns]

    display_df = dock_df[cols_to_copy].copy()

    # Replace empty customer names with placeholder
    if 'customer_name' in display_df.columns:
        display_df['customer_name'] = display_df['customer_name'].fillna('—')
        display_df['customer_name'] = display_df['customer_name'].replace('', '—')

    # Replace empty customer IDs with placeholder
    if 'customer_id' in display_df.columns:
        display_df['customer_id'] = display_df['customer_id'].fillna('—')
        display_df['customer_id'] = display_df['customer_id'].replace('', '—')

    # Convert to datetime and handle timezone-aware datetimes
    display_df['last_seen_dt'] = pd.to_datetime(display_df['last_seen'], utc=True)

    # Calculate hours ago for proper numeric sorting (shows as decimal days)
    now = datetime.now(timezone.utc)
    display_df['hours_ago'] = display_df['last_seen_dt'].apply(
        lambda dt: round((now - dt).total_seconds() / 3600, 1) if pd.notna(dt) else 999999
    )

    # Sort by hours_ago descending (largest first = oldest)
    display_df = display_df.sort_values('hours_ago', ascending=False, na_position='last')

    # Add relative time column
    display_df['time_ago'] = display_df['last_seen_dt'].apply(format_relative_time)
    display_df['last_seen'] = display_df['last_seen_dt'].dt.strftime('%Y-%m-%d %H:%M')

    # Reorder columns: serial, customer_name, customer_id, region, last_seen, time_ago, hours_ago, version
    final_cols = ['serial', 'customer_name', 'customer_id', 'region', 'last_seen', 'time_ago', 'hours_ago']
    # Only include columns that exist
    final_cols = [c for c in final_cols if c in display_df.columns]
    if column and column in dock_df.columns:
        final_cols.append(column)

    display_df = display_df[final_cols]

    # Configure columns
    column_config = {
        'serial': st.column_config.TextColumn('Serial'),
        'customer_name': st.column_config.TextColumn('Customer'),
        'customer_id': st.column_config.TextColumn('Customer ID'),
        'region': st.column_config.TextColumn('Region'),
        'last_seen': st.column_config.TextColumn('Last Seen'),
        'time_ago': st.column_config.TextColumn('Time Ago'),
        'hours_ago': st.column_config.NumberColumn('Hours Ago', format="%.1f"),
    }
    if column and column in dock_df.columns:
        column_config[column] = st.column_config.TextColumn(version_label)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=min(300, len(display_df) * 35 + 40),
        column_config=column_config
    )


def toggle_state(key: str):
    """Toggle a session state key."""
    st.session_state[key] = not st.session_state.get(key, False)


def render_component_table(
    title: str,
    components: List[Dict],
    total_docks: int,
    table_id: str,
    df: Optional[pd.DataFrame] = None,
    entity_label: str = "docks"
):
    """Render a component compliance table with expandable outdated views."""

    # Section title with emphasis
    st.markdown(
        f"""<h2 style='color: #f1f5f9; font-size: 22px; font-weight: 700; margin: 30px 0 20px 0;
            font-family: Montserrat, sans-serif; padding-bottom: 10px;
            border-bottom: 2px solid #3b82f6;'>{title}</h2>""",
        unsafe_allow_html=True
    )

    # Table header
    header_cols = st.columns([2, 1.2, 1, 1, 1.2, 0.8, 2])
    headers = ["Component", "Latest Prod", "On Latest", "Outdated", "Beta", "On Beta", "Distribution"]
    for col, header in zip(header_cols, headers):
        col.markdown(
            f"<span style='color: #94a3b8; font-size: 14px; font-weight: 600; text-transform: uppercase; font-family: Montserrat, sans-serif;'>{header}</span>",
            unsafe_allow_html=True
        )

    st.markdown("<hr style='border: 1px solid #334155; margin: 8px 0;'>", unsafe_allow_html=True)

    # Component rows with inline expanders
    for idx, comp in enumerate(components):
        # Data row
        cols = st.columns([2, 1.2, 1, 1, 1.2, 0.8, 2])

        cols[0].markdown(
            f"<span style='color: #f1f5f9; font-family: Montserrat, sans-serif; font-size: 14px; font-weight: 500;'>{comp['name']}</span>",
            unsafe_allow_html=True
        )

        cols[1].markdown(
            f"<span style='color: #94a3b8; font-family: monospace; font-size: 14px;'>{comp['latest_production']}</span>",
            unsafe_allow_html=True
        )

        prod_color = get_compliance_color(comp['production_percentage'])
        cols[2].markdown(
            f"<span style='color: {prod_color}; font-weight: 600; font-size: 14px; font-family: Montserrat, sans-serif;'>{comp['production_percentage']}%</span>",
            unsafe_allow_html=True
        )

        outdated_pct = comp['outdated_percentage']
        outdated_count = comp['outdated_count']
        expand_key = f"expand_outdated_{table_id}_{idx}"

        if outdated_pct > 0:
            is_expanded = st.session_state.get(expand_key, False)
            icon = "▼" if is_expanded else "▶"

            with cols[3]:
                st.button(
                    f"{outdated_pct}% {icon}",
                    key=f"btn_{expand_key}",
                    help=f"Click to view {outdated_count} outdated {entity_label}",
                    type="primary",
                    on_click=toggle_state,
                    args=(expand_key,)
                )
        else:
            cols[3].markdown(
                "<span style='color: #22c55e; font-size: 20px; font-weight: 700;'>—</span>",
                unsafe_allow_html=True
            )

        if comp['latest_beta']:
            cols[4].markdown(
                f"<span style='background: #3b82f6; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; margin-right: 10px;'>Beta</span><span style='color: #f1f5f9; font-family: monospace; font-size: 14px;'>{comp['latest_beta']}</span>",
                unsafe_allow_html=True
            )
        else:
            cols[4].markdown("<span style='color: #475569; font-size: 14px;'>—</span>", unsafe_allow_html=True)

        beta_pct = comp['beta_percentage']
        beta_count = comp['beta_count']
        beta_expand_key = f"expand_beta_{table_id}_{idx}"

        if beta_pct > 0:
            beta_is_expanded = st.session_state.get(beta_expand_key, False)
            beta_icon = "▼" if beta_is_expanded else "▶"

            with cols[5]:
                st.button(
                    f"{beta_pct}% {beta_icon}",
                    key=f"btn_{beta_expand_key}",
                    help=f"Click to view {beta_count} {entity_label} on beta",
                    type="secondary",
                    on_click=toggle_state,
                    args=(beta_expand_key,)
                )
        else:
            cols[5].markdown("<span style='color: #475569; font-size: 14px;'>—</span>", unsafe_allow_html=True)

        fig = create_distribution_bar(comp['production_percentage'], comp['beta_percentage'])
        cols[6].plotly_chart(
            fig,
            use_container_width=True,
            config={'displayModeBar': False},
            key=f"chart_{table_id}_{idx}"
        )

        # Show expanded content inline
        expand_key = f"expand_outdated_{table_id}_{idx}"
        if df is not None and outdated_count > 0 and st.session_state.get(expand_key, False):
            outdated_df = get_outdated_docks_for_component(df, comp['name'], table_id)
            if len(outdated_df) > 0:
                column_map = _get_component_map(table_id)
                column = column_map.get(comp['name'], '')
                st.markdown(
                    f"<div style='background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; padding: 8px 12px; margin: 4px 0 8px 0; border-radius: 0 4px 4px 0;'><span style='color: #fca5a5; font-size: 14px; font-family: Montserrat, sans-serif;'>Outdated {entity_label} for {comp['name']} ({len(outdated_df)})</span></div>",
                    unsafe_allow_html=True
                )
                render_dock_table(outdated_df, column, 'Current Version')

        beta_expand_key = f"expand_beta_{table_id}_{idx}"
        if df is not None and beta_count > 0 and st.session_state.get(beta_expand_key, False):
            beta_df = get_beta_docks_for_component(df, comp['name'], table_id)
            if len(beta_df) > 0:
                column_map = _get_component_map(table_id)
                column = column_map.get(comp['name'], '')
                st.markdown(
                    f"<div style='background: rgba(59, 130, 246, 0.1); border-left: 3px solid #3b82f6; padding: 8px 12px; margin: 4px 0 8px 0; border-radius: 0 4px 4px 0;'><span style='color: #93c5fd; font-size: 14px; font-family: Montserrat, sans-serif;'>Beta {entity_label} for {comp['name']} ({len(beta_df)})</span></div>",
                    unsafe_allow_html=True
                )
                render_dock_table(beta_df, column, 'Beta Version')

    # Overall compliance row - use same column structure as header [2, 1.2, 1, 1, 1.2, 0.8, 2]
    total_production = sum(c['production_percentage'] for c in components) / len(components) if components else 0
    total_outdated = sum(c['outdated_percentage'] for c in components) / len(components) if components else 0
    overall_compliance = round(total_production)

    st.markdown("<hr style='border: 1px solid #475569; margin: 12px 0;'>", unsafe_allow_html=True)

    summary_cols = st.columns([2, 1.2, 1, 1, 1.2, 0.8, 2])
    summary_cols[0].markdown(
        "<span style='color: #f1f5f9; font-weight: 600; font-size: 14px; font-family: Montserrat, sans-serif;'>Overall Compliance</span>",
        unsafe_allow_html=True
    )

    # Empty column for Latest Prod
    summary_cols[1].markdown("", unsafe_allow_html=True)

    # On Latest %
    compliance_color = get_compliance_color(overall_compliance)
    summary_cols[2].markdown(
        f"<span style='color: {compliance_color}; font-weight: 700; font-size: 14px; font-family: Montserrat, sans-serif;'>{overall_compliance}%</span>",
        unsafe_allow_html=True
    )

    # Outdated %
    if total_outdated > 0:
        summary_cols[3].markdown(
            f"<span style='color: #ef4444; font-weight: 600; font-size: 14px; font-family: Montserrat, sans-serif;'>{round(total_outdated)}%</span>",
            unsafe_allow_html=True
        )
    else:
        summary_cols[3].markdown(
            "<span style='color: #22c55e; font-weight: 600; font-size: 14px; font-family: Montserrat, sans-serif;'>0%</span>",
            unsafe_allow_html=True
        )
