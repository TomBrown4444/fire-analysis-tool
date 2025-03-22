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
#                st.info(f"Filtered data to {len(filtered_df)} points within the selected country boundaries.")
                
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
        chunk_days=7,  # Default chunk size
        max_time_diff_days=5  # Maximum days gap to consider as same fire
    ):
        """
        Fetch and process fire data from FIRMS API with support for historical data.
        
        Args:
            country (str): Country name
            bbox (str): Bounding box string "min_lon,min_lat,max_lon,max_lat"
            dataset (str): FIRMS dataset name (e.g., 'VIIRS_NOAA20_NRT')
            start_date (datetime/date/str): Start date for data
            end_date (datetime/date/str): End date for data
            category (str): Data category ('fires', 'flares', 'volcanoes', 'raw data')
            use_clustering (bool): Whether to apply clustering
            eps (float): DBSCAN epsilon parameter (spatial distance threshold)
            min_samples (int): DBSCAN min_samples parameter (minimum points to form cluster)
            chunk_days (int): Number of days to fetch in each API call
            max_time_diff_days (int): Maximum days between events to be considered same cluster
            
        Returns:
            pandas.DataFrame: Processed fire data with cluster labels
        """
        # Import dataset availability info from settings
        try:
            from app.config.settings import DATASET_AVAILABILITY
        except ImportError:
            # Fallback if not available in settings
            DATASET_AVAILABILITY = {
                'MODIS_NRT': {'min_date': '2024-12-01', 'max_date': '2025-03-17'},
                'MODIS_SP': {'min_date': '2000-11-01', 'max_date': '2024-11-30'},
                'VIIRS_NOAA20_NRT': {'min_date': '2024-12-01', 'max_date': '2025-03-17'},
                'VIIRS_NOAA20_SP': {'min_date': '2018-04-01', 'max_date': '2024-11-30'},
                'VIIRS_NOAA21_NRT': {'min_date': '2024-01-17', 'max_date': '2025-03-17'},
                'VIIRS_SNPP_NRT': {'min_date': '2025-01-01', 'max_date': '2025-03-17'},
                'VIIRS_SNPP_SP': {'min_date': '2012-01-20', 'max_date': '2024-12-31'},
                'LANDSAT_NRT': {'min_date': '2022-06-20', 'max_date': '2025-03-17'}
            }
        
        # Determine if we need historical data
        today = datetime.now().date()
        
        # Convert dates to proper format for comparison
        if isinstance(start_date, date):
            start_date_date = start_date
        elif isinstance(start_date, datetime):
            start_date_date = start_date.date()
        else:
            # If it's a string, parse it
            try:
                start_date_date = datetime.strptime(str(start_date), "%Y-%m-%d").date()
            except:
                # Default to 7 days ago if parsing fails
                start_date_date = today - timedelta(days=7)
        
        # Check if we need historical data (more than 10 days ago)
        need_historical = (today - start_date_date).days > 10
        
        # If we need historical data, switch to Standard Processing dataset
        original_dataset = dataset
        if need_historical and "_NRT" in dataset:
            # Switch to Standard Processing version
            dataset = dataset.replace("_NRT", "_SP")
            st.info(f"Fetching historical data using {dataset} dataset")
        
        # Check dataset validity
        if dataset not in DATASET_AVAILABILITY:
            st.error(f"Invalid dataset: {dataset}. Please select a valid dataset.")
            return None
        
        # Check if the requested date range is available for this dataset
        if dataset in DATASET_AVAILABILITY:
            min_date = datetime.strptime(DATASET_AVAILABILITY[dataset]['min_date'], '%Y-%m-%d').date()
            max_date = datetime.strptime(DATASET_AVAILABILITY[dataset]['max_date'], '%Y-%m-%d').date()
            
            if start_date_date < min_date:
                st.warning(f"Start date {start_date_date} is before the earliest available date ({min_date}) for {dataset}. Using earliest available date.")
                start_date_date = min_date
        
        if not bbox and country:
            bbox = self.get_country_bbox(country)
        
        if not bbox:
            st.error("Provide a country or bounding box")
            return None
        
        # Convert dates to strings
        start_date_str = start_date_date.strftime('%Y-%m-%d')
        
        if isinstance(end_date, date):
            end_date_date = end_date
        elif isinstance(end_date, datetime):
            end_date_date = end_date.date()
        else:
            # If it's a string, parse it
            try:
                end_date_date = datetime.strptime(str(end_date), "%Y-%m-%d").date()
            except:
                # Default to today if parsing fails
                end_date_date = today
        
        # Ensure end date doesn't exceed dataset's max date
        if dataset in DATASET_AVAILABILITY:
            max_date = datetime.strptime(DATASET_AVAILABILITY[dataset]['max_date'], '%Y-%m-%d').date()
            if end_date_date > max_date:
                st.warning(f"End date {end_date_date} is after the latest available date ({max_date}) for {dataset}. Using latest available date.")
                end_date_date = max_date
        
        end_date_str = end_date_date.strftime('%Y-%m-%d')
        
        # Now we need to fetch data in chunks, respecting the API limits
        st.write(f"Fetching fire data from {start_date_str} to {end_date_str} for {country or 'selected region'}...")
        
        # Create date chunks
        date_chunks = []
        current_date = start_date_date
        while current_date <= end_date_date:
            chunk_end = min(current_date + timedelta(days=min(10, chunk_days)-1), end_date_date)
            date_chunks.append((current_date, chunk_end))
            current_date = chunk_end + timedelta(days=1)
        
        # Set up progress tracking
        st.write(f"Processing data in {len(date_chunks)} chunks...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Initialize combined results
        all_results = pd.DataFrame()
        
        # Special handling for large countries
        large_countries = ['United States', 'China', 'Russia', 'Canada', 'Brazil', 'Australia', 'India']
        if country in large_countries:
            st.warning(f"Consider using your own FIRMS API key for faster results.")
            
            # Special handling for Russia which is particularly large
            if country == 'Russia':
                st.info("Russia is very large. Dividing into smaller regions for better performance...")
                
                # Process western Russia
                west_bbox = '19.25,41.151,60.0,81.2'
                st.write("Processing Western Russia...")
                for i, (chunk_start, chunk_end) in enumerate(date_chunks):
                    chunk_start_str = chunk_start.strftime('%Y-%m-%d')
                    chunk_end_str = chunk_end.strftime('%Y-%m-%d')
                    status_text.write(f"Western Region - Chunk {i+1}/{len(date_chunks)}: {chunk_start_str} to {chunk_end_str}")
                    progress_bar.progress((i) / (len(date_chunks) * 3))  # 3 regions
                    
                    days_in_chunk = (chunk_end - chunk_start).days + 1
                    if need_historical:
                        url = f"{self.base_url}{self.api_key}/{dataset}/{west_bbox}/{days_in_chunk}/{chunk_start_str}"
                    else:
                        url = f"{self.base_url}{self.api_key}/{dataset}/{west_bbox}/{days_in_chunk}/{chunk_start_str}"
                    
                    try:
                        response = self.session.get(url, timeout=45)  # Shorter timeout
                        response.raise_for_status()
                        if response.text.strip() and "Invalid" not in response.text:
                            chunk_df = pd.read_csv(StringIO(response.text))
                            if not chunk_df.empty:
                                date_mask = (chunk_df['acq_date'] >= chunk_start_str) & (chunk_df['acq_date'] <= chunk_end_str)
                                filtered_chunk = chunk_df[date_mask].copy()
                                if not filtered_chunk.empty:
                                    all_results = pd.concat([all_results, filtered_chunk], ignore_index=True)
                    except Exception as e:
                        st.warning(f"Error processing Western Russia chunk {i+1}: {str(e)}")
                
                # Process central Russia
                central_bbox = '60.0,41.151,120.0,81.2'
                st.write("Processing Central Russia...")
                for i, (chunk_start, chunk_end) in enumerate(date_chunks):
                    chunk_start_str = chunk_start.strftime('%Y-%m-%d')
                    chunk_end_str = chunk_end.strftime('%Y-%m-%d')
                    status_text.write(f"Central Region - Chunk {i+1}/{len(date_chunks)}: {chunk_start_str} to {chunk_end_str}")
                    progress_bar.progress((len(date_chunks) + i) / (len(date_chunks) * 3))
                    
                    days_in_chunk = (chunk_end - chunk_start).days + 1
                    if need_historical:
                        url = f"{self.base_url}{self.api_key}/{dataset}/{central_bbox}/{days_in_chunk}/{chunk_start_str}"
                    else:
                        url = f"{self.base_url}{self.api_key}/{dataset}/{central_bbox}/{days_in_chunk}/{chunk_start_str}"
                    
                    try:
                        response = self.session.get(url, timeout=45)  # Shorter timeout
                        response.raise_for_status()
                        if response.text.strip() and "Invalid" not in response.text:
                            chunk_df = pd.read_csv(StringIO(response.text))
                            if not chunk_df.empty:
                                date_mask = (chunk_df['acq_date'] >= chunk_start_str) & (chunk_df['acq_date'] <= chunk_end_str)
                                filtered_chunk = chunk_df[date_mask].copy()
                                if not filtered_chunk.empty:
                                    all_results = pd.concat([all_results, filtered_chunk], ignore_index=True)
                    except Exception as e:
                        st.warning(f"Error processing Central Russia chunk {i+1}: {str(e)}")
                
                # Process eastern Russia
                east_bbox = '120.0,41.151,180.0,81.2'
                st.write("Processing Eastern Russia...")
                for i, (chunk_start, chunk_end) in enumerate(date_chunks):
                    chunk_start_str = chunk_start.strftime('%Y-%m-%d')
                    chunk_end_str = chunk_end.strftime('%Y-%m-%d')
                    status_text.write(f"Eastern Region - Chunk {i+1}/{len(date_chunks)}: {chunk_start_str} to {chunk_end_str}")
                    progress_bar.progress((2 * len(date_chunks) + i) / (len(date_chunks) * 3))
                    
                    days_in_chunk = (chunk_end - chunk_start).days + 1
                    if need_historical:
                        url = f"{self.base_url}{self.api_key}/{dataset}/{east_bbox}/{days_in_chunk}/{chunk_start_str}"
                    else:
                        url = f"{self.base_url}{self.api_key}/{dataset}/{east_bbox}/{days_in_chunk}/{chunk_start_str}"
                    
                    try:
                        response = self.session.get(url, timeout=45)  # Shorter timeout
                        response.raise_for_status()
                        if response.text.strip() and "Invalid" not in response.text:
                            chunk_df = pd.read_csv(StringIO(response.text))
                            if not chunk_df.empty:
                                date_mask = (chunk_df['acq_date'] >= chunk_start_str) & (chunk_df['acq_date'] <= chunk_end_str)
                                filtered_chunk = chunk_df[date_mask].copy()
                                if not filtered_chunk.empty:
                                    all_results = pd.concat([all_results, filtered_chunk], ignore_index=True)
                    except Exception as e:
                        st.warning(f"Error processing Eastern Russia chunk {i+1}: {str(e)}")
            else:
                # For other large countries, use standard approach with longer timeout
                self.session.timeout = 120  # Increase timeout to 2 minutes
                
                # Standard chunked processing for other large countries
                for i, (chunk_start, chunk_end) in enumerate(date_chunks):
                    chunk_start_str = chunk_start.strftime('%Y-%m-%d')
                    chunk_end_str = chunk_end.strftime('%Y-%m-%d')
                    
                    # Update progress
                    status_text.write(f"Fetching chunk {i+1}/{len(date_chunks)}: {chunk_start_str} to {chunk_end_str}")
                    progress_bar.progress((i) / len(date_chunks))
                    
                    # Get the number of days in this chunk
                    days_in_chunk = (chunk_end - chunk_start).days + 1
                    
                    # Format API URL based on historical data approach
                    if need_historical:
                        url = f"{self.base_url}{self.api_key}/{dataset}/{bbox}/{days_in_chunk}/{chunk_start_str}"
                    else:
                        if i == 0 and len(date_chunks) == 1 and days_in_chunk <= 7:
                            url = f"{self.base_url}{self.api_key}/{original_dataset}/{bbox}/7"
                        else:
                            url = f"{self.base_url}{self.api_key}/{dataset}/{bbox}/{days_in_chunk}/{chunk_start_str}"
                    
                    try:
                        # Fetch data for this chunk
                        response = self.session.get(url, timeout=120)  # Longer timeout for large countries
                        response.raise_for_status()
                        
                        # Parse CSV data if valid
                        if response.text.strip() and "Invalid" not in response.text and "Error" not in response.text:
                            chunk_df = pd.read_csv(StringIO(response.text))
                            
                            # Only process non-empty results
                            if not chunk_df.empty:
                                # Filter to ensure records are within the requested date range
                                if 'acq_date' in chunk_df.columns:
                                    date_mask = (chunk_df['acq_date'] >= chunk_start_str) & (chunk_df['acq_date'] <= chunk_end_str)
                                    filtered_chunk = chunk_df[date_mask].copy()
                                    if not filtered_chunk.empty:
                                        all_results = pd.concat([all_results, filtered_chunk], ignore_index=True)
                                else:
                                    all_results = pd.concat([all_results, chunk_df], ignore_index=True)
                    except Exception as e:
                        st.warning(f"Error processing chunk {i+1}: {str(e)}")
        else:
            # Standard chunked processing for normal countries
            for i, (chunk_start, chunk_end) in enumerate(date_chunks):
                chunk_start_str = chunk_start.strftime('%Y-%m-%d')
                chunk_end_str = chunk_end.strftime('%Y-%m-%d')
                
                # Update progress
                status_text.write(f"Fetching chunk {i+1}/{len(date_chunks)}: {chunk_start_str} to {chunk_end_str}")
                progress_bar.progress((i) / len(date_chunks))
                
                # Get the number of days in this chunk
                days_in_chunk = (chunk_end - chunk_start).days + 1
                
                # Format API URL based on historical data approach
                if need_historical:
                    url = f"{self.base_url}{self.api_key}/{dataset}/{bbox}/{days_in_chunk}/{chunk_start_str}"
                else:
                    if i == 0 and len(date_chunks) == 1 and days_in_chunk <= 7:
                        url = f"{self.base_url}{self.api_key}/{original_dataset}/{bbox}/7"
                    else:
                        url = f"{self.base_url}{self.api_key}/{dataset}/{bbox}/{days_in_chunk}/{chunk_start_str}"
                
                try:
                    # Fetch data for this chunk
                    response = self.session.get(url, timeout=60)
                    response.raise_for_status()
                    
                    # Parse CSV data if valid
                    if response.text.strip() and "Invalid" not in response.text and "Error" not in response.text:
                        chunk_df = pd.read_csv(StringIO(response.text))
                        
                        # Only process non-empty results
                        if not chunk_df.empty:
                            # Filter to ensure records are within the requested date range
                            if 'acq_date' in chunk_df.columns:
                                date_mask = (chunk_df['acq_date'] >= chunk_start_str) & (chunk_df['acq_date'] <= chunk_end_str)
                                filtered_chunk = chunk_df[date_mask].copy()
                                if not filtered_chunk.empty:
                                    all_results = pd.concat([all_results, filtered_chunk], ignore_index=True)
                            else:
                                all_results = pd.concat([all_results, chunk_df], ignore_index=True)
                except Exception as e:
                    st.warning(f"Error processing chunk {i+1}: {str(e)}")
        
        # Clean up progress indicators
        progress_bar.progress(1.0)
        status_text.empty()
        
        # Check if we got any data
        if all_results.empty:
            st.warning(f"No records found for {category} in {country or 'selected region'} for the selected date range")
            return None
        

        
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
#                st.info(f"Filtered data to {len(filtered_df)} points within the selected country boundaries.")
                
                if len(filtered_df) == 0:
                    st.warning(f"No points found within the specified bounding box for {country or 'selected region'}.")
                    return None
                
                all_results = filtered_df
        
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