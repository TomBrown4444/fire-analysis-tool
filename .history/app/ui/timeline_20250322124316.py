"""
Timeline components for the Fire Investigation Tool.
Provides functions to create and manage timeline-related functionality.
"""
import streamlit as st
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from app.core.utils import get_category_display_name, get_category_singular
from app.ui.map import create_export_map
from app.config.settings import BASEMAP_TILES

def create_arrow_navigation(key_suffix=""):
    """
    Create arrow navigation buttons and JavaScript for keyboard navigation.
    
    Args:
        key_suffix (str): Suffix for button keys to ensure uniqueness
    """
    # Create button columns for navigation
    col1, col2, col3 = st.columns([1, 4, 1])
    
    with col1:
        prev_key = f"prev_btn_{key_suffix}" if key_suffix else "prev_btn"
        prev_clicked = st.button("◀", key=prev_key, help="Previous Date (Left Arrow)", on_click=None)
        if prev_clicked and st.session_state.get('playback_index', 0) > 0:
            st.session_state.playback_index -= 1
            st.rerun()
    
    with col2:
        playback_dates = st.session_state.get('playback_dates', [])
        playback_index = st.session_state.get('playback_index', 0)
        
        if playback_dates and st.session_state.get('playback_mode', False):
            if playback_index < len(playback_dates):
                current_date = playback_dates[playback_index]
                total_dates = len(playback_dates)
                
                # Date slider
                slider_key = f"date_slider_{key_suffix}" if key_suffix else "date_slider_direct"
                date_index = st.slider(
                    "Select Date", 
                    0, 
                    total_dates - 1, 
                    playback_index,
                    key=slider_key,
                    help="Use slider or arrow buttons to change the date"
                )
                
                # Update index if slider changed
                if date_index != playback_index:
                    st.session_state.playback_index = date_index
                    st.rerun()
                    
                st.write(f"**Current Date: {current_date}** (Day {playback_index + 1} of {total_dates})")
    
    with col3:
        next_key = f"next_btn_{key_suffix}" if key_suffix else "next_btn"
        next_clicked = st.button("▶", key=next_key, help="Next Date (Right Arrow)", on_click=None)
        playback_dates = st.session_state.get('playback_dates', [])
        playback_index = st.session_state.get('playback_index', 0)
        
        if next_clicked and playback_index < len(playback_dates) - 1:
            st.session_state.playback_index += 1
            st.rerun()
    
    # Add JavaScript for keyboard navigation
    js_code = """
    <script>
    document.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowRight') {
            // Find and click the next button
            const nextBtn = document.querySelector('button:contains("▶")');
            if (nextBtn) nextBtn.click();
        } else if (e.key === 'ArrowLeft') {
            // Find and click the previous button
            const prevBtn = document.querySelector('button:contains("◀")');
            if (prevBtn) prevBtn.click();
        }
    });
    </script>
    """
    
    st.components.v1.html(js_code, height=0)
    
def create_export_map(data, title, basemap_tiles, basemap, dot_color='#ff3300', border_color='white', border_width=1.5, fixed_zoom=7):
    """
    Create a simplified map for export with static zoom and custom colors.
    
    Args:
        data (pandas.DataFrame): DataFrame with fire data
        title (str): Map title
        basemap_tiles (dict): Dictionary of basemap tiles
        basemap (str): Basemap name
        dot_color (str): Color of the points
        border_color (str): Color of the point borders
        border_width (float): Width of the point borders
        fixed_zoom (int): Zoom level for the map
        
    Returns:
        str: HTML string representation of the map
    """
    import pandas as pd
    import folium
    import streamlit as st
    
    if data.empty:
        return None
    
    # Find coordinate columns
    lat_col = next((col for col in ['latitude', 'Latitude', 'lat', 'Lat'] if col in data.columns), None)
    lon_col = next((col for col in ['longitude', 'Longitude', 'lon', 'Lon'] if col in data.columns), None)
    
    if not lat_col or not lon_col:
        st.error(f"Cannot find coordinate columns in {data.columns.tolist()}")
        return None
    
    # Calculate center point of data
    center_lat = (data[lat_col].min() + data[lat_col].max()) / 2
    center_lon = (data[lon_col].min() + data[lon_col].max()) / 2
    
    # Get the appropriate tile URL based on basemap selection
    tile_url = basemap_tiles.get(basemap, basemap_tiles['Dark'])
    
    # Create a map with fixed zoom and the selected basemap
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=fixed_zoom,  # Fixed zoom level
        tiles=tile_url
    )
    
    # Add title
    title_html = f'<h3 align="center" style="font-size:16px; color: white;"><b>{title}</b></h3>'
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Add each point with custom colors
    for idx, row in data.iterrows():
        folium.CircleMarker(
            location=[row[lat_col], row[lon_col]],
            radius=6,
            color=border_color,         # Border color
            weight=border_width,        # Border width
            fill=True,
            fill_color=dot_color,       # Fill color
            fill_opacity=0.9
        ).add_to(m)
    
    # Return the HTML
    return m._repr_html_()

