import streamlit as st
from typing import Dict, Optional


def get_compliance_color(percentage: float) -> str:
    """Get color based on compliance percentage."""
    if percentage >= 75:
        return "#22c55e"  # Green
    elif percentage >= 50:
        return "#eab308"  # Yellow
    else:
        return "#ef4444"  # Red


def render_metrics_cards(
    total_docks: int,
    active_docks: int,
    fleet_compliance: float,
    outdated_count: int,
    selected_region: str = "All",
    regional_counts: Optional[Dict[str, int]] = None,
    entity_label: str = "Docks",
    compliance_subtitle: str = "All components on latest"
):
    """
    Render the top metrics cards.

    Args:
        total_docks: Total number of docks/devices
        active_docks: Number of active docks/devices (seen in last 14 days)
        fleet_compliance: Fleet compliance percentage
        outdated_count: Number of docks/devices needing updates
        selected_region: Currently selected region for display
        regional_counts: Dict of region -> count (e.g., {'AU': 100, 'EU': 50, 'US': 75})
        entity_label: Display label - "Docks" or "Devices"
        compliance_subtitle: Subtitle for compliance card
    """
    col1, col2, col3, col4 = st.columns(4)

    card_style = """
        background: rgba(30, 41, 59, 0.7);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #334155;
        height: 130px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
    """

    with col1:
        # Build regional breakdown string
        if regional_counts and selected_region == "All":
            region_parts = []
            for region in ['AU', 'EU', 'US']:
                if region in regional_counts:
                    region_parts.append(f"<span style='color: #94a3b8;'>{region}</span> <span style='color: #f1f5f9;'>{regional_counts[region]}</span>")
            regional_display = " &nbsp;·&nbsp; ".join(region_parts)
        else:
            regional_display = f"Region: {selected_region}" if selected_region != "All" else "All Regions"

        st.markdown(
            f"""
            <div style="{card_style}">
                <p style="color: #94a3b8; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin: 0; font-family: 'Montserrat', sans-serif; text-align: center;">
                    Total {entity_label}
                </p>
                <p style="color: #f1f5f9; font-size: 36px; font-weight: 700; margin: 8px 0; font-family: 'Montserrat', sans-serif; text-align: center;">
                    {total_docks:,}
                </p>
                <p style="font-size: 12px; margin: 0; font-family: 'Montserrat', sans-serif; text-align: center;">
                    {regional_display}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        active_percentage = round((active_docks / total_docks) * 100, 1) if total_docks > 0 else 0
        st.markdown(
            f"""
            <div style="{card_style}">
                <p style="color: #94a3b8; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin: 0; font-family: 'Montserrat', sans-serif; text-align: center;">
                    Active {entity_label}
                </p>
                <p style="color: #f1f5f9; font-size: 36px; font-weight: 700; margin: 8px 0; font-family: 'Montserrat', sans-serif; text-align: center;">
                    {active_docks:,}
                </p>
                <p style="color: #64748b; font-size: 11px; margin: 0; font-family: 'Montserrat', sans-serif; text-align: center;">
                    {active_percentage}% seen in last 14 days
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        compliance_color = get_compliance_color(fleet_compliance)
        st.markdown(
            f"""
            <div style="{card_style}">
                <p style="color: #94a3b8; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin: 0; font-family: 'Montserrat', sans-serif; text-align: center;">
                    Fleet Compliance
                </p>
                <p style="color: {compliance_color}; font-size: 36px; font-weight: 700; margin: 8px 0; font-family: 'Montserrat', sans-serif; text-align: center;">
                    {fleet_compliance}%
                </p>
                <p style="color: #64748b; font-size: 11px; margin: 0; font-family: 'Montserrat', sans-serif; text-align: center;">
                    {compliance_subtitle}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col4:
        if outdated_count == 0:
            st.markdown(
                f"""
                <div style="{card_style} border-color: #22c55e;">
                    <p style="color: #94a3b8; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin: 0; font-family: 'Montserrat', sans-serif; text-align: center;">
                        Needs Attention
                    </p>
                    <p style="color: #22c55e; font-size: 36px; font-weight: 700; margin: 8px 0; font-family: 'Montserrat', sans-serif; text-align: center;">
                        All Good!
                    </p>
                    <p style="color: #22c55e; font-size: 11px; margin: 0; font-family: 'Montserrat', sans-serif; text-align: center;">
                        No {entity_label.lower()} need updates
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div style="{card_style}">
                    <p style="color: #94a3b8; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin: 0; font-family: 'Montserrat', sans-serif; text-align: center;">
                        Needs Attention
                    </p>
                    <p style="color: #ef4444; font-size: 36px; font-weight: 700; margin: 8px 0; font-family: 'Montserrat', sans-serif; text-align: center;">
                        {outdated_count:,}
                    </p>
                    <p style="color: #64748b; font-size: 11px; margin: 0; font-family: 'Montserrat', sans-serif; text-align: center;">
                        {entity_label} needing updates
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
