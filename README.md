# Fire Investigation Tool

A Streamlit application for analyzing satellite fire data from NASA FIRMS.

## Features

- Interactive map visualization of fire clusters
- Analysis of fire radiative power (FRP) and temperature
- Timeline view to track fires over time
- Export capabilities for report generation
- Support for different data categories (fires, flares)
- Integration with OpenStreetMap for geographic context

## Application Structure

```
fire-tool-streamlit/
├── app/                      # Main application code
│   ├── main.py               # Main Streamlit app
│   ├── core/                 # Core functionality
│   │   ├── firms_handler.py  # FIRMS API handler
│   │   ├── osm_handler.py    # OpenStreetMap handler
│   │   ├── analysis.py       # Data analysis functions
│   │   └── utils.py          # Utility functions
│   ├── ui/                   # UI components
│   │   ├── map.py            # Map visualization
│   │   ├── sidebar.py        # Sidebar UI
│   │   ├── timeline.py       # Timeline components
│   │   └── utils.py          # UI utilities
│   └── config/
│       └── settings.py       # Configuration settings
├── tests/                    # Test files
├── main.py                   # Entry point
├── LICENSE
├── pyproject.toml
├── poetry.lock
└── README.md
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/fire-tool-streamlit.git
cd fire-tool-streamlit
```

2. Install dependencies using Poetry:
```bash
poetry install
```

Or using pip:
```bash
pip install -r requirements.txt
```

## Usage

Run the application with:
```bash
streamlit run main.py
```

## Dependencies

- streamlit
- pandas
- numpy
- matplotlib
- folium
- requests
- scikit-learn
- altair
- PIL
- Optional: geopandas, shapely (for enhanced spatial functionality)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the terms of the MIT license.
