import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
import io

from utils.version_utils import parse_semver, get_latest_version, get_latest_version_by_adoption, detect_version_type, get_display_version
from utils.metrics import GREENGRASS_COMPONENTS, DOCK_IMAGE_COMPONENTS, VERSION_OVERRIDES
from utils.device_metrics import DEVICE_COMPONENTS


def _get_outdated_docks_for_pdf(df: pd.DataFrame, component_name: str, component_map: Dict[str, str]) -> pd.DataFrame:
    """Get outdated docks for a component, returning customer/serial/version info."""
    column = component_map.get(component_name)
    if not column or column not in df.columns:
        return pd.DataFrame()

    override = VERSION_OVERRIDES.get(column)

    if override:
        latest_prod_semver = override['latest_production']
        latest_beta_semver = override.get('latest_beta')
    else:
        versions = df[column].dropna().tolist()
        versions = [v for v in versions if isinstance(v, str) and v.strip() != '']
        latest_production = get_latest_version(versions, "production")
        latest_prod_semver = parse_semver(latest_production) if latest_production else None
        latest_beta_semver = None

    outdated_rows = []
    for idx, row in df.iterrows():
        version = row.get(column, '')
        if not version or pd.isna(version) or str(version).strip() == '':
            outdated_rows.append(idx)
            continue
        v_semver = parse_semver(version)
        if not v_semver:
            outdated_rows.append(idx)
            continue

        if override:
            # Exact production match or above is not outdated
            if latest_prod_semver and v_semver == latest_prod_semver:
                continue
            # Beta match is not outdated
            if latest_beta_semver and v_semver >= latest_beta_semver:
                continue
            # Above production is not outdated
            if latest_prod_semver and v_semver > latest_prod_semver:
                continue
            outdated_rows.append(idx)
        else:
            if detect_version_type(str(version)) == "beta":
                continue
            if latest_prod_semver and v_semver < latest_prod_semver:
                outdated_rows.append(idx)

    if not outdated_rows:
        return pd.DataFrame()

    result = df.loc[outdated_rows][['serial', 'customer_name', 'customer_id']].copy()
    result['version'] = df.loc[outdated_rows, column].apply(
        lambda v: get_display_version(str(v)) if pd.notna(v) and str(v).strip() else 'N/A'
    )
    return result.sort_values('customer_name', na_position='last')


