import streamlit as st
import pandas as pd
from datetime import datetime


def render_dock_details(df: pd.DataFrame):
    """
    Render the dock details table with filtering.

    Args:
        df: DataFrame with dock data
    """
    st.markdown(
        """
        <h3 style="color: #f1f5f9; font-size: 18px; font-weight: 600; margin-bottom: 12px; font-family: 'Montserrat', sans-serif;">
            Dock Details
        </h3>
        """,
        unsafe_allow_html=True
    )

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        search_term = st.text_input(
            "Search by serial or customer",
            key="dock_search",
            placeholder="Enter serial number or customer name..."
        )

    with col2:
        filter_options = ["All Docks", "Needs Update", "Up to Date"]
        status_filter = st.selectbox("Status", filter_options, key="status_filter")

    with col3:
        sort_options = ["Last Seen (Recent)", "Last Seen (Oldest)", "Serial", "Customer"]
        sort_by = st.selectbox("Sort By", sort_options, key="sort_by")

    # Apply filters
    filtered_df = df.copy()

    if search_term:
        search_lower = search_term.lower()
        filtered_df = filtered_df[
            (filtered_df['serial'].astype(str).str.lower().str.contains(search_lower)) |
            (filtered_df['customer_name'].astype(str).str.lower().str.contains(search_lower))
        ]

    if status_filter == "Needs Update":
        filtered_df = filtered_df[
            (filtered_df['components_needs_update'].notna()) &
            (filtered_df['components_needs_update'].str.strip() != '')
        ]
    elif status_filter == "Up to Date":
        filtered_df = filtered_df[
            (filtered_df['components_up_to_date'] == True) |
            (filtered_df['components_needs_update'].isna()) |
            (filtered_df['components_needs_update'].str.strip() == '')
        ]

    # Apply sorting
    if sort_by == "Last Seen (Recent)":
        filtered_df = filtered_df.sort_values('last_seen', ascending=False)
    elif sort_by == "Last Seen (Oldest)":
        filtered_df = filtered_df.sort_values('last_seen', ascending=True)
    elif sort_by == "Serial":
        filtered_df = filtered_df.sort_values('serial')
    elif sort_by == "Customer":
        filtered_df = filtered_df.sort_values('customer_name')

    # Show count
    st.markdown(
        f"<p style='color: #94a3b8; font-size: 12px; margin: 8px 0;'>Showing {len(filtered_df)} of {len(df)} docks</p>",
        unsafe_allow_html=True
    )

    # Prepare display dataframe
    display_columns = ['serial', 'customer_name', 'region', 'last_seen', 'components_needs_update']
    display_df = filtered_df[display_columns].copy()

    # Format last_seen
    display_df['last_seen'] = pd.to_datetime(display_df['last_seen']).dt.strftime('%Y-%m-%d %H:%M')

    # Rename columns for display
    display_df.columns = ['Serial', 'Customer', 'Region', 'Last Seen', 'Needs Update']

    # Replace empty/NaN with checkmark
    display_df['Needs Update'] = display_df['Needs Update'].apply(
        lambda x: x if x and str(x).strip() else '✓'
    )

    # Display table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            "Serial": st.column_config.TextColumn("Serial", width="small"),
            "Customer": st.column_config.TextColumn("Customer", width="medium"),
            "Region": st.column_config.TextColumn("Region", width="small"),
            "Last Seen": st.column_config.TextColumn("Last Seen", width="medium"),
            "Needs Update": st.column_config.TextColumn("Needs Update", width="large"),
        }
    )

    # Expander for detailed view of a specific dock
    with st.expander("View Dock Component Details"):
        if len(filtered_df) > 0:
            selected_serial = st.selectbox(
                "Select a dock to view details",
                filtered_df['serial'].tolist(),
                key="dock_detail_select"
            )

            if selected_serial:
                dock = filtered_df[filtered_df['serial'] == selected_serial].iloc[0]

                st.markdown("#### Greengrass Components")
                gg_cols = st.columns(2)
                with gg_cols[0]:
                    st.markdown(f"**BLE:** {dock.get('ble_version', 'N/A')}")
                    st.markdown(f"**Device Manager:** {dock.get('device_manager_component_version', 'N/A')}")
                    st.markdown(f"**Power:** {dock.get('power_component_version', 'N/A')}")
                with gg_cols[1]:
                    st.markdown(f"**Raw File Upload:** {dock.get('raw_file_upload_version', 'N/A')}")
                    st.markdown(f"**Retriever:** {dock.get('retriever_version', 'N/A')}")

                st.markdown("#### Dock Image Components")
                di_cols = st.columns(2)
                with di_cols[0]:
                    st.markdown(f"**PMU:** {dock.get('pmu_version', 'N/A')}")
                    st.markdown(f"**Device:** {dock.get('device_version', 'N/A')}")
                with di_cols[1]:
                    st.markdown(f"**Dock Image:** {dock.get('dock_image_version', 'N/A')}")
                    st.markdown(f"**Dock PMU:** {dock.get('dock_pmu_version', 'N/A')}")
