"""
Main Streamlit app for the Fire Analysis Tool.
Entry point for the application that integrates all components.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import traceback

# Import core modules
from app.core.firms_handler import FIRMSHandler
from app.core.analysis import create_cluster_summary, display_feature_exploration, display_coordinate_view, has_multiple_dates
from app.core.utils import clear_stale_state, handle_url_parameters, get_category_display_name, get_category_singular

# Import UI modules
from app.ui.map import plot_fire_detections_folium
from app.ui.sidebar import render_sidebar_content
from app.ui.timeline import export_timeline, create_arrow_navigation
from app.ui.utils import setup_page_config, create_custom_sidebar_js, move_content_to_sidebar_js, custom_css
from app.ui.user_guide import USER_GUIDE_MARKDOWN

# Import settings
from app.config.settings import (
    COUNTRY_BBOXES,
    US_STATE_BBOXES, 
    DATASET_START_DATES, 
    BASEMAP_TILES, 
    LARGE_COUNTRIES,
    DEFAULT_FIRMS_USERNAME,
    DEFAULT_FIRMS_PASSWORD,
    DEFAULT_FIRMS_API_KEY,
    DEFAULT_DOT_SIZE_MULTIPLIER,
    DEFAULT_COLOR_PALETTE,
    DEFAULT_BASEMAP,
    DEFAULT_EPS,
    DEFAULT_MIN_SAMPLES
)

def main():
    """Main function to run the Streamlit app."""
    try:
        # Set up page configuration - MUST BE FIRST STREAMLIT COMMAND
        setup_page_config()
        
        # Clean up stale state
        clear_stale_state()
        
        # Apply custom CSS
        st.markdown(custom_css(), unsafe_allow_html=True)
        
        # Title and description
        st.title("Fire Analysis Tool")
        st.markdown("---")
        
        # Add User Guide
        with st.expander("📖 User Guide & About", expanded=False):
            st.markdown(USER_GUIDE_MARKDOWN, unsafe_allow_html=True)
            
        # Initialize session state for results and selected cluster
        if 'results' not in st.session_state:
            st.session_state.results = None
        if 'selected_cluster' not in st.session_state:
            st.session_state.selected_cluster = None
        # Add session state variables for playback functionality
        if 'playback_mode' not in st.session_state:
            st.session_state.playback_mode = False
        if 'playback_dates' not in st.session_state:
            st.session_state.playback_dates = []
        if 'playback_index' not in st.session_state:
            st.session_state.playback_index = 0
            
        # Check for cluster ID in URL parameters
        cluster_id = None
        if 'selected_cluster' in st.query_params:
            try:
                cluster_id = int(st.query_params['selected_cluster'])
                del st.query_params['selected_cluster']
            except (ValueError, TypeError):
                if 'selected_cluster' in st.query_params:
                    del st.query_params['selected_cluster']
        
        # Create a two-column layout for the main interface
        main_cols = st.columns([1, 3])
        
        with main_cols[0]:
            # Analysis Settings Section
            st.subheader("Analysis Settings")
            
            # Country selection
            st.write("Please select your country")
            country = st.selectbox(
                "Please select",
                list(COUNTRY_BBOXES.keys())
            )
            
            # Add state selection when USA is selected
            selected_state = None
            if country == "United States":
                st.write("Please select a state or 'All States'")
                selected_state = st.selectbox(
                    "Select state",
                    list(US_STATE_BBOXES.keys())
                )
            
            if country == "United States" and state and state != "All States":
                from app.config.settings import US_STATE_BBOXES
                bbox = US_STATE_BBOXES.get(state, None)
                st.info(f"Using bounding box for {state}: {bbox}")
            
            # Dataset selection - checkboxes
            st.subheader("Select Datasets")
            
            datasets = {}
            datasets['VIIRS_NOAA20_NRT'] = st.checkbox("VIIRS NOAA-20", value=True)
            datasets['VIIRS_SNPP_NRT'] = st.checkbox("VIIRS SNPP", value=True)
            datasets['MODIS_NRT'] = st.checkbox("MODIS", value=True)
            
            # Determine which datasets are selected
            selected_datasets = [ds for ds, is_selected in datasets.items() if is_selected]
            if selected_datasets:
                dataset = selected_datasets[0]  # Use the first selected dataset
            else:
                st.warning('Please select at least one dataset')
                dataset = None
            
            # Category selection
            st.subheader("Select Category")
            category = st.selectbox(
                "Thermal Detection Type",
                ["fires", "flares", "raw data"],
                key="category_select",
                help="""
                Fires: Temperature > 300K, FRP > 1.0 (VIIRS) or Confidence > 80% (MODIS)
                Gas Flares: Temperature > 1000K, typically industrial sources
                Volcanic Activity: Temperature > 1300K, clustered near known volcanic regions
                Raw Data: All data points including noise points not assigned to clusters
                """
            )
                   
            # Handle cluster selection from URL parameters
            if cluster_id is not None and 'results' in st.session_state and st.session_state.results is not None:
                if st.session_state.get('selected_cluster') != cluster_id:
                    # This is from the map, so enable playback mode
                    st.session_state.selected_cluster = cluster_id
                    
                    # Get unique dates
                    cluster_points = st.session_state.results[st.session_state.results['cluster'] == cluster_id]
                    unique_dates = sorted(cluster_points['acq_date'].unique())
                    
                    # Store the dates
                    st.session_state.playback_dates = unique_dates
                    st.session_state.playback_index = 0
                    
                    # Enable playback mode for map selections
                    st.session_state.playback_mode = True
                    
                    # Update dropdown if it exists
                    if 'cluster_options' in st.session_state:
                        cluster_name = f"{get_category_display_name(category)} {cluster_id}"
                        if cluster_name in st.session_state['cluster_options']:
                            st.session_state.cluster_select = cluster_name
                    
                    # Rerun
                    st.rerun()
            
            # Date range selection
            st.subheader("Select Date Range")
            default_end_date = datetime.now()
            default_start_date = default_end_date - timedelta(days=7)
            
            date_cols = st.columns(2)
            
            with date_cols[0]:
                start_date = st.date_input(
                    "Start Date",
                    value=default_start_date,
                    max_value=default_end_date
                )
            
            with date_cols[1]:
                end_date = st.date_input(
                    "End Date",
                    value=default_end_date,
                    min_value=start_date,
                    max_value=default_end_date
                )
            
            # Calculate date range in days
            date_range_days = (end_date - start_date).days
            
            # Show warning for large countries with wide date ranges
            # In main.py where you show the warning
            if country in LARGE_COUNTRIES and country != "United States" and date_range_days > 14:
                st.warning(f"⚠️ You selected a {date_range_days}-day period for {country}, which is a large country.")
            elif country == "United States" and selected_state == "All States" and date_range_days > 14:
                st.warning(f"⚠️ You selected a {date_range_days}-day period for all of {country}.")
            
            # API credentials (hidden in expander)
            with st.expander("API Settings"):
                username = st.text_input("FIRMS Username", value=DEFAULT_FIRMS_USERNAME)
                password = st.text_input("FIRMS Password", value=DEFAULT_FIRMS_PASSWORD, type="password")
                api_key = st.text_input("FIRMS API Key", value=DEFAULT_FIRMS_API_KEY)
            
            # Clustering parameters (hidden in expander)
            with st.expander("Advanced Clustering Settings"):
                # Two-column layout for clustering parameters
                clust_cols = st.columns(2)
                
                with clust_cols[0]:
                    eps = st.slider("Spatial Proximity (eps)", 0.005, 0.05, value=0.01, step=0.001, 
                                   help="DBSCAN eps parameter. Higher values create larger clusters.")
                
                with clust_cols[1]:
                    min_samples = st.slider("Minimum Points", 3, 15, value=5, step=1,
                                          help="Minimum points required to form a cluster.")
                    
                use_clustering = st.checkbox("Use Clustering", value=True, 
                                           help="Group nearby detections into clusters for easier analysis.")
                                        
                # Add time-based clustering parameter
                max_time_diff = st.slider("Max Days Between Events (Same Cluster)", 1, 10, value=5, step=1,
                                help="Maximum days between fire events to be considered same cluster.")
        
                show_multiday_only = st.checkbox("Show only multi-day fires", value=False,
                                help="Filter to show only fires that span multiple days")
                
                # Add the new toggle for strict country filtering (OFF by default)
                use_strict_country_filtering = st.checkbox("Strict country filtering", value=False,
                                help="Filter points to only those within exact country borders instead of rectangular bounding box")
            
            # Generate button
            generate_button = st.button("Generate Analysis", key="generate_button", use_container_width=True)
            
            # Add logic to check if we should proceed with analysis
            proceed_with_analysis = dataset is not None
            
            if generate_button and proceed_with_analysis:
                with st.spinner("Analyzing fire data..."):
                    handler = FIRMSHandler(username, password, api_key)
                    
                    # Determine if we need to pass state parameter
                    if country == "United States" and selected_state and selected_state != "All States":
                        results = handler.fetch_fire_data(
                            country=country,
                            state=selected_state,
                            dataset=dataset,
                            category=category,
                            start_date=start_date,
                            end_date=end_date,
                            use_clustering=use_clustering,
                            eps=eps,
                            min_samples=min_samples,
                            chunk_days=7,
                            max_time_diff_days=max_time_diff,
                            use_strict_country_filtering=use_strict_country_filtering
                        )
                    else:
                        results = handler.fetch_fire_data(
                            country=country,
                            dataset=dataset,
                            category=category,
                            start_date=start_date,
                            end_date=end_date,
                            use_clustering=use_clustering,
                            eps=eps,
                            min_samples=min_samples,
                            chunk_days=7,
                            max_time_diff_days=max_time_diff,
                            use_strict_country_filtering=use_strict_country_filtering
                        )
                    
                    # MULTI-DAY FILTERING CODE
                    if show_multiday_only and results is not None and not results.empty:
                        # Standardize column names for date (add this)
                        if 'Date' in results.columns and 'acq_date' not in results.columns:
                            results['acq_date'] = results['Date']
                        elif 'date' in results.columns and 'acq_date' not in results.columns:
                            results['acq_date'] = results['date']
                        
                        # Debug information - before filtering
                        all_clusters = results[results['cluster'] >= 0]['cluster'].unique()
                        st.write(f"Found {len(all_clusters)} clusters before filtering")
                        
                        # Count days per cluster
                        cluster_days = results[results['cluster'] >= 0].groupby('cluster')['acq_date'].nunique()
                        
                        # More detailed information
                        for cluster_id, day_count in cluster_days.items():
                            dates = sorted(results[results['cluster'] == cluster_id]['acq_date'].unique())
                            date_range = f"{dates[0]} to {dates[-1]}" if len(dates) > 1 else dates[0]
                            st.write(f"Cluster {cluster_id}: {day_count} days ({date_range})")
                        
                        # Get multi-day clusters
                        multiday_clusters = cluster_days[cluster_days > 1].index.tolist()
                        
                        # Filter results to keep only multi-day clusters
                        if multiday_clusters:
                            multi_day_mask = results['cluster'].isin(multiday_clusters)
                            filtered_results = results[multi_day_mask].copy()
                            st.success(f"✓ Filtered to {len(multiday_clusters)} clusters that span multiple days")
                            results = filtered_results
                        else:
                            st.warning("⚠ No multi-day fire clusters found. Try adjusting clustering parameters or date range.")

                        if not multiday_clusters:
                            st.warning("⚠ No multi-day fire clusters found. The clustering algorithm didn't find any fires spanning multiple days. Try increasing the 'Max Days Between Events' slider or adjust the 'Spatial Proximity' value.")
                    
                    # Store results in session state
                    st.session_state.results = results
                    # Reset selected cluster
                    st.session_state.selected_cluster = None
                    # Reset playback mode
                    st.session_state.playback_mode = False
                    
        with main_cols[1]:
            # Define category_display before using it
            category_display = get_category_display_name(category)
            
            # First handle URL parameters
            handle_url_parameters(category)
            
            # Then check for results
            if 'results' in st.session_state and st.session_state.results is not None and not st.session_state.results.empty:
                st.subheader(f"Detection Map")
                
                # Set up variables for map creation
                map_settings = st.session_state.get('map_settings', {
                    'color_palette': DEFAULT_COLOR_PALETTE,
                    'basemap': DEFAULT_BASEMAP,
                    'dot_size_multiplier': DEFAULT_DOT_SIZE_MULTIPLIER
                })
                
                # Check if we're in playback mode
                if not st.session_state.get('playback_mode', False):
                    # NORMAL MODE - Create the folium visualization
                    with st.spinner("Generating map..."):
                        folium_map = plot_fire_detections_folium(
                            st.session_state.results, 
                            f"{category_display} Clusters - {country}", 
                            st.session_state.get('selected_cluster'),
                            category=category,
                            color_palette=map_settings.get('color_palette', DEFAULT_COLOR_PALETTE),
                            dot_size_multiplier=map_settings.get('dot_size_multiplier', DEFAULT_DOT_SIZE_MULTIPLIER)
                        )
                    
                    if folium_map:
                        # Display the folium map
                        html_map = folium_map._repr_html_()
                        components.html(html_map, height=550, width=985)
                        
                        if st.session_state.get('selected_cluster') is not None:
                            if st.button("← Exit Cluster Selection", 
                                        type="primary", 
                                        key="exit_cluster_btn",
                                        use_container_width=True):
                                # Clear the selected cluster
                                st.session_state.selected_cluster = None
                                # Reset playback mode
                                st.session_state.playback_mode = False
                                # Rerun to refresh the UI
                                st.rerun()
                        
                        # If a cluster is selected, show timeline options
                        if st.session_state.get('selected_cluster') is not None:
                            # Check if this cluster has data for multiple dates
                            if has_multiple_dates(st.session_state.results, st.session_state.selected_cluster):
                                st.markdown("---")
                                st.subheader(f"{get_category_display_name(category)} {st.session_state.selected_cluster} Timeline")
                                
                                # Container for timeline buttons
                                timeline_cols = st.columns([1, 1])
                                
                                with timeline_cols[0]:
                                    if st.button("View Timeline", key="view_timeline_btn", use_container_width=True):
                                        # Enable playback mode
                                        st.session_state.playback_mode = True
                                        
                                        # Get unique dates for the selected cluster
                                        cluster_points = st.session_state.results[st.session_state.results['cluster'] == st.session_state.selected_cluster]
                                        unique_dates = sorted(cluster_points['acq_date'].unique())
                                        st.session_state.playback_dates = unique_dates
                                        st.session_state.playback_index = 0
                                        
                                        st.rerun()
                                
                                with timeline_cols[1]:
                                    if st.button("Export Timeline", key="export_timeline_btn", use_container_width=True):
                                        # Get unique dates for the selected cluster
                                        cluster_points = st.session_state.results[st.session_state.results['cluster'] == st.session_state.selected_cluster]
                                        unique_dates = sorted(cluster_points['acq_date'].unique())
                                        
                                        export_timeline(
                                            st.session_state.results, 
                                            st.session_state.selected_cluster,
                                            category,
                                            unique_dates,
                                            BASEMAP_TILES,
                                            map_settings.get('basemap', DEFAULT_BASEMAP)
                                        )
                            else:
                                st.info(f"This {get_category_singular(category)} only appears on one date. Timeline features require data on multiple dates.")
                    else:
                        st.warning("No data to display on the map.")
                else:
                    # PLAYBACK MODE - We're in playback mode - get current date
                    playback_dates = st.session_state.get('playback_dates', [])
                    playback_index = st.session_state.get('playback_index', 0)
                    
                    if playback_dates and playback_index < len(playback_dates):
                        current_date = playback_dates[playback_index]
                        
                        # Create the playback visualization
                        playback_title = f"{category_display} {st.session_state.get('selected_cluster')} - {current_date}"
                        
                        # PRE-FILTER the data to only include the selected cluster
                        cluster_filtered_results = st.session_state.results[
                            st.session_state.results['cluster'] == st.session_state.get('selected_cluster')
                        ].copy()
                        
                        folium_map = plot_fire_detections_folium(
                            cluster_filtered_results,  # ONLY pass the pre-filtered data
                            playback_title,
                            st.session_state.get('selected_cluster'),
                            True,
                            current_date,
                            category=category,
                            color_palette=map_settings.get('color_palette', DEFAULT_COLOR_PALETTE),
                            dot_size_multiplier=map_settings.get('dot_size_multiplier', DEFAULT_DOT_SIZE_MULTIPLIER)
                        )
                        
                        if folium_map:
                            # Save the map to an HTML string and display it using components
                            html_map = folium_map._repr_html_()
                            components.html(html_map, height=550, width=985)
                            
                            # Create timeline navigation
                            st.markdown("---")
                            st.subheader(f"{get_category_display_name(category)} {st.session_state.selected_cluster} Timeline")
                            
                            # Create arrow navigation
                            create_arrow_navigation()
                            
                            # Show feature exploration for the current date
                            if st.session_state.selected_cluster is not None:
                                # Use the updated function with the current date parameter
                                display_feature_exploration(
                                    st.session_state.results, 
                                    st.session_state.selected_cluster, 
                                    category, 
                                    current_date
                                )
                            
                            # Export option
                            if st.button("Export Timeline", key="export_timeline_btn", use_container_width=True):
                                export_timeline(
                                    st.session_state.results, 
                                    st.session_state.selected_cluster,
                                    category,
                                    playback_dates,
                                    BASEMAP_TILES,
                                    map_settings.get('basemap', DEFAULT_BASEMAP)
                                )
                            
                            # Exit playback button
                            if st.button("Exit Timeline View", key="exit_timeline_btn", use_container_width=True):
                                st.session_state.playback_mode = False
                                st.rerun()
                
                # If a cluster is selected, show feature graphs under the map (not in playback mode)
                if st.session_state.get('selected_cluster') is not None and not st.session_state.get('playback_mode', False):
                    # Display feature exploration directly under map
                    display_feature_exploration(st.session_state.results, st.session_state.get('selected_cluster'), category)
                
                # Show coordinate data at the bottom for selected cluster
                if st.session_state.get('selected_cluster') is not None:
                    st.markdown("---")
                    if st.session_state.get('playback_mode', False):
                        playback_dates = st.session_state.get('playback_dates', [])
                        playback_index = st.session_state.get('playback_index', 0)
                        if playback_dates and playback_index < len(playback_dates):
                            display_coordinate_view(st.session_state.results, playback_dates[playback_index])
                    else:
                        display_coordinate_view(st.session_state.results)
            
            # Create a collapsible sidebar for cluster summary table
            # Use HTML/JS for the custom sidebar
            cluster_summary = None
            if 'results' in st.session_state and st.session_state.results is not None and not st.session_state.results.empty:
                cluster_summary = create_cluster_summary(st.session_state.results, category)
            
            # Add the sidebar HTML
            st.components.v1.html(create_custom_sidebar_js(), height=0)
            
            # Create a container for the sidebar content
            sidebar_container = st.container()
            
            # Sidebar content in a hidden div that will be moved to the sidebar by JS
            with st.container():
                # Hide this container visually but keep it in the DOM
                st.markdown('<div id="hidden-sidebar-content" style="display:none">', unsafe_allow_html=True)
                
                if cluster_summary is not None:
                    render_sidebar_content(cluster_summary, category)
                
                # Close the hidden content div
                st.markdown('</div>', unsafe_allow_html=True)
                
            # Add the script to move content
            st.components.v1.html(move_content_to_sidebar_js(), height=0)
            
            # Add script for exit cluster button
            exit_cluster_js = """
            <script>
            // Listen for the exit_cluster_selection event from the folium map
            document.addEventListener('exit_cluster_selection', function(e) {
                // Clear selected cluster in session state
                if (window.parent._stateManagementFunctions && 
                    window.parent._stateManagementFunctions.setSessionState) {
                    window.parent._stateManagementFunctions.setSessionState({
                        selected_cluster: null, 
                        playback_mode: false
                    });
                }
            });
            </script>
            """
            st.components.v1.html(exit_cluster_js, height=0)
            
    except Exception as e:
        st.error(f"Application error: {e}")
        st.error(traceback.format_exc())

if __name__ == "__main__":
    main()