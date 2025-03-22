def render_user_guide():
    """
    Render the User Guide in an expander component.
    """
    import streamlit as st
    
    with st.expander("📖 User Guide & About", expanded=False):
        st.markdown(USER_GUIDE_MARKDOWN, unsafe_allow_html=True)
        
"""
User Guide module for the Fire Investigation Tool.
Contains the User Guide content in markdown format.
"""

USER_GUIDE_MARKDOWN = """
# Fire Investigation Tool: User Guide

## About This Tool

The Fire Investigation Tool provides near real-time monitoring and analysis of global fire activity using satellite data from NASA. This tool allows researchers, emergency responders, environmental scientists, and concerned citizens to track and analyze fires anywhere in the world.

## Data Source

This application uses data from NASA's Fire Information for Resource Management System (FIRMS), which distributes near real-time active fire data within 3 hours of satellite observation. The data comes from several satellite instruments:

- **MODIS (Moderate Resolution Imaging Spectroradiometer)** instruments aboard NASA's Terra and Aqua satellites
- **VIIRS (Visible Infrared Imaging Radiometer Suite)** instruments on the NOAA-20, NOAA-21, and Suomi NPP satellites

These satellites orbit the Earth and pass over most locations once per day, capturing thermal anomalies that indicate fires, flares, and other heat sources on the Earth's surface.

## How To Use This Tool

### Basic Operation

1. **Select a Country**: Choose the country you want to monitor from the dropdown menu.
2. **Select Datasets**: Choose which satellite datasets to use (VIIRS NOAA-20, VIIRS SNPP, MODIS).
3. **Select Category**: Choose between fires, flares, or raw data.
4. **Select Date Range**: Set your desired monitoring period.
5. **Advanced Settings** (Optional): Adjust clustering parameters for more precise analysis.
6. **Click "Generate Analysis"**: Process the data and create visualizations.

### Analyzing Results

- The map will display fire detections as colored dots, with color indicating temperature.
- Clicking on a specific cluster will provide detailed information about that fire event.
- For multi-day fires, you can use the Timeline feature to track the fire's progression.
- The sidebar provides a comprehensive list of all detected fire clusters.

### Advanced Features

- **Timeline View**: For multi-day fires, track how the fire changes over time.
- **Export Timeline**: Create shareable visualizations of fire progression.
- **Strict Country Filtering**: Toggle between rectangular bounding box and precise country borders.
- **Cluster Analysis**: View detailed statistics on fire intensity, duration, and spread.

## Understanding Fire Clusters

The tool uses machine learning algorithms (specifically DBSCAN clustering) to identify patterns in the thermal detection points. These clusters typically represent:

- **Wildfires**: Natural or human-caused burning of vegetation
- **Agricultural Fires**: Controlled burning for land management
- **Industrial Flares**: Continuous burning at industrial facilities
- **Volcanic Activity**: Heat signatures from volcanic eruptions

By selecting a specific cluster, you can analyze its characteristics such as:
- Fire radiative power (intensity)
- Duration and spread pattern
- Temperature variations
- Geographic extent

## API Information

This tool connects to NASA FIRMS using an API key. The default key belongs to the tool's creator and has usage limitations. For faster performance and higher quotas, you can:

1. Obtain your own free API key from [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/map_key/)
2. Enter your key in the "API Settings" section in the sidebar

## Additional Resources

- [NASA FIRMS Website](https://firms.modaps.eosdis.nasa.gov/)
- [Active Fire Data](https://firms.modaps.eosdis.nasa.gov/active_fire/)
- [Fire Archive Download](https://firms.modaps.eosdis.nasa.gov/download/)

## Technical Notes

- The tool displays country borders using GeoJSON data from Natural Earth.
- Satellite sensors detect thermal anomalies, not just fires (e.g., industrial heat sources).
- Data availability depends on satellite coverage, cloud cover, and processing time.
- Each satellite makes approximately one daytime and one nighttime pass over most locations.
"""