def export_timeline(df, cluster_id=None, category="fires", playback_dates=None, basemap_tiles=None, basemap="Dark"):
    """
    Create a timeline export as GIF or MP4.
    
    Args:
        df (pandas.DataFrame): DataFrame with fire data
        cluster_id (int, optional): Specific cluster ID to export. If None, exports all clusters.
        category (str): Category name (fires, flares, etc.)
        playback_dates (list): List of dates to include in playback
        basemap_tiles (dict): Dictionary mapping of basemap names to tile URLs
        basemap (str): Selected basemap name
    """
    import streamlit as st
    from app.core.utils import get_category_display_name, get_category_singular
    
    # Initialize basemap_tiles if not provided
    if basemap_tiles is None:
        basemap_tiles = {
            'Dark': 'cartodbdark_matter',
            'Light': 'cartodbpositron',
            'Satellite': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            'Terrain': 'stamenterrain'
        }
    
    # Filter for the selected cluster(s)
    if cluster_id is not None:
        # Export a single cluster
        export_single_cluster_timeline(df, cluster_id, category, playback_dates, basemap_tiles, basemap)
    else:
        # Export all clusters (multi-cluster visualization)
        export_all_clusters_timeline(df, category, playback_dates, basemap_tiles, basemap)

def export_single_cluster_timeline(df, cluster_id, category, playback_dates, basemap_tiles, basemap):
    """
    Export timeline for a single cluster.
    
    Args:
        df (pandas.DataFrame): DataFrame with fire data
        cluster_id (int): Cluster ID to export
        category (str): Category name (fires, flares, etc.)
        playback_dates (list): List of dates to include in playback
        basemap_tiles (dict): Dictionary mapping of basemap names to tile URLs
        basemap (str): Selected basemap name
    """
    import streamlit as st
    import time
    from app.core.utils import get_category_display_name, get_category_singular
    
    # Get data for the selected cluster
    cluster_data = df[df['cluster'] == cluster_id]
    
    # Group by date and count points
    date_counts = cluster_data.groupby('acq_date').size()
    dates_with_data = list(date_counts.index)
    
    # Check if we have at least 2 dates with data
    if len(dates_with_data) <= 1:
        st.warning(f"This {get_category_singular(category)} only has data for one date. Timeline export requires data on multiple dates.")
        return
    
    # Set up progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Capture frames for each date
    frames = []
    total_dates = len(dates_with_data)
    
    # Custom colors for fire visualization
    dot_color = '#ff3300'  # Red-orange fill
    border_color = 'white'
    
    # Find the bounds of all data to determine a fixed zoom level
    all_lat = []
    all_lon = []
    
    # Find coordinate columns
    lat_col = next((col for col in ['latitude', 'Latitude', 'lat', 'Lat'] if col in cluster_data.columns), None)
    lon_col = next((col for col in ['longitude', 'Longitude', 'lon', 'Lon'] if col in cluster_data.columns), None)
    
    if lat_col and lon_col:
        all_lat = cluster_data[lat_col].tolist()
        all_lon = cluster_data[lon_col].tolist()
    
    for i, date in enumerate(sorted(dates_with_data)):
        status_text.write(f"Processing frame {i+1}/{total_dates}: {date}")
        progress_bar.progress((i+1)/total_dates)
        
        # Create map for this date
        playback_title = f"{get_category_display_name(category)} {cluster_id} - {date}"
        
        # Filter data for this date and cluster
        date_data = df[(df['cluster'] == cluster_id) & (df['acq_date'] == date)].copy()
        
        if not date_data.empty:
            # Create a simplified map for export
            folium_map = create_export_map(
                date_data, 
                playback_title, 
                basemap_tiles, 
                basemap,
                dot_color=dot_color,
                border_color=border_color
            )
            frames.append(folium_map)
    
    status_text.write("Processing complete. Preparing download...")
    
    # Store frames in session state
    st.session_state.frames = frames
    
    # Provide download option
    if frames:
        # Create download buffer
        st.info(f"Timeline export ready for cluster {cluster_id}")
        st.download_button(
            label="Download as GIF",
            data=create_gif_from_frames(frames),
            file_name=f"{category}_{cluster_id}_timeline.gif",
            mime="image/gif",
            key="download_gif_single_btn",
            use_container_width=True
        )
        progress_bar.empty()
        status_text.empty()
    else:
        st.error("Failed to create timeline export - no frames were generated")
        progress_bar.empty()
        status_text.empty()