def generate_pdf_report(
    total_docks: int,
    active_docks: int,
    fleet_compliance: float,
    outdated_count: int,
    greengrass_components: List[Dict],
    dock_image_components: List[Dict],
    selected_region: str = "All",
    df: Optional[pd.DataFrame] = None
) -> bytes:
    """Generate a PDF report of fleet stats."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font('Helvetica', 'B', 24)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 15, 'Vector Dock Fleet Report', ln=True, align='C')

    # Date and Region
    pdf.set_font('Helvetica', '', 12)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.cell(0, 8, f"Region: {selected_region}", ln=True, align='C')
    pdf.ln(10)

    # Summary Metrics
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, 'Fleet Summary', ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    pdf.set_font('Helvetica', '', 12)
    pdf.set_text_color(51, 65, 85)

    metrics = [
        ('Total Docks', str(total_docks)),
        ('Active Docks (14 days)', f"{active_docks} ({round(active_docks/total_docks*100) if total_docks > 0 else 0}%)"),
        ('Fleet Compliance', f"{fleet_compliance}%"),
        ('Docks Needing Attention', str(outdated_count)),
    ]

    for label, value in metrics:
        pdf.cell(80, 8, label + ':', ln=False)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, value, ln=True)
        pdf.set_font('Helvetica', '', 12)

    pdf.ln(10)

    # Greengrass Components
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, 'Greengrass Components', ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # Table header
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(241, 245, 249)
    pdf.cell(50, 8, 'Component', border=1, fill=True)
    pdf.cell(35, 8, 'Latest Prod', border=1, fill=True, align='C')
    pdf.cell(25, 8, 'On Latest', border=1, fill=True, align='C')
    pdf.cell(25, 8, 'Outdated', border=1, fill=True, align='C')
    pdf.cell(25, 8, 'On Beta', border=1, fill=True, align='C')
    pdf.cell(30, 8, 'Latest Beta', border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font('Helvetica', '', 10)
    for comp in greengrass_components:
        pdf.cell(50, 7, comp['name'], border=1)
        pdf.cell(35, 7, comp['latest_production'], border=1, align='C')

        # Color code On Latest
        if comp['production_percentage'] >= 75:
            pdf.set_text_color(34, 197, 94)
        elif comp['production_percentage'] >= 50:
            pdf.set_text_color(234, 179, 8)
        else:
            pdf.set_text_color(239, 68, 68)
        pdf.cell(25, 7, f"{comp['production_percentage']}%", border=1, align='C')
        pdf.set_text_color(51, 65, 85)

        # Color code Outdated
        if comp['outdated_percentage'] > 0:
            pdf.set_text_color(239, 68, 68)
        pdf.cell(25, 7, f"{comp['outdated_percentage']}%", border=1, align='C')
        pdf.set_text_color(51, 65, 85)

        # Beta
        pdf.set_text_color(59, 130, 246)
        pdf.cell(25, 7, f"{comp['beta_percentage']}%" if comp['beta_percentage'] > 0 else "-", border=1, align='C')
        pdf.cell(30, 7, comp['latest_beta'] if comp['latest_beta'] else "-", border=1, align='C')
        pdf.set_text_color(51, 65, 85)
        pdf.ln()

    pdf.ln(10)

    # Dock Image Components
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, 'Dock Image Components', ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # Table header
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(241, 245, 249)
    pdf.cell(50, 8, 'Component', border=1, fill=True)
    pdf.cell(35, 8, 'Latest Prod', border=1, fill=True, align='C')
    pdf.cell(25, 8, 'On Latest', border=1, fill=True, align='C')
    pdf.cell(25, 8, 'Outdated', border=1, fill=True, align='C')
    pdf.cell(25, 8, 'On Beta', border=1, fill=True, align='C')
    pdf.cell(30, 8, 'Latest Beta', border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font('Helvetica', '', 10)
    for comp in dock_image_components:
        pdf.cell(50, 7, comp['name'], border=1)
        pdf.cell(35, 7, comp['latest_production'], border=1, align='C')

        # Color code On Latest
        if comp['production_percentage'] >= 75:
            pdf.set_text_color(34, 197, 94)
        elif comp['production_percentage'] >= 50:
            pdf.set_text_color(234, 179, 8)
        else:
            pdf.set_text_color(239, 68, 68)
        pdf.cell(25, 7, f"{comp['production_percentage']}%", border=1, align='C')
        pdf.set_text_color(51, 65, 85)

        # Color code Outdated
        if comp['outdated_percentage'] > 0:
            pdf.set_text_color(239, 68, 68)
        pdf.cell(25, 7, f"{comp['outdated_percentage']}%", border=1, align='C')
        pdf.set_text_color(51, 65, 85)

        # Beta
        pdf.set_text_color(59, 130, 246)
        pdf.cell(25, 7, f"{comp['beta_percentage']}%" if comp['beta_percentage'] > 0 else "-", border=1, align='C')
        pdf.cell(30, 7, comp['latest_beta'] if comp['latest_beta'] else "-", border=1, align='C')
        pdf.set_text_color(51, 65, 85)
        pdf.ln()

    # Docks Needing Updates - detailed customer/serial breakdown
    if df is not None and len(df) > 0:
        all_component_maps = [
            ("Greengrass", GREENGRASS_COMPONENTS, greengrass_components),
            ("Dock Image", DOCK_IMAGE_COMPONENTS, dock_image_components),
        ]

        has_any_outdated = False
        for section_name, component_map, comp_stats in all_component_maps:
            for comp in comp_stats:
                if comp['outdated_count'] > 0:
                    has_any_outdated = True
                    break

        if has_any_outdated:
            pdf.add_page()
            pdf.set_font('Helvetica', 'B', 16)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(0, 10, 'Docks Needing Updates', ln=True)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)

            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(0, 7, 'Customers and docks with outdated component versions, grouped by component.', ln=True)
            pdf.ln(5)

            for section_name, component_map, comp_stats in all_component_maps:
                for comp in comp_stats:
                    if comp['outdated_count'] == 0:
                        continue

                    outdated_df = _get_outdated_docks_for_pdf(df, comp['name'], component_map)
                    if outdated_df.empty:
                        continue

                    # Check if we need a new page (leave room for header + a few rows)
                    if pdf.get_y() > 240:
                        pdf.add_page()

                    # Component sub-header
                    pdf.set_font('Helvetica', 'B', 12)
                    pdf.set_text_color(30, 41, 59)
                    pdf.cell(0, 9, f"{comp['name']}  -  {comp['outdated_count']} outdated  (latest: {comp['latest_production']})", ln=True)

                    # Table header
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.set_fill_color(241, 245, 249)
                    pdf.set_text_color(51, 65, 85)
                    pdf.cell(50, 7, 'Customer', border=1, fill=True)
                    pdf.cell(30, 7, 'Customer ID', border=1, fill=True, align='C')
                    pdf.cell(45, 7, 'Serial', border=1, fill=True)
                    pdf.cell(40, 7, 'Current Version', border=1, fill=True, align='C')
                    pdf.ln()

                    # Table rows
                    pdf.set_font('Helvetica', '', 8)
                    pdf.set_text_color(51, 65, 85)
                    for _, row in outdated_df.iterrows():
                        if pdf.get_y() > 270:
                            pdf.add_page()
                            # Re-print header on new page
                            pdf.set_font('Helvetica', 'B', 12)
                            pdf.set_text_color(30, 41, 59)
                            pdf.cell(0, 9, f"{comp['name']} (continued)", ln=True)
                            pdf.set_font('Helvetica', 'B', 9)
                            pdf.set_fill_color(241, 245, 249)
                            pdf.set_text_color(51, 65, 85)
                            pdf.cell(50, 7, 'Customer', border=1, fill=True)
                            pdf.cell(30, 7, 'Customer ID', border=1, fill=True, align='C')
                            pdf.cell(45, 7, 'Serial', border=1, fill=True)
                            pdf.cell(40, 7, 'Current Version', border=1, fill=True, align='C')
                            pdf.ln()
                            pdf.set_font('Helvetica', '', 8)
                            pdf.set_text_color(51, 65, 85)

                        customer = str(row.get('customer_name', '—')) if pd.notna(row.get('customer_name')) and str(row.get('customer_name', '')).strip() else '—'
                        customer_id = str(row.get('customer_id', '—')) if pd.notna(row.get('customer_id')) and str(row.get('customer_id', '')).strip() else '—'
                        serial = str(row.get('serial', '—')) if pd.notna(row.get('serial')) else '—'
                        version = str(row.get('version', '—'))

                        # Truncate long strings to fit cells
                        pdf.cell(50, 6, customer[:30], border=1)
                        pdf.cell(30, 6, customer_id[:18], border=1, align='C')
                        pdf.cell(45, 6, serial[:28], border=1)
                        pdf.set_text_color(239, 68, 68)
                        pdf.cell(40, 6, version[:24], border=1, align='C')
                        pdf.set_text_color(51, 65, 85)
                        pdf.ln()

                    pdf.ln(6)

    return bytes(pdf.output())


def generate_slack_summary(
    total_docks: int,
    active_docks: int,
    fleet_compliance: float,
    outdated_count: int,
    greengrass_components: List[Dict],
    dock_image_components: List[Dict],
    selected_region: str = "All"
) -> str:
    """Generate a Slack-formatted summary of fleet stats."""

    # Emoji helpers
    def get_status_emoji(pct):
        if pct >= 75:
            return ":large_green_circle:"
        elif pct >= 50:
            return ":large_yellow_circle:"
        else:
            return ":red_circle:"

    lines = []

    # Header
    lines.append(f":dock: *Vector Dock Fleet Report* - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Region: *{selected_region}*")
    lines.append("")

    # Summary
    lines.append("*:bar_chart: Fleet Summary*")
    lines.append(f"• Total Docks: *{total_docks}*")
    active_pct = round(active_docks/total_docks*100) if total_docks > 0 else 0
    lines.append(f"• Active (14 days): *{active_docks}* ({active_pct}%)")
    lines.append(f"• Fleet Compliance: {get_status_emoji(fleet_compliance)} *{fleet_compliance}%*")
    if outdated_count > 0:
        lines.append(f"• :warning: Needs Attention: *{outdated_count} docks*")
    else:
        lines.append(f"• :white_check_mark: All docks up to date!")
    lines.append("")

    # Greengrass Components
    lines.append("*:gear: Greengrass Components*")
    for comp in greengrass_components:
        emoji = get_status_emoji(comp['production_percentage'])
        line = f"• {emoji} *{comp['name']}*: {comp['production_percentage']}% on latest ({comp['latest_production']})"
        if comp['outdated_percentage'] > 0:
            line += f" | :red_circle: {comp['outdated_percentage']}% outdated"
        if comp['beta_percentage'] > 0:
            line += f" | :large_blue_circle: {comp['beta_percentage']}% on beta"
        lines.append(line)
    lines.append("")

    # Dock Image Components
    lines.append("*:floppy_disk: Dock Image Components*")
    for comp in dock_image_components:
        emoji = get_status_emoji(comp['production_percentage'])
        line = f"• {emoji} *{comp['name']}*: {comp['production_percentage']}% on latest ({comp['latest_production']})"
        if comp['outdated_percentage'] > 0:
            line += f" | :red_circle: {comp['outdated_percentage']}% outdated"
        if comp['beta_percentage'] > 0:
            line += f" | :large_blue_circle: {comp['beta_percentage']}% on beta"
        lines.append(line)
    lines.append("")

    # Action items
    total_outdated_components = sum(1 for c in greengrass_components + dock_image_components if c['outdated_percentage'] > 0)
    if total_outdated_components > 0:
        lines.append("*:memo: Action Required*")
        for comp in greengrass_components + dock_image_components:
            if comp['outdated_percentage'] > 0:
                lines.append(f"• Update *{comp['name']}* - {comp['outdated_count']} docks need update to {comp['latest_production']}")

    return "\n".join(lines)


def render_export_buttons(
    total_docks: int,
    active_docks: int,
    fleet_compliance: float,
    outdated_count: int,
    greengrass_components: List[Dict],
    dock_image_components: List[Dict],
    selected_region: str = "All",
    compact: bool = False
):
    """Render export buttons for PDF and Slack summary."""

    # Generate the data
    pdf_bytes = generate_pdf_report(
        total_docks, active_docks, fleet_compliance, outdated_count,
        greengrass_components, dock_image_components, selected_region
    )
    slack_text = generate_slack_summary(
        total_docks, active_docks, fleet_compliance, outdated_count,
        greengrass_components, dock_image_components, selected_region
    )

    if compact:
        # Compact layout for top-right placement
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="PDF Report",
                data=pdf_bytes,
                file_name=f"fleet_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        with col2:
            # Store slack text in session state for copying
            if 'slack_text' not in st.session_state:
                st.session_state['slack_text'] = slack_text
            else:
                st.session_state['slack_text'] = slack_text

            if st.button("Create Slack Message", use_container_width=True, key="slack_btn_compact"):
                st.session_state['show_slack_copy'] = True

        # Show copyable text area when button is clicked
        if st.session_state.get('show_slack_copy', False):
            st.text_area("Copy this message:", slack_text, height=200, key="slack_copy_area")
            if st.button("Done", key="slack_done_btn"):
                st.session_state['show_slack_copy'] = False
                st.rerun()
    else:
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            st.download_button(
                label="PDF Report",
                data=pdf_bytes,
                file_name=f"fleet_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        with col2:
            if st.button("Create Slack Message", use_container_width=True, key="slack_btn_full"):
                st.session_state['show_slack_copy'] = True

        # Show copyable text area when button is clicked
        if st.session_state.get('show_slack_copy', False):
            st.text_area("Copy this message:", slack_text, height=200, key="slack_copy_area_full")
            if st.button("Done", key="slack_done_btn_full"):
                st.session_state['show_slack_copy'] = False
                st.rerun()


def generate_device_pdf_report(
    total_devices: int,
    active_devices: int,
    fleet_compliance: float,
    outdated_count: int,
    fw_compliance: List[Dict],
    selected_region: str = "All",
    df: Optional[pd.DataFrame] = None
) -> bytes:
    """Generate a PDF report for device fleet stats with customer breakdown by region."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font('Helvetica', 'B', 24)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 15, 'Vector Device Fleet Report', ln=True, align='C')

    # Date and Region
    pdf.set_font('Helvetica', '', 12)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.cell(0, 8, f"Region: {selected_region}", ln=True, align='C')
    pdf.ln(10)

    # Summary Metrics
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, 'Fleet Summary', ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    pdf.set_font('Helvetica', '', 12)
    pdf.set_text_color(51, 65, 85)

    metrics = [
        ('Total Devices', str(total_devices)),
        ('Active Devices (14 days)', f"{active_devices} ({round(active_devices/total_devices*100) if total_devices > 0 else 0}%)"),
        ('Firmware Compliance', f"{fleet_compliance}%"),
        ('Devices Needing Update', str(outdated_count)),
    ]

    for label, value in metrics:
        pdf.cell(80, 8, label + ':', ln=False)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, value, ln=True)
        pdf.set_font('Helvetica', '', 12)

    pdf.ln(10)

    # Firmware Version Summary
    if fw_compliance:
        comp = fw_compliance[0]
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 10, 'Firmware Version', ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        pdf.set_font('Helvetica', '', 12)
        pdf.set_text_color(51, 65, 85)

        fw_info = [
            ('Latest Production', comp['latest_production']),
            ('On Latest', f"{comp['production_percentage']}% ({comp['production_count']} devices)"),
            ('Outdated', f"{comp['outdated_percentage']}% ({comp['outdated_count']} devices)"),
        ]
        if comp['latest_beta']:
            fw_info.append(('Latest Beta', comp['latest_beta']))
            fw_info.append(('On Beta/Alpha', f"{comp['beta_percentage']}% ({comp['beta_count']} devices)"))

        for label, value in fw_info:
            pdf.cell(80, 8, label + ':', ln=False)
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(0, 8, value, ln=True)
            pdf.set_font('Helvetica', '', 12)

    # Customers needing updates by region
    if df is not None and len(df) > 0:
        column = 'fw_version'
        versions = df[column].dropna().tolist()
        versions = [v for v in versions if isinstance(v, str) and v.strip() != '']
        latest_prod = get_latest_version_by_adoption(versions, "production")
        latest_prod_semver = parse_semver(latest_prod) if latest_prod else None
        latest_display = get_display_version(latest_prod) if latest_prod else 'N/A'

        # Find outdated devices
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

        if outdated_rows:
            outdated_df = df.loc[outdated_rows].copy()
            outdated_df['display_version'] = outdated_df[column].apply(
                lambda v: get_display_version(str(v)) if pd.notna(v) and str(v).strip() else 'N/A'
            )

            # Group by region
            regions = sorted(outdated_df['region'].unique())

            pdf.add_page()
            pdf.set_font('Helvetica', 'B', 16)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(0, 10, f'Devices Needing Update to {latest_display}', ln=True)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)

            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(0, 7, 'Customers and devices with outdated firmware, grouped by region.', ln=True)
            pdf.ln(5)

            for region in regions:
                region_df = outdated_df[outdated_df['region'] == region]
                if region_df.empty:
                    continue

                # Aggregate by customer
                customer_groups = region_df.groupby(['customer_name', 'customer_id']).agg(
                    device_count=('serial', 'count'),
                    serials=('serial', lambda x: ', '.join(x.astype(str).head(10))),
                    versions=('display_version', lambda x: ', '.join(x.unique()))
                ).reset_index().sort_values('customer_name', na_position='last')

                if pdf.get_y() > 240:
                    pdf.add_page()

                # Region header
                pdf.set_font('Helvetica', 'B', 14)
                pdf.set_text_color(30, 41, 59)
                pdf.cell(0, 10, f"{region}  ({len(region_df)} devices, {len(customer_groups)} customers)", ln=True)

                # Table header
                pdf.set_font('Helvetica', 'B', 9)
                pdf.set_fill_color(241, 245, 249)
                pdf.set_text_color(51, 65, 85)
                pdf.cell(45, 7, 'Customer', border=1, fill=True)
                pdf.cell(25, 7, 'Customer ID', border=1, fill=True, align='C')
                pdf.cell(15, 7, 'Count', border=1, fill=True, align='C')
                pdf.cell(35, 7, 'Current Version(s)', border=1, fill=True, align='C')
                pdf.cell(70, 7, 'Serials', border=1, fill=True)
                pdf.ln()

                # Table rows
                pdf.set_font('Helvetica', '', 8)
                pdf.set_text_color(51, 65, 85)
                for _, row in customer_groups.iterrows():
                    if pdf.get_y() > 270:
                        pdf.add_page()
                        pdf.set_font('Helvetica', 'B', 14)
                        pdf.set_text_color(30, 41, 59)
                        pdf.cell(0, 10, f"{region} (continued)", ln=True)
                        pdf.set_font('Helvetica', 'B', 9)
                        pdf.set_fill_color(241, 245, 249)
                        pdf.set_text_color(51, 65, 85)
                        pdf.cell(45, 7, 'Customer', border=1, fill=True)
                        pdf.cell(25, 7, 'Customer ID', border=1, fill=True, align='C')
                        pdf.cell(15, 7, 'Count', border=1, fill=True, align='C')
                        pdf.cell(35, 7, 'Current Version(s)', border=1, fill=True, align='C')
                        pdf.cell(70, 7, 'Serials', border=1, fill=True)
                        pdf.ln()
                        pdf.set_font('Helvetica', '', 8)
                        pdf.set_text_color(51, 65, 85)

                    customer = str(row['customer_name']) if row['customer_name'] else '-'
                    if not customer.strip():
                        customer = '-'
                    cid = str(row['customer_id']) if row['customer_id'] else '-'
                    count = str(row['device_count'])
                    vers = str(row['versions'])
                    serials = str(row['serials'])

                    pdf.cell(45, 6, customer[:26], border=1)
                    pdf.cell(25, 6, cid[:15], border=1, align='C')
                    pdf.cell(15, 6, count, border=1, align='C')
                    pdf.set_text_color(239, 68, 68)
                    pdf.cell(35, 6, vers[:20], border=1, align='C')
                    pdf.set_text_color(51, 65, 85)
                    pdf.cell(70, 6, serials[:42], border=1)
                    pdf.ln()

                pdf.ln(6)

            # Flagged version section: 0.3.4+d8bbe0d5
            flagged_version = '0.3.4+d8bbe0d5'
            flagged_df = df[df[column] == flagged_version]
            if not flagged_df.empty:
                pdf.add_page()
                pdf.set_font('Helvetica', 'B', 16)
                pdf.set_text_color(239, 68, 68)
                pdf.cell(0, 10, f'FLAGGED: Devices on {get_display_version(flagged_version)}', ln=True)
                pdf.set_text_color(30, 41, 59)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)

                pdf.set_font('Helvetica', '', 10)
                pdf.set_text_color(100, 116, 139)
                pdf.cell(0, 7, f'{len(flagged_df)} devices still on version {flagged_version} - requires immediate attention.', ln=True)
                pdf.ln(5)

                flagged_regions = sorted(flagged_df['region'].unique())
                for region in flagged_regions:
                    region_flagged = flagged_df[flagged_df['region'] == region]
                    if region_flagged.empty:
                        continue

                    customer_groups = region_flagged.groupby(['customer_name', 'customer_id']).agg(
                        device_count=('serial', 'count'),
                        serials=('serial', lambda x: ', '.join(x.astype(str).head(10))),
                    ).reset_index().sort_values('device_count', ascending=False)

                    if pdf.get_y() > 240:
                        pdf.add_page()

                    pdf.set_font('Helvetica', 'B', 14)
                    pdf.set_text_color(30, 41, 59)
                    pdf.cell(0, 10, f"{region}  ({len(region_flagged)} devices, {len(customer_groups)} customers)", ln=True)

                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.set_fill_color(254, 226, 226)
                    pdf.set_text_color(51, 65, 85)
                    pdf.cell(55, 7, 'Customer', border=1, fill=True)
                    pdf.cell(30, 7, 'Customer ID', border=1, fill=True, align='C')
                    pdf.cell(20, 7, 'Devices', border=1, fill=True, align='C')
                    pdf.cell(85, 7, 'Serials', border=1, fill=True)
                    pdf.ln()

                    pdf.set_font('Helvetica', '', 8)
                    pdf.set_text_color(51, 65, 85)
                    for _, row in customer_groups.iterrows():
                        if pdf.get_y() > 270:
                            pdf.add_page()
                            pdf.set_font('Helvetica', 'B', 14)
                            pdf.set_text_color(30, 41, 59)
                            pdf.cell(0, 10, f"{region} (continued)", ln=True)
                            pdf.set_font('Helvetica', 'B', 9)
                            pdf.set_fill_color(254, 226, 226)
                            pdf.set_text_color(51, 65, 85)
                            pdf.cell(55, 7, 'Customer', border=1, fill=True)
                            pdf.cell(30, 7, 'Customer ID', border=1, fill=True, align='C')
                            pdf.cell(20, 7, 'Devices', border=1, fill=True, align='C')
                            pdf.cell(85, 7, 'Serials', border=1, fill=True)
                            pdf.ln()
                            pdf.set_font('Helvetica', '', 8)
                            pdf.set_text_color(51, 65, 85)

                        customer = str(row['customer_name']) if row['customer_name'] else '-'
                        if not customer.strip():
                            customer = '-'
                        cid = str(row['customer_id']) if row['customer_id'] else '-'
                        count = str(row['device_count'])
                        serials = str(row['serials'])

                        pdf.cell(55, 6, customer[:32], border=1)
                        pdf.cell(30, 6, cid[:18], border=1, align='C')
                        pdf.set_text_color(239, 68, 68)
                        pdf.cell(20, 6, count, border=1, align='C')
                        pdf.set_text_color(51, 65, 85)
                        pdf.cell(85, 6, serials[:52], border=1)
                        pdf.ln()

                    pdf.ln(6)

    return bytes(pdf.output())
