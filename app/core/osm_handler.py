"""
OpenStreetMap query handler for the Fire Investigation Tool.
Provides functionality to query and process OSM data for spatial analysis.
"""
import time
import pandas as pd
import numpy as np
import requests
import streamlit as st

# Check if geospatial dependencies are available
try:
    import geopandas as gpd
    from shapely.geometry import Point
    HAVE_GEO_DEPS = True
except ImportError:
    HAVE_GEO_DEPS = False

class OSMHandler:
    """Class for handling OpenStreetMap queries"""
    
    def __init__(self, verbose=False):
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.timeout = 60  # seconds
        self.max_retries = 3
        self.verbose = verbose  # Add a flag to control logging
        
    def query_osm_features(self, bbox, tags, radius_km=10):
        """
        Query OSM features within a bounding box and with specified tags.
        
        Args:
            bbox (tuple): (min_lon, min_lat, max_lon, max_lat)
            tags (list): List of tag dictionaries to query for
            radius_km (float): Radius in kilometers for spatial join
            
        Returns:
            list: List of OSM features
        """
        if not HAVE_GEO_DEPS:
            # Silent handling instead of st.warning
            return []
            
        # Convert the radius to degrees (approximate, good enough for most uses)
        # 1 degree of latitude = ~111km, 1 degree of longitude varies with latitude
        radius_deg = radius_km / 111.0
        
        # Expand the bbox by the radius
        expanded_bbox = (
            bbox[0] - radius_deg,
            bbox[1] - radius_deg,
            bbox[2] + radius_deg,
            bbox[3] + radius_deg
        )
        
        # Build the Overpass query for all tag combinations
        tag_queries = []
        for tag_dict in tags:
            tag_query = ""
            for k, v in tag_dict.items():
                tag_query += f'["{k}"="{v}"]'
            tag_queries.append(tag_query)
        
        # Combine all tag queries with OR operator
        if tag_queries:
            tag_query_combined = ' nwr ' + ' nwr '.join(tag_queries) + '; '
        else:
            # If no tags provided, match any node, way, or relation
            tag_query_combined = ' nwr; '
        
        # Build query with explicit bbox
        bbox_str = f"{expanded_bbox[0]},{expanded_bbox[1]},{expanded_bbox[2]},{expanded_bbox[3]}"
        overpass_query = f"""
        [out:json][timeout:{self.timeout}][bbox:{bbox_str}];
        (
          {tag_query_combined}
        );
        out center;
        """
        
        # Try to query with retries
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    self.overpass_url,
                    params={"data": overpass_query},
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                return data['elements']
            except Exception as e:
                if attempt < self.max_retries - 1:
                    # Wait and retry
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    return []
    
    def spatial_join(self, df, category, bbox):
        """
        Perform spatial join with OSM features based on category.
        
        Args:
            df (pandas.DataFrame): DataFrame with latitude and longitude columns
            category (str): Category to join ('flares', 'volcanoes', etc.)
            bbox (str): Bounding box string "min_lon,min_lat,max_lon,max_lat"
            
        Returns:
            pandas.DataFrame: DataFrame with additional OSM feature columns
        """
        # Skip if category doesn't need spatial join or we don't have GeoSpatial dependencies
        if not HAVE_GEO_DEPS or category not in ['flares', 'volcanoes']:
            return df
        
        # Parse the bbox string
        bbox_coords = [float(coord) for coord in bbox.split(',')]
        
        # Define tags for different categories - each category has its own exclusive tags
        tags = []
        if category == 'flares':
            # Only use flare/oil & gas related tags for 'flares' category
            tags = [
                {"man_made": "flare"},
                {"usage": "flare_header"},
                {"landmark": "flare_stack"},
                {"industrial": "oil"}
            ]
        elif category == 'volcanoes':
            # Only use volcano related tags for 'volcanoes' category
            tags = [
                {"natural": "volcano"},
                {"geological": "volcanic_vent"},
                {"volcano:type": "stratovolcano"},
                {"volcano:type": "scoria"},
                {"volcano:type": "shield"},
                {"volcano:type": "dirt"},
                {"volcano:type": "lava_dome"},
                {"volcano:type": "caldera"}
            ]
        
        # Query OSM features using the category-specific tags
        osm_features = self.query_osm_features(bbox_coords, tags)
        
        # Create GeoDataFrame from DataFrame
        gdf = gpd.GeoDataFrame(
            df,
            geometry=[Point(lon, lat) for lon, lat in zip(df['longitude'], df['latitude'])],
            crs="EPSG:4326"
        )
        
        # Create buffer of 10km (approximate, for quick calculation)
        # 0.1 degrees is approximately 11km at the equator
        buffer_degrees = 10 / 111  # Approximate conversion from km to degrees
        
        # Add columns for OSM matches
        gdf['osm_match'] = False
        gdf['osm_feature_id'] = None
        gdf['osm_feature_type'] = None
        gdf['osm_distance_km'] = None
        
        # Process OSM features
        if osm_features:
            # Create a list of Points for OSM features
            osm_points = []
            for feature in osm_features:
                # Get center coordinates
                if 'center' in feature:
                    lat, lon = feature['center']['lat'], feature['center']['lon']
                elif 'lat' in feature and 'lon' in feature:
                    lat, lon = feature['lat'], feature['lon']
                else:
                    continue
                
                osm_points.append({
                    'id': feature['id'],
                    'type': feature['type'],
                    'geometry': Point(lon, lat)
                })
            
            # Create GeoDataFrame for OSM features
            osm_gdf = gpd.GeoDataFrame(osm_points, crs="EPSG:4326")
            
            if not osm_gdf.empty:
                # Buffer the DataFrame points by 10km
                gdf_buffered = gdf.copy()
                gdf_buffered['geometry'] = gdf_buffered['geometry'].buffer(buffer_degrees)
                
                # Perform spatial join
                joined = gpd.sjoin(gdf_buffered, osm_gdf, how="left", predicate="intersects")
                
                # Update the original GDF with match information
                for idx, row in joined.iterrows():
                    if pd.notna(row['id']):
                        # Calculate distance (approximately)
                        orig_point = Point(df.loc[idx, 'longitude'], df.loc[idx, 'latitude'])
                        osm_point = row['geometry_right']
                        # Simple Euclidean distance (degrees) * 111 km/degree for approximate km
                        distance = orig_point.distance(osm_point) * 111
                        
                        # Update the dataframe
                        gdf.loc[idx, 'osm_match'] = True
                        gdf.loc[idx, 'osm_feature_id'] = row['id']
                        gdf.loc[idx, 'osm_feature_type'] = row['type']
                        gdf.loc[idx, 'osm_distance_km'] = distance
        
        # Return the updated DataFrame with OSM join information
        result_df = pd.DataFrame(gdf.drop(columns='geometry'))
        matched_count = result_df['osm_match'].sum()
        
        # This one is actually useful to know
        if self.verbose or matched_count > 0:
            st.success(f"Found {matched_count} points within 10km of relevant {category} features.")
        
        # For non-fire categories, only include points that match OSM features
        if category in ['flares', 'volcanoes'] and matched_count > 0:
            filtered_df = result_df[result_df['osm_match'] == True].copy()
            return filtered_df
        else:
            return result_df