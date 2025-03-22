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
    
    # Calculate the bounding box for auto-zoom
    min_lat = data[lat_col].min()
    max_lat = data[lat_col].max()
    min_lon = data[lon_col].min()
    max_lon = data[lon_col].max()
    
    # Always use satellite by default
    initial_tiles = 'https://stamen-tiles-{s}.a.ssl.fastly.net/terrain/{z}/{x}/{y}.jpg'
    tile_attr = 'Default Satellite Basemap'
    
    # Only use different basemap if explicitly specified
    if basemap != 'Satellite' and basemap in basemap_tiles:
        initial_tiles = basemap_tiles[basemap]
    
    # Create a map with fixed zoom and the selected basemap
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=fixed_zoom,
        tiles=initial_tiles,
        attr=tile_attr
    )
    
    # Add the actual required attribution in a more discreet way
    attribution_css = """
    <style>
    .leaflet-control-attribution {
        font-size: 8px !important;
        background-color: rgba(0,0,0,0.5) !important;
        color: #ddd !important;
        padding: 0 5px !important;
        bottom: 0 !important;
        right: 0 !important;
        position: absolute !important;
    }
    </style>
    """
    m.get_root().html.add_child(folium.Element(attribution_css))
    
    # Fit bounds to ensure all points are visible
    m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]], padding=(50, 50))
    
    # Add title with clean styling
    title_html = f'''
    <style>
        .leaflet-container {{ 
            margin-top: 0 !important; 
            padding-top: 0 !important;
        }}
        .map-title {{ 
            position: absolute; 
            z-index: 999; 
            left: 50%; 
            transform: translateX(-50%);
            background-color: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            margin-top: 10px;
        }}
        
        /* Remove any whitespace */
        body, html {{
            margin: 0;
            padding: 0;
            height: 100%;
            overflow: hidden;
        }}
        
        /* Make map container fill entire frame */
        #map {{
            height: 100vh !important;
            width: 100vw !important;
            position: absolute;
            top: 0;
            left: 0;
        }}
    </style>
    <div class="map-title"><b>{title}</b></div>
    '''
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
    
    # Save to HTML string with additional fixes for export
    html_string = m._repr_html_()
    
    # Fix any remaining issues in the HTML that could cause whitespace
    html_string = html_string.replace('<body>', '<body style="margin:0; padding:0; overflow:hidden;">')
    
    return html_string

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
    Create a GIF from HTML frames with properly loaded satellite imagery and visible fire points.
    
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
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        from webdriver_manager.chrome import ChromeDriverManager
        from PIL import Image, ImageDraw
        import tempfile
        import os
        import time
        import streamlit as st
        from io import BytesIO
        import re
        
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        screenshot_paths = []
        
        # Set up Chrome with larger window size
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1280,960")  # Larger window size
        
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
            
            # Extract the title to use in the static map
            title_match = re.search(r'<div class="map-title"><b>(.*?)</b></div>', html_content)
            title = title_match.group(1) if title_match else f"Fire Map - Frame {i+1}"
            
            # Extract latitude/longitude points from the original HTML
            # Look for CircleMarker patterns in the HTML
            lat_lon_pattern = r'location=\[\s*([0-9.-]+)\s*,\s*([0-9.-]+)\s*\]'
            matches = re.findall(lat_lon_pattern, html_content)
            
            # Check if we found any points
            if not matches:
                # Try an alternative pattern that might be in the HTML
                lat_lon_pattern = r'\[\s*([0-9.-]+)\s*,\s*([0-9.-]+)\s*\]'
                matches = re.findall(lat_lon_pattern, html_content)
                
                # Filter out matches that aren't likely to be coordinates
                matches = [(lat, lon) for lat, lon in matches 
                          if -90 <= float(lat) <= 90 and -180 <= float(lon) <= 180]
            
            # Log the number of points found for debugging
            st.write(f"Found {len(matches)} fire points in frame {i+1}")
            
            # Create a static map HTML that will definitely load
            static_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css"/>
                <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
                <style>
                    body, html {{
                        margin: 0;
                        padding: 0;
                        width: 100%;
                        height: 100%;
                        overflow: hidden;
                        background-color: #000;
                    }}
                    #map {{
                        position: absolute;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        z-index: 1;
                    }}
                    .title-overlay {{
                        position: absolute;
                        top: 10px;
                        left: 50%;
                        transform: translateX(-50%);
                        background-color: rgba(0, 0, 0, 0.7);
                        color: white;
                        padding: 5px 15px;
                        border-radius: 5px;
                        z-index: 2;
                        font-family: Arial, sans-serif;
                        font-size: 16px;
                        font-weight: bold;
                    }}
                    /* Hide attribution text */
                    .leaflet-control-attribution {{
                        display: none !important;
                    }}
                </style>
            </head>
            <body>
                <div id="map"></div>
                <div class="title-overlay">{title}</div>
                
                <script>
                    // Create a map with satellite imagery
                    const map = L.map('map', {{
                        center: [34.0, 65.0], // Default center (will be adjusted)
                        zoom: 6,
                        attributionControl: false
                    }});
                    
                    // Add satellite layer
                    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                        attribution: 'Satellite Imagery'
                    }}).addTo(map);
                    
                    // Add fire points as circle markers
                    const pointGroup = L.featureGroup();
                    
                    // Fire point locations
                    const firePoints = [
            """
            
            # Add each coordinate as a JavaScript array
            for lat, lon in matches:
                static_html += f"        [{lat}, {lon}],\n"
            
            # If no points were found, add a dummy point to avoid JavaScript errors
            if not matches:
                static_html += "        [34.0, 65.0],  // Default point if none found\n"
            
            static_html += """
                    ];
                    
                    // Add each point to the map
                    firePoints.forEach(point => {
                        L.circleMarker(point, {
                            radius: 8,  // Larger radius for better visibility
                            color: 'white',
                            weight: 2,
                            fillColor: '#ff3300',
                            fillOpacity: 1.0,  // Full opacity for better visibility
                        }).addTo(pointGroup);
                    });
                    
                    // Add the points to the map
                    pointGroup.addTo(map);
                    
                    // Fit bounds to see all points
                    if (firePoints.length > 0) {
                        map.fitBounds(pointGroup.getBounds(), {padding: [50, 50]});
                    }
                    
                    // Signal that map is ready after tiles load
                    map.whenReady(() => {
                        // First wait for the map to be ready
                        setTimeout(() => {
                            // Then wait even longer for tiles
                            document.body.classList.add('map-loaded');
                        }, 5000); // Extra delay to ensure tiles load
                    });
                </script>
            </body>
            </html>
            """
            
            # Save the HTML to a file
            html_path = os.path.join(temp_dir, f"frame_{i}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(static_html)
            
            # Load the HTML in the browser
            driver.get(f"file://{html_path}")
            
            # Wait for map to be fully loaded
            try:
                # Wait longer to ensure tiles load
                time.sleep(8)  # Increased wait time
                
                # Ensure the map container exists and is visible
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "map"))
                )
                
                # Take screenshot
                screenshot_path = os.path.join(temp_dir, f"frame_{i}.png")
                driver.save_screenshot(screenshot_path)
                
                # Process the screenshot to ensure fire points are visible
                # This adds a backup solution in case the JavaScript markers don't render
                image = Image.open(screenshot_path)
                draw = ImageDraw.Draw(image)
                
                # Get image dimensions
                img_width, img_height = image.size
                
                # If we have valid points and the image seems to have loaded correctly
                # Convert lat/lon to approximate pixel coordinates
                if matches and img_width > 100 and img_height > 100:
                    # First find the bounding box of points
                    lats = [float(lat) for lat, _ in matches]
                    lons = [float(lon) for _, lon in matches]
                    min_lat, max_lat = min(lats), max(lats)
                    min_lon, max_lon = min(lons), max(lons)
                    
                    # Adjust for padding (similar to the leaflet fitBounds padding)
                    padding = 50
                    lat_range = max_lat - min_lat
                    lon_range = max_lon - min_lon
                    min_lat -= lat_range * padding / img_height
                    max_lat += lat_range * padding / img_height
                    min_lon -= lon_range * padding / img_width
                    max_lon += lon_range * padding / img_width
                    
                    # Draw each point as a circle
                    for lat, lon in matches:
                        # Convert lat/lon to pixel coordinates
                        lat_f = float(lat)
                        lon_f = float(lon)
                        
                        # Linear interpolation from geographic to pixel coordinates
                        x = (lon_f - min_lon) / (max_lon - min_lon) * img_width
                        y = (max_lat - lat_f) / (max_lat - min_lat) * img_height
                        
                        # Draw a filled circle with border
                        radius = 8  # Larger radius for better visibility
                        draw.ellipse((x-radius, y-radius, x+radius, y+radius), 
                                    fill='#ff3300', outline='white')
                
                # Save the image with drawn points
                image.save(screenshot_path)
                
                screenshot_paths.append(screenshot_path)
            except Exception as e:
                st.warning(f"Issue with frame {i+1}: {str(e)}")
                # Try to take screenshot anyway
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
        import traceback
        st.error(traceback.format_exc())
        return None