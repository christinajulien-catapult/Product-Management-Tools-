import streamlit as st
import pandas as pd
from datetime import datetime

from utils.data_loader import load_csv_data, load_data, filter_by_region
from utils.google_sheets import check_credentials_exist, get_service_account_email
from utils.metrics import (
    calculate_active_docks,
    calculate_all_component_compliance,
    calculate_fleet_compliance,
    get_docks_needing_update,
    GREENGRASS_COMPONENTS,
    DOCK_IMAGE_COMPONENTS
)
from components.metrics_cards import render_metrics_cards
from components.component_table import render_component_table
from components.export_reports import render_export_buttons


# Page config
st.set_page_config(
    page_title="Vector Dock Fleet Overview",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme styling with Montserrat font
st.markdown("""
    <style>
        /* Import Montserrat font */
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap');

        /* Apply Montserrat globally */
        html, body, [class*="css"], .stApp, .stMarkdown, p, span, label, h1, h2, h3, h4, h5, h6, div {
            font-family: 'Montserrat', sans-serif !important;
        }

        /* Main background */
        .stApp {
            background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        }

        /* Remove any white/light backgrounds from containers */
        .stApp > header {
            background: transparent !important;
        }

        div[data-testid="stHeader"] {
            background: transparent !important;
        }

        div[data-testid="stToolbar"] {
            background: transparent !important;
        }

        div[data-testid="stDecoration"] {
            background: transparent !important;
        }

        /* Main content area */
        .main .block-container {
            background: transparent !important;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: #1e293b;
            border-right: 1px solid #334155;
        }

        section[data-testid="stSidebar"] > div {
            background: #1e293b;
        }

        /* Headers */
        h1, h2, h3 {
            color: #f1f5f9 !important;
            font-family: 'Montserrat', sans-serif !important;
        }

        /* Text */
        p, span, label {
            color: #cbd5e1;
        }

        /* Selectbox */
        .stSelectbox > div > div {
            background-color: #334155;
            border-color: #475569;
        }

        /* File uploader */
        .stFileUploader > div {
            background-color: #334155;
            border-color: #475569;
        }

        /* Dataframe */
        .stDataFrame {
            background-color: #1e293b;
        }

        /* Expander styling - remove all backgrounds and borders */
        .streamlit-expanderHeader {
            background-color: transparent !important;
            color: #f1f5f9 !important;
            font-family: 'Montserrat', sans-serif !important;
            border: none !important;
        }

        div[data-testid="stExpander"] {
            border: none !important;
            background: transparent !important;
        }

        div[data-testid="stExpander"] > details {
            border: none !important;
            background: transparent !important;
        }

        div[data-testid="stExpander"] > details > summary {
            background: transparent !important;
            border: none !important;
            color: #94a3b8 !important;
        }

        div[data-testid="stExpander"] > details > summary:hover {
            color: #f1f5f9 !important;
        }

        /* Remove default padding */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        /* Button styling */
        .stButton > button {
            font-family: 'Montserrat', sans-serif !important;
        }

        /* Info box styling */
        div[data-testid="stAlert"] {
            background-color: rgba(59, 130, 246, 0.1) !important;
            border: 1px solid #3b82f6 !important;
            color: #93c5fd !important;
        }

        /* Hide Material Icons text that shows as plain text */
        [data-testid="stExpanderToggleIcon"],
        [data-testid="stIconMaterial"] {
            display: none !important;
        }

        /* Expander styling */
        .stExpander details {
            border: 1px solid #334155 !important;
            border-radius: 8px !important;
            margin-bottom: 4px !important;
        }

        .stExpander summary {
            color: #94a3b8 !important;
            font-family: 'Montserrat', sans-serif !important;
            padding: 8px 12px !important;
        }

        .stExpander summary:hover {
            color: #f1f5f9 !important;
        }

        .stExpander details[open] {
            border-color: #475569 !important;
        }

        /* Style expand buttons in table */
        .stButton button,
        .stButton button p,
        .stButton button span,
        button[data-testid^="stBaseButton"],
        button[data-testid^="stBaseButton"] p,
        button[data-testid^="stBaseButton"] span {
            background: transparent !important;
            border: none !important;
            padding: 2px 4px !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            font-family: 'Montserrat', sans-serif !important;
            cursor: pointer !important;
            min-height: 0 !important;
            line-height: 1.2 !important;
        }

        /* Primary button - red for outdated */
        button[data-testid="stBaseButton-primary"],
        button[data-testid="stBaseButton-primary"] p,
        button[data-testid="stBaseButton-primary"] span {
            color: #ef4444 !important;
            background: transparent !important;
            border: none !important;
        }

        button[data-testid="stBaseButton-primary"]:hover {
            background: rgba(239, 68, 68, 0.1) !important;
            border-radius: 4px !important;
        }

        /* Secondary button - blue for beta */
        button[data-testid="stBaseButton-secondary"],
        button[data-testid="stBaseButton-secondary"] p,
        button[data-testid="stBaseButton-secondary"] span {
            color: #3b82f6 !important;
            background: transparent !important;
            border: none !important;
        }

        button[data-testid="stBaseButton-secondary"]:hover {
            background: rgba(59, 130, 246, 0.1) !important;
            border-radius: 4px !important;
        }
    </style>
""", unsafe_allow_html=True)


def main():
    # Header will be rendered after we have data for export buttons
    header_placeholder = st.empty()

    # Sidebar
    with st.sidebar:
        st.markdown("### Data Source")

        # Data source selector
        data_source = st.radio(
            "Select data source",
            ["Google Sheets", "CSV Upload"],
            index=0 if check_credentials_exist() else 1,
            help="Choose where to load fleet data from",
            horizontal=True
        )

        uploaded_file = None
        google_sheet_url = None

        if data_source == "Google Sheets":
            # Check for credentials
            if not check_credentials_exist():
                st.warning(
                    "**Setup Required**\n\n"
                    "To use Google Sheets, you need a service account:\n"
                    "1. Create a Google Cloud project\n"
                    "2. Enable Google Sheets API\n"
                    "3. Create a service account\n"
                    "4. Download credentials JSON\n"
                    "5. Save as `credentials.json` in this folder"
                )
            else:
                # Show service account email for sharing
                service_email = get_service_account_email()
                if service_email:
                    with st.expander("Service account email"):
                        st.code(service_email, language=None)
                        st.caption("Share your Google Sheet with this email")

            # Google Sheet URL input
            google_sheet_url = st.text_input(
                "Google Sheet URL",
                value=st.session_state.get('google_sheet_url', ''),
                placeholder="https://docs.google.com/spreadsheets/d/...",
                help="Paste the full URL or just the sheet ID"
            )

            # Save URL to session state
            if google_sheet_url:
                st.session_state['google_sheet_url'] = google_sheet_url

            # Refresh button
            col1, col2 = st.columns([1, 1])
            with col1:
                refresh_clicked = st.button(
                    "🔄 Refresh Data",
                    use_container_width=True,
                    disabled=not google_sheet_url or not check_credentials_exist()
                )
            with col2:
                if st.button("Clear Cache", use_container_width=True):
                    if 'loaded_df' in st.session_state:
                        del st.session_state['loaded_df']
                    if 'last_refresh_time' in st.session_state:
                        del st.session_state['last_refresh_time']
                    st.rerun()

            # Handle refresh
            if refresh_clicked and google_sheet_url and check_credentials_exist():
                try:
                    with st.spinner("Fetching data from Google Sheets..."):
                        df = load_data('google_sheets', google_sheet_url)
                        st.session_state['loaded_df'] = df
                        st.session_state['last_refresh_time'] = datetime.now()
                        st.session_state['data_source_type'] = 'google_sheets'
                    st.success("Data refreshed successfully!")
                except Exception as e:
                    st.error(f"Error loading from Google Sheets: {str(e)}")

        else:
            # CSV Upload mode
            uploaded_file = st.file_uploader(
                "Upload CSV/TSV file",
                type=['csv', 'tsv'],
                help="Upload your dock fleet data export"
            )

        # Sample data option
        use_sample = st.checkbox("Use sample data (for demo)", value=False)

        st.markdown("---")

        st.markdown("### Filters")

        # Region selector
        region_options = ["All", "AU", "EU", "US"]
        selected_region = st.selectbox(
            "Region",
            region_options,
            index=0,
            help="Filter docks by region"
        )

        st.markdown("---")

        # Last updated / refreshed timestamp
        last_refresh = st.session_state.get('last_refresh_time')
        if last_refresh:
            time_ago = datetime.now() - last_refresh
            minutes_ago = int(time_ago.total_seconds() / 60)
            if minutes_ago < 1:
                time_str = "just now"
            elif minutes_ago < 60:
                time_str = f"{minutes_ago} min ago"
            else:
                hours = minutes_ago // 60
                time_str = f"{hours} hour{'s' if hours > 1 else ''} ago"

            st.markdown(
                f"""
                <div style="color: #64748b; font-size: 12px;">
                    <p>Last refreshed: {time_str}</p>
                    <p style="font-size: 10px;">{last_refresh.strftime('%Y-%m-%d %H:%M')}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div style="color: #64748b; font-size: 12px;">
                    <p>No data loaded</p>
                </div>
                """,
                unsafe_allow_html=True
            )

    # Check for file from main area uploader too
    main_file = st.session_state.get('main_uploader', None)
    active_file = uploaded_file if uploaded_file is not None else main_file

    # Store loaded data in session state to persist across reruns
    if active_file is not None:
        try:
            df = load_csv_data(active_file)
            st.session_state['loaded_df'] = df
            st.session_state['last_refresh_time'] = datetime.now()
            st.session_state['data_source_type'] = 'csv'
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            st.exception(e)
            return

    # Check if we have data loaded (from CSV, Google Sheets, or session state)
    has_data = (
        active_file is not None or
        'loaded_df' in st.session_state
    )

    # Main content - use cached data if available
    if has_data:
        try:
            # Use cached dataframe
            df = st.session_state.get('loaded_df')
            if df is None:
                st.error("No data loaded")
                return

            # Filter by region
            filtered_df = filter_by_region(df, selected_region)

            # Calculate metrics
            active_df, active_count = calculate_active_docks(filtered_df)
            _, fleet_compliance = calculate_fleet_compliance(filtered_df)
            outdated_docks = get_docks_needing_update(filtered_df)

            # Calculate regional counts from original data (before filtering)
            regional_counts = {}
            if 'region' in df.columns:
                for region in ['AU', 'EU', 'US']:
                    regional_counts[region] = len(df[df['region'] == region])

            # Calculate component compliance (needed for export buttons)
            greengrass_compliance = calculate_all_component_compliance(
                filtered_df, GREENGRASS_COMPONENTS
            )
            dock_image_compliance = calculate_all_component_compliance(
                filtered_df, DOCK_IMAGE_COMPONENTS
            )

            # Render header with export buttons
            with header_placeholder.container():
                st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
                header_col1, header_col2 = st.columns([3, 1])
                with header_col1:
                    st.markdown(
                        """
                        <h1 style="margin: 0; font-size: 26px; font-weight: 700; color: #f1f5f9; font-family: 'Montserrat', sans-serif;">
                            Vector Dock Fleet Overview
                        </h1>
                        """,
                        unsafe_allow_html=True
                    )
                with header_col2:
                    render_export_buttons(
                        total_docks=len(filtered_df),
                        active_docks=active_count,
                        fleet_compliance=fleet_compliance,
                        outdated_count=len(outdated_docks),
                        greengrass_components=greengrass_compliance,
                        dock_image_components=dock_image_compliance,
                        selected_region=selected_region,
                        compact=True
                    )

            st.markdown("<br>", unsafe_allow_html=True)

            # Render metrics cards
            render_metrics_cards(
                total_docks=len(filtered_df),
                active_docks=active_count,
                fleet_compliance=fleet_compliance,
                outdated_count=len(outdated_docks),
                selected_region=selected_region,
                regional_counts=regional_counts
            )

            st.markdown("<br>", unsafe_allow_html=True)

            # Render component tables
            render_component_table(
                "Greengrass Components",
                greengrass_compliance,
                len(filtered_df),
                "greengrass",
                filtered_df
            )

            render_component_table(
                "Dock Image",
                dock_image_compliance,
                len(filtered_df),
                "dock_image",
                filtered_df
            )

        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            st.exception(e)

    elif use_sample:
        # Generate sample data for demo
        st.info("Sample data mode - showing demo data")

        sample_data = {
            'region': ['AU', 'AU', 'EU', 'EU', 'US', 'US', 'US', 'AU'],
            'serial': ['627', '637', '267', '923', '732', '845', '668', '639'],
            'customer_name': ['Team A', 'Team B', 'Team C', 'Team D', 'Team E', 'Team F', 'Team G', 'Team H'],
            'customer_id': ['1548', '1308', '2291', '4060', '1219', '2104', '3370', '1548'],
            'model': ['DO-V8-VD-V1'] * 8,
            'last_seen': [datetime.now()] * 8,
            'pmu_version': ['1.0.4+9de1e872', '1.0.3+cd54c5f9', '1.0.4+9de1e872', '1.0.4+9de1e872',
                          '1.0.4+9de1e872', '1.0.4+9de1e872', '1.0.3+cd54c5f9', '1.0.3+cd54c5f9'],
            'device_version': ['1.1.0+08ca3ca'] * 8,
            'ble_version': ['1.17.1-production.20251209.235148.f35abd4'] * 8,
            'power_component_version': ['1.7.0-production.20260129.031159.49963db', '1.6.0-production.20251212.015324.1b99982'] * 4,
            'retriever_version': ['2.14.0-production.20251014.045700.4a19c9b'] * 8,
            'raw_file_upload_version': ['1.14.0-production.20251031.061902.2e2a0f3'] * 8,
            'device_manager_component_version': ['3.7.0-production.20251201.051918.3ac2d6e'] * 8,
            'dock_image_version': ['1.1.0-production.20250908.101443.08ca3ca', '', '1.1.0-production.20250908.101443.08ca3ca', '1.1.0-production.20250908.101443.08ca3ca', '', '', '1.1.0-production.20250908.101443.08ca3ca', ''],
            'dock_pmu_version': ['1.0.4-production.20251112.223600.9de1e872'] * 8,
            'images_up_to_date': [True, False, True, True, True, True, False, False],
            'components_up_to_date': [True, False, True, True, False, False, False, False],
            'components_needs_update': ['', 'dock_image', '', '', 'dock_image', 'dock_image', 'power, dock_image', 'dock_image'],
            'needs_update': ['', 'pmu', '', '', 'pmu', 'pmu', 'pmu', 'pmu'],
        }

        df = pd.DataFrame(sample_data)
        filtered_df = filter_by_region(df, selected_region)

        active_df, active_count = calculate_active_docks(filtered_df)
        _, fleet_compliance = calculate_fleet_compliance(filtered_df)
        outdated_docks = get_docks_needing_update(filtered_df)

        # Calculate regional counts from original data
        regional_counts = {}
        if 'region' in df.columns:
            for region in ['AU', 'EU', 'US']:
                regional_counts[region] = len(df[df['region'] == region])

        # Calculate component compliance (needed for export buttons)
        greengrass_compliance = calculate_all_component_compliance(
            filtered_df, GREENGRASS_COMPONENTS
        )
        dock_image_compliance = calculate_all_component_compliance(
            filtered_df, DOCK_IMAGE_COMPONENTS
        )

        # Render header with export buttons
        with header_placeholder.container():
            st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
            header_col1, header_col2 = st.columns([3, 1])
            with header_col1:
                st.markdown(
                    """
                    <h1 style="margin: 0; font-size: 26px; font-weight: 700; color: #f1f5f9; font-family: 'Montserrat', sans-serif;">
                        Vector Dock Fleet Overview
                    </h1>
                    """,
                    unsafe_allow_html=True
                )
            with header_col2:
                render_export_buttons(
                    total_docks=len(filtered_df),
                    active_docks=active_count,
                    fleet_compliance=fleet_compliance,
                    outdated_count=len(outdated_docks),
                    greengrass_components=greengrass_compliance,
                    dock_image_components=dock_image_compliance,
                    selected_region=selected_region,
                    compact=True
                )

        st.markdown("<br>", unsafe_allow_html=True)

        render_metrics_cards(
            total_docks=len(filtered_df),
            active_docks=active_count,
            fleet_compliance=fleet_compliance,
            outdated_count=len(outdated_docks),
            selected_region=selected_region,
            regional_counts=regional_counts
        )

        st.markdown("<br>", unsafe_allow_html=True)

        render_component_table(
            "Greengrass Components",
            greengrass_compliance,
            len(filtered_df),
            "greengrass",
            filtered_df
        )

        render_component_table(
            "Dock Image",
            dock_image_compliance,
            len(filtered_df),
            "dock_image",
            filtered_df
        )

    else:
        # Render header without export buttons for empty state
        with header_placeholder.container():
            st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <h1 style="margin: 0; font-size: 26px; font-weight: 700; color: #f1f5f9; font-family: 'Montserrat', sans-serif;">
                    Vector Dock Fleet Overview
                </h1>
                """,
                unsafe_allow_html=True
            )

        # Custom CSS for file uploader styling
        st.markdown("""
            <style>
                /* Style the file uploader container */
                [data-testid="stFileUploader"] {
                    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
                    border: 2px dashed #475569;
                    border-radius: 12px;
                    padding: 40px 20px;
                }

                [data-testid="stFileUploader"]:hover {
                    border-color: #3b82f6;
                }

                /* Style the Browse files button */
                [data-testid="stFileUploader"] button {
                    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
                    color: white !important;
                    border: none !important;
                    border-radius: 8px !important;
                    padding: 12px 32px !important;
                    font-family: 'Montserrat', sans-serif !important;
                    font-weight: 600 !important;
                    font-size: 14px !important;
                    cursor: pointer !important;
                    transition: all 0.2s ease !important;
                }

                [data-testid="stFileUploader"] button:hover {
                    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
                    transform: translateY(-1px) !important;
                    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4) !important;
                }

                /* Style the drag and drop text */
                [data-testid="stFileUploader"] section {
                    padding: 20px !important;
                }

                [data-testid="stFileUploader"] section > div {
                    color: #94a3b8 !important;
                    font-family: 'Montserrat', sans-serif !important;
                }

                /* Hide the default label */
                [data-testid="stFileUploader"] label {
                    display: none !important;
                }
            </style>
        """, unsafe_allow_html=True)

        # Empty state header
        st.markdown(
            """
            <div style="text-align: center; margin-top: 60px; margin-bottom: 20px;">
                <h2 style="color: #f1f5f9; margin-bottom: 8px; font-family: 'Montserrat', sans-serif; font-size: 28px; font-weight: 700;">
                    Welcome to Fleet Overview
                </h2>
                <p style="color: #64748b; font-size: 16px; font-family: 'Montserrat', sans-serif;">
                    Upload a CSV or TSV file to view your dock fleet status
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # File uploader in main area
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            main_uploaded_file = st.file_uploader(
                "Drop your file here",
                type=['csv', 'tsv'],
                help="Upload your dock fleet data export",
                key="main_uploader",
                label_visibility="collapsed"
            )


if __name__ == "__main__":
    main()
