"""
Configuration settings for the Fire Investigation Tool.
Contains constants, predefined settings, and configuration parameters.
"""
import json
import os
from pathlib import Path

# Create directory for GeoJSON files
GEOJSON_DIR = Path("app/data/geojson")
os.makedirs(GEOJSON_DIR, exist_ok=True)

# Flag to use GeoJSON borders (can be toggled)
USE_GEOJSON_BORDERS = True

# FIRMS API dataset start dates
DATASET_START_DATES = {
    'MODIS_NRT': '2000-11-01',
    'VIIRS_SNPP_NRT': '2012-01-19',
    'VIIRS_NOAA20_NRT': '2018-01-01',
    'VIIRS_NOAA21_NRT': '2023-01-01'
}

# Basemap tiles for the map visualization
BASEMAP_TILES = {
    'Dark': 'cartodbdark_matter',
    'Light': 'cartodbpositron',
    'Satellite': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    'Terrain': 'stamenterrain'
}

# Country bounding boxes for the FIRMS API (still needed for API requests)
COUNTRY_BBOXES = {
    'Afghanistan': '60.52,29.31,75.15,38.48',
    'United States': '-125.0,24.0,-66.0,50.0',
    # ... the rest of your existing dictionary
}

# Country name mapping (for cases where names differ between your app and Natural Earth dataset)
COUNTRY_NAME_MAPPING = {
    "United States": "United States of America",
    "Russia": "Russia",
    # Add more mappings if needed
}

def get_country_geojson(country_name):
    """
    Get GeoJSON data for a country using geopandas.
    
    Args:
        country_name (str): Name of the country
        
    Returns:
        dict: GeoJSON data for the country, or None if not found
    """
    try:
        import geopandas as gpd
    except ImportError:
        print("geopandas is not installed. Please install it with 'pip install geopandas'.")
        return None
    
    # Create a safe filename
    safe_name = country_name.lower().replace(' ', '_')
    filepath = GEOJSON_DIR / f"{safe_name}.geojson"
    
    # If the file exists, load it
    if filepath.exists():
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading GeoJSON for {country_name}: {e}")
    
    try:
        # Load world data from Natural Earth
        world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
        
        # Try to find the country with the original name
        country_data = world[world.name.str.lower() == country_name.lower()]
        
        # If not found, try using the mapping
        if country_data.empty and country_name in COUNTRY_NAME_MAPPING:
            mapped_name = COUNTRY_NAME_MAPPING[country_name]
            country_data = world[world.name.str.lower() == mapped_name.lower()]
        
        if country_data.empty:
            print(f"Country '{country_name}' not found in Natural Earth data.")
            return None
        
        # Save to file
        country_data.to_file(filepath, driver='GeoJSON')
        
        # Load and return the saved file
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error getting GeoJSON for {country_name}: {e}")
    
    return None

# Add this function to satisfy the existing import in main.py
def download_country_geojson(country_name):
    """
    Download GeoJSON for a country (alias for get_country_geojson).
    """
    return get_country_geojson(country_name)

# Default API credentials
DEFAULT_FIRMS_USERNAME = "tombrown4444"
DEFAULT_FIRMS_PASSWORD = "wft_wxh6phw9URY-pkv"
DEFAULT_FIRMS_API_KEY = "897a9b7869fd5e4ad231573e14e1c8c8"

# Map settings
DEFAULT_DOT_SIZE_MULTIPLIER = 1.0
DEFAULT_COLOR_PALETTE = 'inferno'
DEFAULT_BASEMAP = 'Dark'

# Color palettes for map visualization
COLOR_PALETTES = {
    'inferno': ['#FCFFA4', '#F8DF3A', '#FB9E3A', '#ED6925', '#D94E11', '#B62A07', '#8B0F07', '#5D0C0C', '#420A68'],
    'viridis': ['#FDE725', '#BBDF27', '#6DCE59', '#35B779', '#1F9E89', '#26828E', '#31688E', '#3E4989', '#482878'],
    'plasma': ['#F0F921', '#FCCE25', '#FCA636', '#F1844B', '#E16462', '#CC4778', '#B12A90', '#8F0DA4', '#6A00A8'],
    'magma': ['#FCFDBF', '#FECA8D', '#FD9668', '#F1605D', '#CD4071', '#9E2F7F', '#721F81', '#440F76', '#180F3D'],
    'cividis': ['#FEE838', '#E1CC55', '#C3B369', '#A59C74', '#8A8678', '#707173', '#575D6D', '#3B496C', '#123570']
}

# Large countries that might be slow with wide date ranges
LARGE_COUNTRIES = ['United States', 'China', 'Russia', 'Canada', 'Brazil', 'Australia', 'India']

# Default clustering parameters
DEFAULT_EPS = 0.01
DEFAULT_MIN_SAMPLES = 5