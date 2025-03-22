"""
Sidebar UI components for the Fire Investigation Tool.
Provides functions to create and manage the sidebar UI.
"""
import streamlit as st
import pandas as pd

from app.core.utils import get_category_display_name, get_category_singular

def render_sidebar_content(cluster_summary, category, playback_date=None):
    """
    Render the sidebar content with cluster selection and details.
    
    Args:
        cluster_summary (pandas.DataFrame): Summary statistics for each cluster
        category (str): Category of data ('fires', 'flares', 'volcanoes', 'raw data')
        playback_date (str, optional): Current date for playback mode
    """
    if cluster_summary is None:
        return
    
    # Allow user to select a cluster from the table
    st.write(f"Select a {get_category_singular(category)} to highlight on the map:")
    cluster_options = [f"{get_category_display_name(category)} {c}" for c in cluster_summary['cluster'].tolist()]
    
    # Store options in session state for syncing with map selection
    st.session_state['cluster_options'] = cluster_options
    
    selected_from_table = st.selectbox(
        f"Select {get_category_singular(category)}",
        ["None"] + cluster_options,
        key="cluster_select"
    )
    
    if selected_from_table != "None":
        cluster_id = int(selected_from_table.split(' ')[-1])
        
        # Check if this is a new selection (different from current)
        if st.session_state.get('selected_cluster') != cluster_id:
            # Store the previous value to compare
            prev_selected = st.session_state.get('selected_cluster')
            st.session_state.selected_cluster = cluster_id
            
            # Get unique dates for the selected cluster
            cluster_points = st.session_state.results[st.session_state.results['cluster'] == st.session_state.selected_cluster]
            unique_dates = sorted(cluster_points['acq_date'].unique())
            
            # Store the dates and initialize to the first one
            st.session_state.playback_dates = unique_dates
            st.session_state.playback_index = 0
            
            # Reset playback mode when selecting a new cluster
            st.session_state.playback_mode = False
            
            # Only rerun if this was a genuinely new selection
            # This prevents the infinite refresh loop
            if prev_selected != cluster_id:
                st.rerun()
    else:
        # If "None" is selected, clear the selected cluster
        if st.session_state.get('selected_cluster') is not None:
            prev_selected = st.session_state.get('selected_cluster')
            st.session_state.selected_cluster = None
            
            # Only rerun if this was a genuinely new selection
            if prev_selected is not None:
                st.rerun()
    
    # Display the cluster table
    # Highlight the selected cluster in the table if one is selected
    if st.session_state.get('selected_cluster') is not None:
        highlight_func = lambda x: ['background-color: rgba(255, 220, 40, 0.6); color: black;' 
                                  if x.name == st.session_state.get('selected_cluster') 
                                  else '' for i in x]
        styled_summary = cluster_summary.style.apply(highlight_func, axis=1)
        st.dataframe(
            styled_summary,
            column_config={
                "cluster": f"{get_category_display_name(category)} ID",
                "Number of Points": st.column_config.NumberColumn(help=f"{get_category_display_name(category)} detections in cluster"),
                "Mean FRP": st.column_config.NumberColumn(format="%.2f"),
                "Total FRP": st.column_config.NumberColumn(format="%.2f"),
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        # Display the normal table without highlighting
        st.dataframe(
            cluster_summary,
            column_config={
                "cluster": f"{get_category_display_name(category)} ID",
                "Number of Points": st.column_config.NumberColumn(help=f"{get_category_display_name(category)} detections in cluster"),
                "Mean FRP": st.column_config.NumberColumn(format="%.2f"),
                "Total FRP": st.column_config.NumberColumn(format="%.2f"),
            },
            hide_index=True,
            use_container_width=True
        )
    
    # Display detailed info for the selected cluster
    display_cluster_details(cluster_summary, category)

def display_cluster_details(cluster_summary, category):
    """
    Display detailed information for the selected cluster.
    
    Args:
        cluster_summary (pandas.DataFrame): Summary statistics for each cluster
        category (str): Category of data ('fires', 'flares', 'volcanoes', 'raw data')
    """
    if st.session_state.get('selected_cluster') is not None:
        cluster_data = cluster_summary[cluster_summary['cluster'] == st.session_state.get('selected_cluster')].iloc[0]
        
        st.markdown("---")
        st.write(f"### {get_category_display_name(category)} {st.session_state.get('selected_cluster')} Details")
        
        # Create two columns for details
        detail_col1, detail_col2 = st.columns(2)
        
        with detail_col1:
            st.write(f"**Detection Points:** {cluster_data['Number of Points']}")
            st.write(f"**Mean Location:** {cluster_data['Mean Latitude']}, {cluster_data['Mean Longitude']}")
            st.write(f"**First Detection:** {cluster_data['First Detection']}")
            st.write(f"**Last Detection:** {cluster_data['Last Detection']}")
        
        with detail_col2:
            st.write(f"**Mean FRP:** {cluster_data['Mean FRP']:.2f}")
            st.write(f"**Total FRP:** {cluster_data['Total FRP']:.2f}")
            if 'Mean Temperature' in cluster_data:
                st.write(f"**Mean Temperature:** {cluster_data['Mean Temperature']:.2f}K")
                st.write(f"**Max Temperature:** {cluster_data['Max Temperature']:.2f}K")
            
            # Add OSM information if available for flares and volcanoes
            if category in ['flares', 'volcanoes'] and 'OSM Matches' in cluster_data:
                st.write(f"**OSM Feature Matches:** {int(cluster_data['OSM Matches'])}")
                if 'Mean OSM Distance (km)' in cluster_data and not pd.isna(cluster_data['Mean OSM Distance (km)']):
                    st.write(f"**Mean OSM Distance:** {cluster_data['Mean OSM Distance (km)']:.2f} km")
        
        # Add a help tooltip
        st.info("""
        **FRP** (Fire Radiative Power) is measured in megawatts (MW) and indicates the intensity of the fire.
        Higher values suggest more intense burning.
        """)
        
        if 'Mean Temperature' in cluster_data:
            st.info("""
            **Temperature coloring**: 
            - Yellow/White indicates the hottest areas (higher temperature)
            - Orange/Red shows medium temperature
            - Purple/Black indicates lower temperature
            """)
            
        # Add OSM explanation if applicable
        if category in ['flares', 'volcanoes'] and 'OSM Matches' in cluster_data:
            if category == 'flares':
                st.info("""
                **OSM Matches** show points within 10km of:
                - Industrial flare stacks
                - Oil and gas facilities
                - Flare headers
                - Other industrial areas tagged in OpenStreetMap
                """)
            elif category == 'volcanoes':
                st.info("""
                **OSM Matches** show points within 10km of:
                - Known volcanoes
                - Volcanic vents
                - Different volcano types (stratovolcano, shield, caldera, etc.)
                - Other geological features tagged in OpenStreetMap
                """)