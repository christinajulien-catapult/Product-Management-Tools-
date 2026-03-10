# Fleet Overview Tool - Project Context

## Overview
A Streamlit dashboard for monitoring Vector Dock fleet health, showing which docks need Greengrass or image component updates.

## How to Run
```bash
cd "/Users/christina.julien/Desktop/Fleet Overview Tool"
streamlit run app.py
```

## Project Structure
```
Fleet Overview Tool/
├── app.py                    # Main Streamlit app with styling
├── requirements.txt          # Dependencies (streamlit, pandas, plotly)
├── assets/
│   └── very_nice.png         # Icon shown when 0% outdated
├── utils/
│   ├── __init__.py
│   ├── data_loader.py        # CSV/TSV loading and region filtering
│   ├── version_utils.py      # Version detection (production/beta) and semver parsing
│   └── metrics.py            # Compliance calculations, component mappings
└── components/
    ├── __init__.py
    ├── metrics_cards.py      # Top 4 metric cards (Total, Active, Compliance, Needs Attention)
    ├── component_table.py    # Component tables with expandable dock lists
    └── dock_details.py       # Full dock details view
```

## Component Mappings (utils/metrics.py)

**Greengrass Components:**
- BLE → `ble_version`
- Device Manager → `device_manager_component_version`
- Power → `power_component_version`
- Raw File Upload → `raw_file_upload_version`
- Retriever → `retriever_version`
- Dock PMU → `dock_pmu_version`
- Dock Image → `dock_image_version`

**Dock Image Components:**
- PMU → `pmu_version`
- APU → `device_version`

## Key Features Implemented

### Version Detection
- **Production**: Versions containing `-production` or short format like `1.0.4+hash`
- **Beta**: Versions containing `-beta`
- Detection in `utils/version_utils.py:detect_version_type()`

### Component Tables
- Shows latest production version, % on latest, % outdated, beta version, % on beta
- Distribution bar (green=production, blue=beta, gray=outdated)
- **Clickable percentages** that expand inline to show affected docks:
  - Red buttons for outdated % (type="primary")
  - Blue buttons for beta % (type="secondary")
- Uses `on_click` callback for reliable state toggling
- Shows "Very Nice!" image when 0% outdated

### Dock Tables (expanded view)
- Columns: Serial, Customer, Region, Last Seen, Time Ago, Version
- Time Ago shows relative time like "2 days 1 hour 34 min"

### Metrics Cards
- Total Docks (with regional breakdown: AU · EU · US)
- Active Docks (seen in last 14 days)
- Fleet Compliance (% with all components on latest)
- Needs Attention (count of docks with outdated components)

### Styling
- Dark theme with gradient backgrounds
- Montserrat font throughout
- 14px table font size
- Custom file uploader with blue "Browse files" button

## Data Requirements
CSV/TSV with columns:
- `region`, `serial`, `customer_name`, `customer_id`
- `last_seen` (datetime)
- Version columns matching the component mappings above
- Optional: `images_up_to_date`, `components_up_to_date`, `components_needs_update`

## Session State Keys
- `loaded_df` - Cached dataframe to persist across button clicks
- `expand_outdated_{table_id}_{idx}` - Expand state for outdated docks
- `expand_beta_{table_id}_{idx}` - Expand state for beta docks

## Recent Changes
1. Fixed expand icon toggle using `on_click` callback
2. Fixed beta counting - now checks version type first before comparing to latest
3. Added count to expanded section titles: "Outdated docks for BLE (8)"
4. Added "Time Ago" column to dock tables
5. Moved PMU, Dock PMU, Dock Image to Greengrass; PMU and APU in Dock Image table
6. Styled main upload screen with gradient and blue button
