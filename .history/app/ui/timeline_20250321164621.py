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

def export_timeline(df, cluster_id, category, playback_dates, basemap_tiles, basemap):
    """
    Create a timeline export as GIF or MP4.
    
    Args:
        df (pandas.DataFrame): DataFrame with fire data
        cluster_id (int): Cluster ID to export
        category (str): Category of data ('fires', 'flares', 'volcanoes', 'raw data')
        playback_dates (list): List of dates in the timeline
        basemap_tiles (dict): Dictionary of basemap tiles
        basemap (str): Basemap name
    """
    # Check if we have valid timeline data to export
    if not playback_dates or len(playback_dates) <= 1 or cluster_id is None:
        st.warning(f"No multi-date timeline data available to export. This {get_category_singular(category)} must appear on multiple dates for timeline export.")
        return
    
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
    
    for i, date in enumerate(sorted(dates_with_data)):
        status_text.write(f"Processing frame {i+1}/{total_dates}: {date}")
        progress_bar.progress((i+1)/total_dates)
        
        # Create map for this date
        playback_title = f"{get_category_display_name(category)} {cluster_id} - {date}"
        
        # Filter data for this date and cluster
        date_data = df[(df['cluster'] == cluster_id) & (df['acq_date'] == date)].copy()
        
        if not date_data.empty:
            # Create a simplified map for export
            folium_map = create_export_map(date_data, playback_title, basemap_tiles, basemap)
            frames.append(folium_map)
    
    status_text.write("Processing complete. Preparing download...")
    
    # Store frames in session state
    st.session_state.frames = frames
    
    # Provide download option
    if frames:
        # Create download buffer
        st.info("Timeline export ready for download")
        st.download_button(
            label="Download as GIF",
            data=create_gif_from_frames(frames),
            file_name=f"{category}_{cluster_id}_timeline.gif",
            mime="image/gif",
            use_container_width=True
        )
        progress_bar.empty()
        status_text.empty()
    else:
        st.error("Failed to create timeline export - no frames were generated")
        progress_bar.empty()
        status_text.empty()

def create_gif_from_frames(frames):
    """
    Create a GIF from HTML frames.
    
    Args:
        frames (list): List of HTML frame strings
        
    Returns:
        bytes: Binary GIF data
    """
    # This is a placeholder - in a real implementation, you would:
    # 1. Render each HTML frame to an image
    # 2. Use a library like PIL or imageio to create a GIF
    # 3. Return the binary data of the GIF
    
    frames_pil = []
    for i in range(len(frames)):
        # Create a placeholder image for each frame
        img = Image.new('RGB', (800, 600), color=(30, 30, 30))
        draw = ImageDraw.Draw(img)
        draw.text((400, 300), f"Frame {i+1}/{len(frames)}", fill=(255, 255, 255))
        frames_pil.append(img)
    
    # Save as GIF
    gif_buffer = BytesIO()
    frames_pil[0].save(
        gif_buffer,
        format='GIF',
        append_images=frames_pil[1:],
        save_all=True,
        duration=500,  # 500ms per frame
        loop=0  # Loop forever
    )
    gif_buffer.seek(0)
    return gif_buffer.getvalue()