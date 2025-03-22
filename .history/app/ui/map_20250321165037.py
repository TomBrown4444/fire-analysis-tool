"""
Map visualization components for the Fire Investigation Tool.
Provides functions to create and display interactive maps using folium.
"""
import folium
from folium.plugins import Fullscreen
from branca.colormap import LinearColormap
import streamlit.components.v1 as components
import streamlit as st
import pandas as pd

from app.core.utils import get_temp_column, get_category_display_name
from app.config.settings import BASEMAP_TILES, COLOR_PALETTES

def plot_fire_detections_folium(df, title="Fire Detections", selected_cluster=None, playback_mode=False, playback_date=None, dot_size_multiplier=1.0, color_palette='inferno', category="fires"):
    """
    Plot fire detections on a folium map with color palette based on temperature.
    
    Args:
        df (pandas.DataFrame): DataFrame with fire data
        title (str): Map title
        selected_cluster (int, optional): Selected cluster ID
        playback_mode (bool): Whether playback mode is enabled
        playback_date (str, optional): Current date for playback mode
        dot_size_multiplier (float): Multiplier for marker size
        color_palette (str): Color palette name
        category (str): Category of data ('fires', 'flares', 'volcanoes', 'raw data')
        
    Returns:
        folium.Map: Folium map object
    """
    # Create a working copy of the dataframe
    plot_df = df.copy()
    
    # Filter out noise points (-1) if category is not raw data
    if category != "raw data":
        plot_df = plot_df[plot_df['cluster'] >= 0].copy()
    
    # Apply cluster selection filter if a cluster is selected
    if selected_cluster is not None and selected_cluster in plot_df['cluster'].values:
        # Filter for just the selected cluster
        plot_df = plot_df[plot_df['cluster'] == selected_cluster].copy()
        # Get category display name for title
        category_display = get_category_display_name(category)
        title = f"{title} - {category_display} {selected_cluster}"
    
    # Then apply playback filter if in playback mode
    if playback_mode and playback_date is not None:
        plot_df = plot_df[plot_df['acq_date'] == playback_date].copy()
        title = f"{title} - {playback_date}"
    
    # Check if there is any data to plot
    if plot_df.empty:
        st.warning("No data to plot for the selected filters.")
        # Create an empty map with default center if no data
        m = folium.Map(location=[34.0, 65.0], zoom_start=4, control_scale=True, 
                      tiles='cartodbdark_matter')
        
        # Add information about why map is empty
        empty_info = """
        <div style="position: absolute; 
                    top: 50%; 
                    left: 50%; 
                    transform: translate(-50%, -50%);
                    padding: 20px; 
                    background-color: rgba(0,0,0,0.8); 
                    color: white;
                    z-index: 9999; 
                    border-radius: 5px;
                    text-align: center;">
            <h3>No data points to display</h3>
            <p>The selected filters returned no results.</p>
            <p>Try changing your selection criteria.</p>
        </div>
        """
        
        m.get_root().html.add_child(folium.Element(empty_info))
        return m
    
    # Calculate the bounding box for auto-zoom
    min_lat = plot_df['latitude'].min()
    max_lat = plot_df['latitude'].max()
    min_lon = plot_df['longitude'].min()
    max_lon = plot_df['longitude'].max()
    
    # Create a map centered on the mean coordinates with appropriate zoom
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    
    # Determine which temperature column to use
    temp_col = get_temp_column(plot_df)
    
    # Set the initial tiles based on basemap parameter (defaulting to dark if not specified)
    initial_tiles = 'cartodbdark_matter'
    basemap = st.session_state.get('basemap', 'Dark')
    if basemap in BASEMAP_TILES:
        initial_tiles = BASEMAP_TILES[basemap]
    
    m = folium.Map(location=[center_lat, center_lon], control_scale=True, 
                  tiles=initial_tiles)  # Set the base map from user selection
    
    Fullscreen().add_to(m)
    
    # Automatically zoom to fit all points
    m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]], padding=(50, 50))
    
    # Add a title to the map
    title_html = f'''
             <h3 align="center" style="font-size:16px; color: white;"><b>{title}</b></h3>
             '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Create feature groups for different sets of points
    fg_all = folium.FeatureGroup(name="All Points")
    fg_selected = folium.FeatureGroup(name="Selected Points")
    
    # Get selected color palette
    selected_palette = COLOR_PALETTES.get(color_palette, COLOR_PALETTES['inferno'])
    
    # Create colormap for temperature
    if temp_col:
        vmin = plot_df[temp_col].min()
        vmax = plot_df[temp_col].max()
        colormap = LinearColormap(
            selected_palette,
            vmin=vmin, 
            vmax=vmax,
            caption=f'Temperature (K)'
        )
    
    # Base dot sizes, will be multiplied by the dot_size_multiplier
    base_small_dot = 5 * dot_size_multiplier
    base_medium_dot = 6 * dot_size_multiplier
    base_large_dot = 8 * dot_size_multiplier
    
    # Process data based on selection state
    if selected_cluster is not None and selected_cluster in plot_df['cluster'].values:
        # Split data into selected and unselected
        selected_data = plot_df[plot_df['cluster'] == selected_cluster]
        other_data = plot_df[plot_df['cluster'] != selected_cluster]
        
        # Add unselected clusters if not in playback mode
        if not other_data.empty and not playback_mode:
            for idx, point in other_data.iterrows():
                if temp_col and not pd.isna(point[temp_col]):
                    color = colormap(point[temp_col])
                else:
                    color = '#3186cc'  # Default blue
                
                popup_text = f"""
                <b>Cluster:</b> {point['cluster']}<br>
                <b>Date:</b> {point['acq_date']}<br>
                <b>Time:</b> {point['acq_time']}<br>
                <b>FRP:</b> {point['frp']:.2f}<br>
                <b>Coordinates:</b> {point['latitude']:.4f}, {point['longitude']:.4f}<br>
                """
                if temp_col and not pd.isna(point[temp_col]):
                    popup_text += f"<b>Temperature:</b> {point[temp_col]:.2f}K<br>"
                
                circle = folium.CircleMarker(
                    location=[point['latitude'], point['longitude']],
                    radius=base_small_dot,
                    color='white',  # Use white border for visibility on dark background
                    weight=0.5,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.9,  # Increased opacity for better visibility
                    popup=folium.Popup(popup_text, max_width=300),
                    tooltip=f"Cluster {point['cluster']} - ({point['latitude']:.4f}, {point['longitude']:.4f})"
                )
                
                circle.add_to(fg_all)
        
        # Add selected cluster with different style
        if not selected_data.empty:
            for idx, point in selected_data.iterrows():
                if temp_col and not pd.isna(point[temp_col]):
                    color = colormap(point[temp_col])
                else:
                    color = '#ff3300'  # Default red
                
                popup_text = f"""
                <b>Cluster:</b> {point['cluster']}<br>
                <b>Date:</b> {point['acq_date']}<br>
                <b>Time:</b> {point['acq_time']}<br>
                <b>FRP:</b> {point['frp']:.2f}<br>
                <b>Coordinates:</b> {point['latitude']:.4f}, {point['longitude']:.4f}<br>
                """
                if temp_col and not pd.isna(point[temp_col]):
                    popup_text += f"<b>Temperature:</b> {point[temp_col]:.2f}K<br>"
                
                folium.CircleMarker(
                    location=[point['latitude'], point['longitude']],
                    radius=base_large_dot,
                    color='white',  # White border for visibility
                    weight=1.5,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.9,
                    popup=folium.Popup(popup_text, max_width=300),
                    tooltip=f"Cluster {point['cluster']} - Selected - ({point['latitude']:.4f}, {point['longitude']:.4f})"
                ).add_to(fg_selected)
    else:
        # Add all points with default style
        for idx, point in plot_df.iterrows():
            if temp_col and not pd.isna(point[temp_col]):
                color = colormap(point[temp_col])
            else:
                color = '#3186cc'  # Default blue

            # Create a popup with a URL parameter-based cluster selection
            popup_html = f"""
            <div style="text-align: center;">
                <p><b>Cluster:</b> {point['cluster']}</p>
                <p><b>Date:</b> {point['acq_date']}</p>
                <p><b>Time:</b> {point['acq_time']}</p>
                <p><b>FRP:</b> {point['frp']:.2f}</p>
                <p><b>Coordinates:</b> {point['latitude']:.4f}, {point['longitude']:.4f}</p>
                <a href="?selected_cluster={point['cluster']}" 
                style="display: inline-block; 
                        background-color: #4CAF50; 
                        color: white; 
                        padding: 10px 20px; 
                        border: none; 
                        border-radius: 5px; 
                        cursor: pointer; 
                        text-decoration: none;">
                    Select Cluster {point['cluster']}
                </a>
            </div>
            """
            popup = folium.Popup(popup_html, max_width=300)

            folium.CircleMarker(
                location=[point['latitude'], point['longitude']],
                radius=base_medium_dot,
                color='white',  # White border for visibility
                weight=0.5,
                fill=True,
                fill_color=color,
                fill_opacity=0.9,  # Increased opacity
                popup=popup,
                tooltip=f"Cluster {point['cluster']} - ({point['latitude']:.4f}, {point['longitude']:.4f})"
            ).add_to(fg_all)

    fg_all.add_to(m)
    fg_selected.add_to(m)

    # Add base layers with explicit names
    folium.TileLayer(
        'cartodbpositron', 
        name='Light Map',
        attr='© <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, © <a href="https://carto.com/attribution">CARTO</a>'
    ).add_to(m)

    folium.TileLayer(
        'cartodbdark_matter', 
        name='Dark Map',
        attr='© <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, © <a href="https://carto.com/attribution">CARTO</a>'
    ).add_to(m)

    folium.TileLayer(
        'stamenterrain', 
        name='Terrain Map',
        attr='Map tiles by <a href="http://stamen.com">Stamen Design</a>, under <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by <a href="http://openstreetmap.org">OpenStreetMap</a>, under <a href="http://www.openstreetmap.org/copyright">ODbL</a>.'
    ).add_to(m)

    folium.TileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        name='Satellite',
        attr='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    ).add_to(m)

    # Now add the layer control after all layers are added
    folium.LayerControl(position='topright').add_to(m)

    # If you have a temperature colormap, add it after the layer control
    if temp_col:
        colormap.add_to(m)
    
    folium.LayerControl().add_to(m)
    
    # Add an interaction explanation with instructions to use UI for selection
    info_text = """
    <div style="position: fixed; 
                bottom: 20px; 
                left: 10px; 
                padding: 10px; 
                background-color: rgba(0,0,0,0.7); 
                color: white;
                z-index: 9999; 
                border-radius: 5px;
                max-width: 300px;
                font-size: 12px;">
        <b>Interaction:</b><br>
        • Hover over points to see details<br>
        • Click points to view full information<br>
        • Use the dropdown menu on the right to select clusters<br>
        • Zoom with +/- or mouse wheel<br>
        • Change base maps with layer control (top right)
    </div>
    """
    m.get_root().html.add_child(folium.Element(info_text))
    
    return m

def create_export_map(data, title, basemap_tiles, basemap):
    """
    Create a simplified map for export.
    
    Args:
        data (pandas.DataFrame): DataFrame with fire data
        title (str): Map title
        basemap_tiles (dict): Dictionary of basemap tiles
        basemap (str): Basemap name
        
    Returns:
        str: HTML string representation of the map
    """
    import pandas as pd
    
    if data.empty:
        return None
    
    # Calculate the bounding box
    min_lat = data['latitude'].min()
    max_lat = data['latitude'].max()
    min_lon = data['longitude'].min()
    max_lon = data['longitude'].max()
    
    # Create a map centered on the mean coordinates
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    
    # Set the initial tiles based on basemap
    initial_tiles = 'cartodbdark_matter'
    if basemap in basemap_tiles:
        initial_tiles = basemap_tiles[basemap]
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10, 
                  tiles=initial_tiles)
    
    # Add the title
    title_html = f'''
             <h3 align="center" style="font-size:16px; color: white;"><b>{title}</b></h3>
             '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Plot the points
    for idx, point in data.iterrows():
        folium.CircleMarker(
            location=[point['latitude'], point['longitude']],
            radius=6,
            color='white',
            weight=1.5,
            fill=True,
            fill_color='#ff3300',  # Red for visibility
            fill_opacity=0.9
        ).add_to(m)
    
    # Save to HTML string
    html_string = m._repr_html_()
    return html_string