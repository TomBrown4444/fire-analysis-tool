def create_gif_from_frames(frames, fps=2):
    """
    Create a GIF from HTML frames with properly loaded satellite imagery and visible fire points.
    Ensures the correct location is preserved from the original map.
    
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
        import json
        
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
            
            # Extract centerpoint and zoom level from the HTML
            # Look for the fitBounds function call which contains the geographic bounds
            bounds_pattern = r'\.fitBounds\(\[\[([0-9.-]+),\s*([0-9.-]+)\],\s*\[([0-9.-]+),\s*([0-9.-]+)\]\]'
            bounds_match = re.search(bounds_pattern, html_content)
            
            # Default bounds for Afghanistan if we can't find the bounds
            min_lat, min_lon, max_lat, max_lon = 33.0, 60.0, 38.0, 75.0
            
            if bounds_match:
                min_lat = float(bounds_match.group(1))
                min_lon = float(bounds_match.group(2))
                max_lat = float(bounds_match.group(3))
                max_lon = float(bounds_match.group(4))
            
            # Extract latitude/longitude points from the original HTML
            # Try multiple patterns to find the fire points
            # Pattern 1: Look for CircleMarker with location attribute
            lat_lon_pattern1 = r'location=\[\s*([0-9.-]+)\s*,\s*([0-9.-]+)\s*\]'
            matches1 = re.findall(lat_lon_pattern1, html_content)
            
            # Pattern 2: Look for CircleMarker style formatting with fill_color='#ff3300'
            # This targets specifically fire points
            fire_marker_section = re.search(r'fill_color=[\'"]#ff3300[\'"].*?location=\[\s*([0-9.-]+)\s*,\s*([0-9.-]+)\s*\]', 
                                          html_content, re.DOTALL)
            if fire_marker_section:
                # Extract all locations that follow this pattern
                fire_section = html_content[fire_marker_section.start():]
                lat_lon_pattern2 = r'location=\[\s*([0-9.-]+)\s*,\s*([0-9.-]+)\s*\]'
                matches2 = re.findall(lat_lon_pattern2, fire_section)
            else:
                matches2 = []
            
            # Pattern 3: Generic coordinate pattern as a fallback
            # This will match any [lat, lon] patterns in the HTML
            lat_lon_pattern3 = r'\[\s*([0-9.-]+)\s*,\s*([0-9.-]+)\s*\]'
            matches3 = re.findall(lat_lon_pattern3, html_content)
            
            # Filter out matches that aren't likely to be coordinates
            valid_matches3 = []
            for lat, lon in matches3:
                try:
                    lat_f = float(lat)
                    lon_f = float(lon)
                    if -90 <= lat_f <= 90 and -180 <= lon_f <= 180:
                        valid_matches3.append((lat, lon))
                except ValueError:
                    continue
            
            # Start with the most specific patterns and fall back to more general ones
            if matches1:
                matches = matches1
                st.write(f"Found {len(matches)} points using pattern 1")
            elif matches2:
                matches = matches2
                st.write(f"Found {len(matches)} points using pattern 2")
            elif valid_matches3:
                matches = valid_matches3
                st.write(f"Found {len(matches)} points using pattern 3")
            else:
                matches = []
                st.warning("Could not find fire points in the HTML")
            
            # Filter the points based on the extracted bounds to ensure they're in the correct area
            # This helps eliminate false positives
            filtered_matches = []
            for lat, lon in matches:
                try:
                    lat_f = float(lat)
                    lon_f = float(lon)
                    # Allow a slight buffer beyond the bounds (2 degrees)
                    buffer = 2.0
                    if (min_lat - buffer <= lat_f <= max_lat + buffer and 
                        min_lon - buffer <= lon_f <= max_lon + buffer):
                        filtered_matches.append((lat, lon))
                except ValueError:
                    continue
            
            matches = filtered_matches
            
            # Log the number of points found after filtering
            st.write(f"Found {len(matches)} fire points in viewport")
            
            # Calculate center point and zoom level
            center_lat = (min_lat + max_lat) / 2
            center_lon = (min_lon + max_lon) / 2
            
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
                        center: [{center_lat}, {center_lon}],
                        zoom: 10,  // Default zoom level
                        attributionControl: false
                    }});
                    
                    // Add satellite layer
                    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                        attribution: 'Satellite Imagery'
                    }}).addTo(map);
                    
                    // Define bounds for the map view
                    const southWest = L.latLng({min_lat}, {min_lon});
                    const northEast = L.latLng({max_lat}, {max_lon});
                    const bounds = L.latLngBounds(southWest, northEast);
                    
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
                static_html += f"        [{center_lat}, {center_lon}],  // Default point if none found\n"
            
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
                    
                    // Fit bounds to the defined bounds with padding
                    map.fitBounds(bounds, {padding: [50, 50]});
                    
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
                
                # Draw backup points directly on the image for redundancy
                if matches and img_width > 100 and img_height > 100:
                    # Adjusted function to convert geo coordinates to pixel coordinates
                    def geo_to_pixel(lat, lon):
                        # Calculate percentage position within the bounds
                        x_percent = (float(lon) - min_lon) / (max_lon - min_lon)
                        # For latitude, we need to invert the percentage since pixel y increases downward
                        y_percent = 1.0 - (float(lat) - min_lat) / (max_lat - min_lat)
                        
                        # Apply padding (50 pixels)
                        padding = 50
                        x = padding + x_percent * (img_width - 2 * padding)
                        y = padding + y_percent * (img_height - 2 * padding)
                        
                        return x, y
                    
                    # Draw each point as a circle
                    for lat, lon in matches:
                        x, y = geo_to_pixel(lat, lon)
                        
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