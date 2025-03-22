"""
FIRMS API handler for the Fire Investigation Tool.
Provides functionality to fetch and process fire data from NASA's FIRMS API
with support for historical data, large country handling, and advanced clustering.
"""
import pandas as pd
import requests
import streamlit as st
from io import StringIO
from datetime import datetime, date, timedelta
import time

from app.core.osm_handler import OSMHandler

class FIRMSHandler:
    """Handler for FIRMS API interactions with enhanced functionality"""
    
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

    def _apply_dbscan(self, df, eps=0.01, min_samples=5, bbox=None, max_time_diff_days=5):
        """
        Apply DBSCAN clustering with bbox filtering and temporal constraints.
        
        Args:
            df (pandas.DataFrame): DataFrame to cluster
            eps (float): DBSCAN epsilon parameter (spatial distance threshold)
            min_samples (int): DBSCAN min_samples parameter (minimum points to form cluster)
            bbox (str): Optional bounding box string for additional filtering
            max_time_diff_days (int): Maximum days between events to be considered same cluster
            
        Returns:
            pandas.DataFrame: DataFrame with cluster labels
        """
        from sklearn.cluster import DBSCAN
        
        # Early exit if not enough points
        if len(df) < min_samples:
            st.warning(f"Too few points ({len(df)}) for clustering. Minimum required: {min_samples}")
            # Add cluster label column filled with noise indicator (-1)
            df['cluster'] = -1
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
        
        # Check date column format and standardize if needed
        date_col = None
        for col in ['acq_date', 'date', 'Date', 'ACQ_DATE']:
            if col in df.columns:
                date_col = col
                break
        
        if date_col:
            # Convert date to datetime if it's not already
            if df[date_col].dtype != 'datetime64[ns]':
                df[date_col] = pd.to_datetime(df[date_col])
            
            # Create day number from min date for temporal clustering
            min_date = df[date_col].min()
            df['day_num'] = (df[date_col] - min_date).dt.days
            
            # Scale day_num to have less impact than spatial coordinates
            # This ensures fires that occurred at the same location on different days
            # are grouped together if they're within max_time_diff_days
            day_scale = 0.001  # Small weight to time dimension
            
            # Create 3D coordinates: (lat, lon, scaled_day)
            coords = df[['latitude', 'longitude']].copy()
            coords['scaled_day'] = df['day_num'] * day_scale * max_time_diff_days  # Adjust scale by max days
            
            # Apply DBSCAN on 3D coordinates
            clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
        else:
            # If no date column, just use standard 2D clustering
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
    Fetch and process fire data from FIRMS API with support for historical data.
    """
    # Original code remains unchanged...
    
    # After fetching all data and applying the bbox filter:
    # Apply bbox filtering to make sure points are within country boundaries
    if bbox and not all_results.empty:
        # Parse the bbox string to get coordinates
        bbox_coords = [float(coord) for coord in bbox.split(',')]
        if len(bbox_coords) == 4:  # min_lon, min_lat, max_lon, max_lat
            min_lon, min_lat, max_lon, max_lat = bbox_coords
            
            # Filter dataframe to only include points within the bounding box
            bbox_mask = (
                (all_results['longitude'] >= min_lon) & 
                (all_results['longitude'] <= max_lon) & 
                (all_results['latitude'] >= min_lat) & 
                (all_results['latitude'] <= max_lat)
            )
            
            filtered_df = all_results[bbox_mask].copy()
            st.info(f"Filtered data to {len(filtered_df)} points within the rectangular bounding box.")
            
            if len(filtered_df) == 0:
                st.warning(f"No points found within the specified bounding box for {country or 'selected region'}.")
                return None
            
            all_results = filtered_df
            
            # NEW CODE: Further filter by actual country polygon if a country was specified
            if country:
                try:
                    from app.config.settings import get_country_geojson
                    import shapely.geometry as sg
                    from shapely.geometry import Point, shape
                    
                    # Get the country GeoJSON
                    country_geojson = get_country_geojson(country)
                    
                    if country_geojson:
                        # Convert to shapely geometry
                        if 'features' in country_geojson:
                            # Multiple features case
                            country_polygon = None
                            for feature in country_geojson['features']:
                                if feature['geometry']['type'] in ['Polygon', 'MultiPolygon']:
                                    poly = shape(feature['geometry'])
                                    if country_polygon is None:
                                        country_polygon = poly
                                    else:
                                        country_polygon = country_polygon.union(poly)
                        else:
                            # Single geometry case
                            country_polygon = shape(country_geojson['geometry'])
                        
                        # Filter points to only those inside the country polygon
                        initial_count = len(all_results)
                        points_in_country = []
                        
                        for idx, row in all_results.iterrows():
                            point = Point(row['longitude'], row['latitude'])
                            if country_polygon.contains(point):
                                points_in_country.append(idx)
                        
                        if points_in_country:
                            all_results = all_results.loc[points_in_country].copy()
                            st.success(f"Filtered to {len(all_results)} points within the actual {country} borders (removed {initial_count - len(all_results)} points outside borders).")
                        else:
                            st.warning(f"No points found within the actual borders of {country}.")
                            return None
                except ImportError:
                    st.warning("Shapely library not installed. Cannot filter by precise country borders.")
                except Exception as e:
                    st.warning(f"Could not filter by country polygon: {str(e)}")
        
        # Apply clustering to the results if needed
        if use_clustering and not all_results.empty:
            all_results = self._apply_dbscan(all_results, eps=eps, min_samples=min_samples, 
                                            bbox=bbox, max_time_diff_days=max_time_diff_days)
        
        # Apply spatial joins for specific categories
        try:
            # Check if we have geographic dependencies installed
            HAVE_GEO_DEPS = True
            if category in ['flares', 'volcanoes'] and HAVE_GEO_DEPS and not all_results.empty:
                with st.spinner(f'Performing spatial join with OSM {category} data...'):
                    original_count = len(all_results)
                    all_results = self.osm_handler.spatial_join(all_results, category, bbox)
                    
                    # If spatial join found no matches
                    if all_results.empty:
                        # Create a container for the message
                        message_container = st.empty()
                        message_container.warning(f"No {category} found within the selected area and date range. Try a different location or category.")
                        # Return None to prevent map creation
                        return None
        except Exception as e:
            st.warning(f"Could not perform spatial join: {str(e)}")
                    
        st.write("Raw Data Information:")
        st.write(f"Total records: {len(all_results)}")
        
        return all_results