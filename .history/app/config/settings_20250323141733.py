"""
Configuration settings for the Fire Investigation Tool.
Contains constants, predefined settings, and configuration parameters.
"""
import json
import os
from pathlib import Path
import streamlit as st

# Retrieve API credentials from Streamlit secrets if available, otherwise use fallbacks
DEFAULT_FIRMS_USERNAME = st.secrets.get("firms", {}).get("username", "tombrown4444")
DEFAULT_FIRMS_PASSWORD = st.secrets.get("firms", {}).get("password", "wft_wxh6phw9URY-pkv")
DEFAULT_FIRMS_API_KEY = st.secrets.get("firms", {}).get("api_key", "897a9b7869fd5e4ad231573e14e1c8c8")

# Add these lines after the imports
# Create directory for GeoJSON files
GEOJSON_DIR = Path("app/data/geojson")
os.makedirs(GEOJSON_DIR, exist_ok=True)

# Flag to use GeoJSON borders
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

# Country bounding boxes for the FIRMS API
COUNTRY_BBOXES = {
            'Afghanistan': '60.52,29.31,75.15,38.48',
            'United States': '-125.0,24.0,-66.0,50.0',
            'Brazil': '-73.0,-33.0,-35.0,5.0',
            'Australia': '113.0,-44.0,154.0,-10.0',
            'India': '68.0,7.0,97.0,37.0',
            'China': '73.0,18.0,135.0,53.0',
            'Canada': '-141.0,41.7,-52.6,83.0',
            'Russia': '19.25,41.151,180.0,81.2',
            'Indonesia': '95.0,-11.0,141.0,6.0',
            'Mongolia': '87.76,41.59,119.93,52.15',
            'Kazakhstan': '46.46,40.57,87.36,55.45',
            'Mexico': '-118.4,14.5,-86.4,32.7',
            'Argentina': '-73.6,-55.1,-53.6,-21.8',
            'Chile': '-75.6,-55.9,-66.9,-17.5',
            'South Africa': '16.3,-34.8,32.9,-22.1',
            'New Zealand': '166.3,-47.3,178.6,-34.4',
            'Thailand': '97.3,5.6,105.6,20.5',
            'Vietnam': '102.1,8.4,109.5,23.4',
            'Malaysia': '99.6,0.8,119.3,7.4',
            'Myanmar': '92.2,9.8,101.2,28.5',
            'Philippines': '116.9,4.6,126.6,19.6',
            'Papua New Guinea': '140.8,-11.7,155.6,-1.3',
            'Greece': '19.4,34.8,28.3,41.8',
            'Turkey': '26.0,36.0,45.0,42.0',
            'Spain': '-9.3,36.0,4.3,43.8',
            'Portugal': '-9.5,37.0,-6.2,42.2',
            'Italy': '6.6,35.5,18.5,47.1',
            'France': '-5.1,41.3,9.6,51.1',
            'Germany': '5.9,47.3,15.0,55.1',
            'Ukraine': '22.1,44.4,40.2,52.4',
            'Sweden': '11.1,55.3,24.2,69.1',
            'Norway': '4.5,58.0,31.1,71.2',
            'Finland': '20.6,59.8,31.6,70.1',
            'Japan': '129.5,31.4,145.8,45.5',
            'South Korea': '126.1,33.1,129.6,38.6',
            'North Korea': '124.2,37.7,130.7,43.0',
            'Iran': '44.0,25.1,63.3,39.8',
            'Iraq': '38.8,29.1,48.8,37.4',
            'Saudi Arabia': '34.6,16.3,55.7,32.2',
            'Egypt': '24.7,22.0,36.9,31.7',
            'Libya': '9.3,19.5,25.2,33.2',
            'Algeria': '-8.7,19.1,12.0,37.1',
            'Morocco': '-13.2,27.7,-1.0,35.9',
            'Sudan': '21.8,8.7,38.6,22.2',
            'South Sudan': '23.4,3.5,35.9,12.2',
            'Ethiopia': '33.0,3.4,47.9,14.8',
            'Kenya': '33.9,-4.7,41.9,5.0',
            'Tanzania': '29.3,-11.7,40.4,-1.0',
            'Uganda': '29.5,-1.4,35.0,4.2',
            'Nigeria': '2.7,4.3,14.7,13.9',
            'Ghana': '-3.3,4.7,1.2,11.2',
            'Ivory Coast': '-8.6,4.4,-2.5,10.7',
            'Guinea': '-15.1,7.2,-7.6,12.7',
            'Somalia': '40.9,-1.7,51.4,11.9',
            'Democratic Republic of the Congo': '12.2,-13.5,31.3,5.3',
            'Angola': '11.7,-18.0,24.1,-4.4',
            'Namibia': '11.7,-28.9,25.3,-16.9',
            'Zambia': '22.0,-18.0,33.7,-8.2',
            'Zimbabwe': '25.2,-22.4,33.1,-15.6',
            'Mozambique': '30.2,-26.9,40.9,-10.5',
            'Madagascar': '43.2,-25.6,50.5,-11.9',
            'Colombia': '-79.0,-4.2,-66.9,12.5',
            'Venezuela': '-73.4,0.6,-59.8,12.2',
            'Peru': '-81.3,-18.4,-68.7,-0.0',
            'Bolivia': '-69.6,-22.9,-57.5,-9.7',
            'Paraguay': '-62.6,-27.6,-54.3,-19.3',
            'Uruguay': '-58.4,-34.9,-53.1,-30.1',
            'Ecuador': '-81.0,-5.0,-75.2,1.4',
            'French Guiana': '-54.6,2.1,-51.6,5.8',
            'Suriname': '-58.1,1.8,-54.0,6.0',
            'Guyana': '-61.4,1.2,-56.5,8.6',
            'Panama': '-83.0,7.2,-77.1,9.7',
            'Costa Rica': '-85.9,8.0,-82.5,11.2',
            'Nicaragua': '-87.7,10.7,-83.1,15.0',
            'Honduras': '-89.4,12.9,-83.1,16.5',
            'El Salvador': '-90.1,13.1,-87.7,14.5',
            'Guatemala': '-92.2,13.7,-88.2,17.8',
            'Belize': '-89.2,15.9,-87.8,18.5',
            'Cuba': '-85.0,19.8,-74.1,23.2',
            'Haiti': '-74.5,18.0,-71.6,20.1',
            'Dominican Republic': '-72.0,17.5,-68.3,20.0',
            'Jamaica': '-78.4,17.7,-76.2,18.5',
            'Puerto Rico': '-67.3,17.9,-65.6,18.5',
            'Bahamas': '-79.0,20.9,-72.7,27.3',
            'Trinidad and Tobago': '-61.9,10.0,-60.5,11.3',
            'Bangladesh': '88.0,20.6,92.7,26.6',
            'Nepal': '80.0,26.3,88.2,30.4',
            'Bhutan': '88.7,26.7,92.1,28.3',
            'Sri Lanka': '79.6,5.9,81.9,9.8',
            'Maldives': '72.7,-0.7,73.8,7.1',
            'Pakistan': '61.0,23.5,77.8,37.1',
            'Afghanistan': '60.5,29.4,74.9,38.5',
            'Uzbekistan': '56.0,37.2,73.1,45.6',
            'Turkmenistan': '52.5,35.1,66.7,42.8',
            'Tajikistan': '67.3,36.7,75.2,41.0',
            'Kyrgyzstan': '69.3,39.2,80.3,43.3',
            'Cambodia': '102.3,10.4,107.6,14.7',
            'Laos': '100.1,13.9,107.7,22.5',
            'Taiwan': '120.0,21.9,122.0,25.3',
            'United Arab Emirates': '51.5,22.6,56.4,26.1',
            'Oman': '52.0,16.6,59.8,26.4',
            'Yemen': '42.5,12.5,54.0,19.0',
            'Kuwait': '46.5,28.5,48.4,30.1',
            'Qatar': '50.7,24.5,51.6,26.2',
            'Bahrain': '50.4,25.8,50.8,26.3',
            'Jordan': '34.9,29.2,39.3,33.4',
            'Lebanon': '35.1,33.0,36.6,34.7',
            'Syria': '35.7,32.3,42.4,37.3',
            'Israel': '34.2,29.5,35.9,33.3',
            'Palestine': '34.9,31.2,35.6,32.6',
            'Cyprus': '32.0,34.6,34.6,35.7',
            'Iceland': '-24.5,63.3,-13.5,66.6',
            'Ireland': '-10.5,51.4,-6.0,55.4',
            'United Kingdom': '-8.2,49.9,1.8,58.7',
            'Belgium': '2.5,49.5,6.4,51.5',
            'Netherlands': '3.3,50.8,7.2,53.5',
            'Luxembourg': '5.7,49.4,6.5,50.2',
            'Switzerland': '5.9,45.8,10.5,47.8',
            'Austria': '9.5,46.4,17.2,49.0',
            'Hungary': '16.1,45.7,22.9,48.6',
            'Slovakia': '16.8,47.7,22.6,49.6',
            'Czech Republic': '12.1,48.5,18.9,51.1',
            'Poland': '14.1,49.0,24.2,54.8',
            'Denmark': '8.0,54.5,15.2,57.8',
            'Estonia': '23.3,57.5,28.2,59.7',
            'Latvia': '20.8,55.7,28.2,58.1',
            'Lithuania': '20.9,53.9,26.8,56.5',
            'Belarus': '23.2,51.3,32.8,56.2',
            'Moldova': '26.6,45.5,30.2,48.5',
            'Romania': '20.3,43.6,29.7,48.3',
            'Bulgaria': '22.4,41.2,28.6,44.2',
            'Serbia': '18.8,42.2,23.0,46.2',
            'Croatia': '13.5,42.4,19.4,46.6',
            'Bosnia and Herzegovina': '15.7,42.6,19.6,45.3',
            'Slovenia': '13.4,45.4,16.6,46.9',
            'Albania': '19.3,39.6,21.1,42.7',
            'North Macedonia': '20.4,40.8,23.0,42.4',
            'Montenegro': '18.4,41.9,20.4,43.6',
            'New Caledonia': '164.0,-22.7,167.0,-20.0',
            'Fiji': '177.0,-19.2,180.0,-16.0',
            'Vanuatu': '166.0,-20.3,170.0,-13.0',
            'Solomon Islands': '155.0,-11.0,170.0,-5.0',
            'Timor-Leste': '124.0,-9.5,127.3,-8.1',
            'Palau': '131.1,2.8,134.7,8.1',
            'Micronesia': '138.0,1.0,163.0,10.0',
            'Marshall Islands': '160.0,4.0,172.0,15.0',
            'Kiribati': '-175.0,-5.0,177.0,5.0',
            'Tuvalu': '176.0,-10.0,180.0,-5.0',
            'Samoa': '-172.8,-14.1,-171.4,-13.4',
            'Tonga': '-175.4,-22.4,-173.7,-15.5',
            'Cook Islands': '-166.0,-22.0,-157.0,-8.0',
}

# Add this function to your settings.py file
def get_country_geojson(country_name):
    """Get GeoJSON for a country, downloading it if needed."""
    try:
        import geopandas as gpd
    except ImportError:
        print("geopandas is not installed. Install with 'pip install geopandas'")
        return None
        
    # Create a safe filename
    safe_name = country_name.lower().replace(' ', '_')
    filepath = GEOJSON_DIR / f"{safe_name}.geojson"
    
    # If file exists, load it
    if filepath.exists():
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading GeoJSON for {country_name}: {e}")
            
    # Otherwise download it
    try:
        # Load world data from Natural Earth
        world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
        
        # Find the country
        country_data = world[world.name.str.lower() == country_name.lower()]
        
        if country_data.empty:
            print(f"Country '{country_name}' not found in Natural Earth data")
            return None
            
        # Save to file
        country_data.to_file(filepath, driver='GeoJSON')
        
        # Load and return
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error getting GeoJSON for {country_name}: {e}")
        
    return None

# For backward compatibility
def download_country_geojson(country_name):
    """Alias for get_country_geojson for backward compatibility."""
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