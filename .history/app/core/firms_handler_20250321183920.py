"""
FIRMS API handler for the Fire Investigation Tool.
Provides functionality to fetch and process fire data from NASA's FIRMS API.
"""
import pandas as pd
import requests
import streamlit as st
from io import StringIO
from datetime import datetime, timedelta

from app.core.osm_handler import OSMHandler

class FIRMSHandler:
    """Handler for FIRMS API interactions"""
    
    def __init__(self, username, password, api_key):
        self.username = username
        self.password = password
        self.api_key = api_key
        self.base_url = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.osm_handler = OSMHandler(verbose=False)

    def get_country_bbox(self, country):
        """
        Get bounding box coordinates for a country.
        
        Args:
            country (str): Country name
            
        Returns:
            str: Bounding box string in format "min_lon,min_lat,max_lon,max_lat"
        """
        # This large dictionary is moved to settings.py
        from app.config.settings import COUNTRY_BBOXES
        return COUNTRY_BBOXES.get(country, None)

    def _apply_dbscan(self, df, eps=0.01, min_samples=5, bbox=None):
        """
        Apply DBSCAN clustering with bbox filtering.
        
        Args:
            df (pandas.DataFrame): DataFrame to cluster
            eps (float): DBSCAN epsilon parameter
            min_samples (int): DBSCAN min_samples parameter
            bbox (str): Optional bounding box string
            
        Returns:
            pandas.DataFrame: DataFrame with cluster labels
        """
        from sklearn.cluster import DBSCAN
        
        if len(df) < min_samples:
            st.warning(f"Too few points ({len(df)}) for clustering. Minimum required: {min_samples}")
            return df
        
        # First filter the data by bounding box if provided
        if bbox:
            # Parse the bbox string to get coordinates
            bbox_coords = [float(coord) for coord in bbox.split(',')]
            if len(bbox_coords) == 4:  # min_lon, min_lat, max_lon, max_lat
                min_lon, min_lat, max_lon, max_lat = bbox_coords
                
                # Filter dataframe to only include points within the bounding box
                bbox_mask = (
                    (df['longitude'] >= min_lon) & 
                    (df['longitude'] <= max_lon) & 
                    (df['latitude'] >= min_lat) & 
                    (df['latitude'] <= max_lat)
                )
                
                filtered_df = df[bbox_mask].copy()
                st.info(f"Filtered data to {len(filtered_df)} points within the selected country boundaries.")
                
                # If filtering resulted in too few points, return the filtered df without clustering
                if len(filtered_df) < min_samples:
                    st.warning(f"Too few points within country boundaries ({len(filtered_df)}) for clustering. Minimum required: {min_samples}")
                    # Mark all as noise
                    filtered_df['cluster'] = -1
                    return filtered_df
                
                df = filtered_df
        
        coords = df[['latitude', 'longitude']].values
        clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
        df['cluster'] = clustering.labels_
        
        n_clusters = len(set(clustering.labels_)) - (1 if -1 in clustering.labels_ else 0)
        n_noise = list(clustering.labels_).count(-1)
        
        st.write(f"Number of clusters found: {n_clusters}")
        st.write(f"Number of noise points: {n_noise}")
        st.write(f"Points in clusters: {len(df) - n_noise}")
        
        return df

    def fetch_fire_data(
        self, 
        country=None, 
        bbox=None, 
        dataset='VIIRS_NOAA20_NRT', 
        start_date=None, 
        end_date=None,
        category='fires',
        use_clustering=True,
        eps=0.01,
        min_samples=5,
        chunk_days=7,
        max_time_diff_days=5
    ):
        """
        Fetch and process fire data from FIRMS API.
        
        Args:
            country (str): Country name
            bbox (str): Bounding box string
            dataset (str): FIRMS dataset name
            start_date (datetime): Start date for data
            end_date (datetime): End date for data
            category (str): Data category ('fires', 'flares', 'volcanoes', 'raw data')
            use_clustering (bool): Whether to apply clustering
            eps (float): DBSCAN epsilon parameter
            min_samples (int): DBSCAN min_samples parameter
            chunk_days (int): Number of days to fetch in each API call
            max_time_diff_days (int): Maximum days between events to be considered same cluster
            
        Returns:
            pandas.DataFrame: Processed fire data with cluster labels
        """
        from app.config.settings import DATASET_START_DATES
        
        if dataset not in DATASET_START_DATES:
            st.error(f"Invalid dataset. Choose from: {list(DATASET_START_DATES.keys())}")
            return None

        if not bbox and country:
            bbox = self.get_country_bbox(country)
        
        if not bbox:
            st.error("Provide a country or bounding box")
            return None

        # Check if the country is large and show a message
        large_countries = ['United States', 'China', 'Russia', 'Canada', 'Brazil', 'Australia', 'India']
        if country in large_countries:
            st.info(f"Fetching data for {country}, which may take longer due to the size of the country. Please be patient...")
            
        url = f"{self.base_url}{self.api_key}/{dataset}/{bbox}/7"
        
        with st.spinner('Fetching data...'):
            try:
                response = self.session.get(url)
                response.raise_for_status()
                df = pd.read_csv(StringIO(response.text))
                
                st.write("Raw Data Information:")
                st.write(f"Total records: {len(df)}")
                
                if len(df) == 0:
                    st.warning(f"No records found for {category} in {country}")
                    return None
                
                if use_clustering:
                    df = self._apply_dbscan(df, eps=eps, min_samples=min_samples, bbox=bbox)
                
                # Perform spatial join if needed for specified categories
                if category in ['flares', 'volcanoes']:
                    with st.spinner(f'Performing spatial join with OSM {category} data...'):
                        df = self.osm_handler.spatial_join(df, category, bbox)
                
                return df

            except Exception as e:
                st.error(f"Error fetching data: {str(e)}")
                return None