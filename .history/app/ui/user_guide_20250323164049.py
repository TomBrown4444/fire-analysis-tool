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
# User Guide

## About This Tool

The Fire Investigation Tool provides near real-time monitoring and analysis of global fire activity using satellite data from NASA. This tool allows researchers, journalists and open-source investigators to track and analyze fires anywhere in the world.

## Data Source

This application uses data from NASA's Fire Information for Resource Management System (FIRMS), which distributes near real-time active fire data within three hours of satellite observation. The data comes from several satellite instruments:

- **MODIS (Moderate Resolution Imaging Spectroradiometer)** instruments aboard NASA's Terra and Aqua satellites
- **VIIRS (Visible Infrared Imaging Radiometer Suite)** instruments on the NOAA-20, NOAA-21, and Suomi NPP satellites

These satellites orbit the Earth and pass over most locations once per day, capturing thermal anomalies that indicate fires, flares, and other heat sources on the Earth's surface.

## How To Use This Tool

### Basic Operation

1. **Select a Country**: Choose the country you want to monitor from the dropdown menu. (Many fires will appear outside a country's borders, but you can restrict the results by selecting 'Strict Country Filtering' under the 'Advanced Clustering Settings' tab.)
2. **Select Datasets**: Choose which satellite datasets to use (VIIRS NOAA-20, VIIRS SNPP, MODIS). 
3. **Select Category**: Choose between fires, flares, or raw data. (Flares are industrial heat sources, while raw data includes all thermal anomalies. There may be some overlap between 'fires' and 'flares'.)
4. **Select Date Range**: Set your desired monitoring period.
5. **Advanced Settings** (Optional): Adjust clustering parameters for more precise analysis. (A 'cluster' is essentially a fire identified using machine learning algorithims. For most users, the default settings will work well.)
6. **Click "Generate Analysis"**: Process the data and create visualizations.

### Notes

- If you're looking for a specific fire and it's not showing up within the date range, try adjusting the clustering parameters or using 'raw data'.

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

## Contact details

- The tool was made by investigative journalist Tom Brown as part of the Bellingcat Technology Fellowship. If you find a problem with it or would like to share tips or story ideas, please contact him at: tom.brown_journalist@outlook.com
"""

