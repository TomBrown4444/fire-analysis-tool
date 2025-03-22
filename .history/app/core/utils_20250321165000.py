"""
Utility functions for the Fire Investigation Tool.
Includes helper functions used across the application.
"""

def get_temp_column(df):
    """
    Determine which temperature column to use based on available data.
    
    Args:
        df (pandas.DataFrame): DataFrame with fire data
        
    Returns:
        str: Temperature column name or None if not available
    """
    if df is None:
        return None
        
    if 'bright_ti4' in df.columns:
        return 'bright_ti4'
    elif 'brightness' in df.columns:
        return 'brightness'
    else:
        return None

def get_category_display_name(category):
    """
    Return the display name for a category.
    
    Args:
        category (str): Category name ('fires', 'flares', 'volcanoes', 'raw data')
        
    Returns:
        str: Category display name for UI
    """
    if category == "fires":
        return "Fire"
    elif category == "flares":
        return "Flare"
    elif category == "volcanoes":
        return "Volcano"
    else:
        return "Cluster"  # Default for raw data

def get_category_singular(category):
    """
    Return singular form of category name for UI purposes.
    
    Args:
        category (str): Category name ('fires', 'flares', 'volcanoes', 'raw data')
        
    Returns:
        str: Singular form of category name
    """
    if category == "fires":
        return "fire"
    elif category == "flares":
        return "flare"
    elif category == "volcanoes":
        return "volcano"
    else:
        return "cluster"  # Default for raw data

def clear_stale_state():
    """
    Clean up any stale state that might be causing issues.
    """
    import streamlit as st
    import time
    
    # Check for and clean up potentially problematic session state
    if "processed_params" in st.session_state:
        # Clean up old tracked parameters (older than 10 minutes)
        current_time = time.time()
        keys_to_remove = []
        for key, timestamp in st.session_state.processed_params.items():
            if current_time - timestamp > 600:  # 10 minutes
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del st.session_state.processed_params[key]
    
    # Make sure URL parameters are clean
    if 'selected_cluster' in st.query_params:
        # If any query params were left over from a previous run,
        # clear them for a fresh start
        del st.query_params['selected_cluster']

def handle_url_parameters(category=None):
    """
    Handle URL parameters with auto-playback mode for map selections.
    
    Args:
        category (str, optional): Current category of data
    """
    import streamlit as st
    
    # Check if selected_cluster parameter exists
    if 'selected_cluster' in st.query_params:
        try:
            # Get cluster ID from URL parameters
            cluster_id = int(st.query_params['selected_cluster'])
            
            # Clear the URL parameter immediately to prevent reprocessing
            del st.query_params['selected_cluster']
            
            # Skip further processing if category isn't defined yet
            if category is None or 'results' not in st.session_state or st.session_state.results is None:
                return
                
            # Check if it's a new selection
            if st.session_state.get('selected_cluster') != cluster_id:
                # Update the selected cluster in session state
                st.session_state.selected_cluster = cluster_id
                
                # Get unique dates for the selected cluster
                cluster_points = st.session_state.results[st.session_state.results['cluster'] == cluster_id]
                unique_dates = sorted(cluster_points['acq_date'].unique())
                
                # Store the dates and initialize to the first one
                st.session_state.playback_dates = unique_dates
                st.session_state.playback_index = 0
                
                # Enable playback mode when selecting from map
                st.session_state.playback_mode = True
                
                # Update cluster dropdown to match if it exists
                if 'cluster_select' in st.session_state and 'cluster_options' in st.session_state:
                    cluster_name = f"{get_category_display_name(category)} {cluster_id}"
                    if cluster_name in st.session_state['cluster_options']:
                        st.session_state.cluster_select = cluster_name
                
                # Use a safer rerun approach
                st.rerun()
        except (ValueError, TypeError):
            # Invalid cluster ID, ignore it
            if 'selected_cluster' in st.query_params:
                del st.query_params['selected_cluster']