def export_all_clusters_timeline(df, category, playback_dates, basemap_tiles, basemap):
    """
    Export timeline showing all clusters over time.
    
    Args:
        df (pandas.DataFrame): DataFrame with fire data
        category (str): Category name (fires, flares, etc.)
        playback_dates (list): List of dates to include in playback
        basemap_tiles (dict): Dictionary mapping of basemap names to tile URLs
        basemap (str): Selected basemap name
    """
    import streamlit as st
    import time
    from app.core.utils import get_category_display_name, get_category_singular
    from app.ui.map import create_export_map
    
    # Filter out noise points
    valid_data = df[df['cluster'] >= 0].copy()
    
    if valid_data.empty:
        st.warning("No valid clusters found to export.")
        return
    
    # Identify the correct date column 
    date_col = None
    for possible_name in ['acq_date', 'date', 'Date', 'ACQ_DATE']:
        if possible_name in valid_data.columns:
            date_col = possible_name
            break
    
    if not date_col:
        st.error("❌ No date column found in data")
        return
        
    # Get all unique dates
    dates_with_data = sorted(valid_data[date_col].unique())
    
    # Check if we have at least 2 dates with data
    if len(dates_with_data) <= 1:
        st.warning(f"Data only spans one date. Timeline export requires data on multiple dates.")
        return
    
    # Set up progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Capture frames for each date
    frames = []
    total_dates = len(dates_with_data)
    
    # Custom colors for fire visualization
    dot_color = '#ff3300'  # Red-orange fill
    border_color = 'white'
    
    # Force the basemap to Satellite for export unless explicitly changed by user
    if not basemap or basemap == 'DEFAULT_BASEMAP':
        basemap = 'Satellite'
    
    for i, date in enumerate(dates_with_data):
        status_text.write(f"Processing frame {i+1}/{total_dates}: {date}")
        progress_bar.progress((i+1)/total_dates)
        
        # Create map for this date
        playback_title = f"All {get_category_display_name(category)}s - {date}"
        
        # Filter data for this date across all clusters
        date_data = valid_data[valid_data[date_col] == date].copy()
        
        if not date_data.empty:
            # Create a simplified map for export using the selected basemap
            folium_map = create_export_map(
                date_data, 
                playback_title, 
                basemap_tiles, 
                basemap,
                dot_color=dot_color,
                border_color=border_color
            )
            frames.append(folium_map)
    
    status_text.write("Processing complete. Preparing download...")
    
    # Store frames in session state
    st.session_state.frames = frames
    
    # Provide download option
    if frames:
        # Create download buffer
        st.info(f"Timeline export ready for all clusters")
        st.download_button(
            label="Download as GIF",
            data=create_gif_from_frames(frames),
            file_name=f"{category}_all_clusters_timeline.gif",
            mime="image/gif",
            key="download_gif_all_btn",
            use_container_width=True
        )
        progress_bar.empty()
        status_text.empty()
    else:
        st.error("Failed to create timeline export - no frames were generated")
        progress_bar.empty()
        status_text.empty()

def create_gif_from_frames(frames, fps=2):
    """
    Create a GIF from HTML frames - without individual frame downloads.
    
    Args:
        frames (list): List of HTML frame strings
        fps (int): Frames per second for the GIF
        
    Returns:
        bytes: Binary GIF data
    """
    try:
        # Import required libraries
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        from PIL import Image
        import tempfile
        import os
        import time
        import streamlit as st
        from io import BytesIO
        
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        screenshot_paths = []
        
        # Set up Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1200,800")
        
        st.info("Setting up browser for image capture...")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        
        # Process each frame
        progress_bar = st.progress(0)
        for i, html_content in enumerate(frames):
            st.write(f"Processing frame {i+1}/{len(frames)}")
            progress_bar.progress((i+1)/len(frames))
            
            # Create simplified HTML that ensures no whitespace and proper rendering
            simple_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body, html {{
                        margin: 0;
                        padding: 0;
                        overflow: hidden;
                        width: 100%;
                        height: 100%;
                        background-color: transparent;
                    }}
                    iframe {{
                        border: none;
                        width: 100%;
                        height: 100%;
                    }}
                    .map-container {{
                        position: absolute;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                    }}
                </style>
            </head>
            <body>
                <div class="map-container">
                    {html_content}
                </div>
            </body>
            </html>
            """
            
            # Save to file
            html_path = os.path.join(temp_dir, f"frame_{i}.html")
            with open(html_path, "w") as f:
                f.write(simple_html)
            
            # Load in browser
            driver.get(f"file://{html_path}")
            
            # Add a longer wait to ensure map and tiles are fully loaded
            time.sleep(3)  # Wait for map to render
            
            # Take screenshot
            screenshot_path = os.path.join(temp_dir, f"frame_{i}.png")
            driver.save_screenshot(screenshot_path)
            screenshot_paths.append(screenshot_path)
        
        # Close driver
        driver.quit()
        
        # Create GIF
        images = [Image.open(path) for path in screenshot_paths if os.path.exists(path)]
        if not images:
            raise Exception("No valid screenshots captured")
            
        # Output GIF
        gif_buffer = BytesIO()
        images[0].save(
            gif_buffer,
            format='GIF',
            append_images=images[1:],
            save_all=True,
            duration=1000//fps,
            loop=0
        )
        gif_buffer.seek(0)
        
        # Clean up
        for path in screenshot_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except:
                pass
        
        st.success("GIF created successfully!")
        
        return gif_buffer.getvalue()
        
    except Exception as e:
        st.error(f"Error creating GIF: {str(e)}")
        return None