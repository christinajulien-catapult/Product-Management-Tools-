import streamlit as st
from datetime import datetime
from typing import List, Dict
import io


def generate_pdf_report(
    total_docks: int,
    active_docks: int,
    fleet_compliance: float,
    outdated_count: int,
    greengrass_components: List[Dict],
    dock_image_components: List[Dict],
    selected_region: str = "All"
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
