"""
Data analysis functions for the Fire Investigation Tool.
Provides clustering, summary, and feature analysis functionality.
"""
import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

from app.core.utils import get_temp_column, get_category_display_name, get_category_singular

def create_cluster_summary(df, category="fires"):
    """
    Create summary statistics for each cluster.
    
    Args:
        df (pandas.DataFrame): DataFrame with cluster labels
        category (str): Category of data ('fires', 'flares', 'volcanoes', 'raw data')
        
    Returns:
        pandas.DataFrame: Summary statistics for each cluster
    """
    if df is None or df.empty:
        return None
    
    # Filter out noise points (-1) if category is not raw data
    if category != "raw data":
        summary_df = df[df['cluster'] >= 0].copy()
    else:
        summary_df = df.copy()
        
    if summary_df.empty:
        st.warning("No valid clusters found after filtering.")
        return None
        
    cluster_summary = (summary_df
                      .groupby('cluster')
                      .agg({
                          'latitude': ['count', 'mean'],
                          'longitude': 'mean',
                          'frp': ['mean', 'sum'],
                          'acq_date': ['min', 'max']
                      })
                      .round(3))
    
    cluster_summary.columns = [
        'Number of Points', 'Mean Latitude', 'Mean Longitude',
        'Mean FRP', 'Total FRP', 'First Detection', 'Last Detection'
    ]
    
    # Add temperature statistics based on dataset type
    temp_col = get_temp_column(df)
    if temp_col:
        temp_stats = summary_df.groupby('cluster')[temp_col].agg(['mean', 'max']).round(2)
        cluster_summary['Mean Temperature'] = temp_stats['mean']
        cluster_summary['Max Temperature'] = temp_stats['max']
    
    return cluster_summary.reset_index()

def has_multiple_dates(df, cluster_id):
    """
    Check if a cluster has data for multiple dates.
    
    Args:
        df (pandas.DataFrame): DataFrame with cluster labels
        cluster_id (int): Cluster ID to check
        
    Returns:
        bool: True if cluster has multiple dates, False otherwise
    """
    if df is None or cluster_id is None:
        return False
    cluster_data = df[df['cluster'] == cluster_id]
    unique_dates = cluster_data['acq_date'].unique()
    return len(unique_dates) > 1

def plot_feature_time_series(df, cluster_id, features):
    """
    Generate time series plots for selected features of a cluster with robust error handling.
    
    Args:
        df (pandas.DataFrame): DataFrame with cluster labels
        cluster_id (int): Cluster ID to plot
        features (list): List of feature names to plot
        
    Returns:
        tuple: (altair.Chart, dict) - Chart object and feature information dictionary
    """
    if df is None or df.empty or cluster_id is None:
        return None
    
    # Filter for the selected cluster
    cluster_data = df[df['cluster'] == cluster_id].copy()
    
    if cluster_data.empty:
        return None
    
    # Create a daily summary with mean, max for each feature
    daily_data = []
    
    for date in sorted(cluster_data['acq_date'].unique()):
        day_data = {'date': date}
        day_df = cluster_data[cluster_data['acq_date'] == date]
        
        # Calculate stats for requested features
        for feature in features:
            if feature in cluster_data.columns:
                # Calculate values with safety checks
                mean_val = day_df[feature].mean()
                max_val = day_df[feature].max()
                min_val = day_df[feature].min()
                count_val = day_df[feature].count()
                
                # Check for invalid values
                if not (pd.isna(mean_val) or np.isinf(mean_val)):
                    day_data[f'{feature}_mean'] = mean_val
                else:
                    day_data[f'{feature}_mean'] = None
                    
                if not (pd.isna(max_val) or np.isinf(max_val)):
                    day_data[f'{feature}_max'] = max_val
                else:
                    day_data[f'{feature}_max'] = None
                    
                if not (pd.isna(min_val) or np.isinf(min_val)):
                    day_data[f'{feature}_min'] = min_val
                else:
                    day_data[f'{feature}_min'] = None
                    
                day_data[f'{feature}_count'] = count_val
                
        # Only add days with valid data
        has_valid_data = False
        for key in day_data:
            if key != 'date' and day_data[key] is not None:
                has_valid_data = True
                break
                
        if has_valid_data:
            daily_data.append(day_data)
    
    # Create dataframe from daily summaries
    if not daily_data:
        return None
        
    daily_df = pd.DataFrame(daily_data)
    
    # Convert date column to datetime - with error handling
    try:
        daily_df['date'] = pd.to_datetime(daily_df['date'])
    except Exception as e:
        st.warning(f"Error converting dates: {str(e)}")
        # Use index as fallback
        daily_df['date'] = range(len(daily_df))
    
    # Feature display names and descriptions
    feature_info = {
        'frp': {
            'display_name': 'Fire Radiative Power (MW)',
            'description': 'Fire Radiative Power (FRP) measures the rate of emitted energy from a fire in megawatts (MW). Higher values indicate more intense burning.'
        },
        'bright_ti4': {
            'display_name': 'Brightness (K)',
            'description': 'Brightness Temperature is measured in Kelvin (K) and indicates how hot the fire is. Higher values indicate hotter fires.'
        }
    }
    
    # Create chart data for combined visualization - with proper filtering
    chart_data = pd.DataFrame({'date': daily_df['date']})
    
    # Add data for each selected feature, filtering out invalid values
    for feature in features:
        feature_key = f'{feature}_mean'
        if feature_key in daily_df.columns:
            feature_display = feature_info.get(feature, {}).get('display_name', feature)
            
            # First replace inf with NaN
            if feature_key in daily_df:
                daily_df[feature_key].replace([np.inf, -np.inf], np.nan, inplace=True)
            
            # Only add columns with valid data
            if feature_key in daily_df and not daily_df[feature_key].isna().all():
                chart_data[feature_display] = daily_df[feature_key]
    
    # If no valid feature data, return None
    if len(chart_data.columns) <= 1:  # Only has 'date' column
        return None
        
    # Remove any rows with NaN values to prevent chart errors
    chart_data = chart_data.dropna()
    if chart_data.empty:
        return None
        
    # Make sure date column has at least 2 unique values
    if len(chart_data['date'].unique()) < 2:
        st.info("Not enough time points to create a useful chart.")
        return None
    
    # Melt the dataframe for Altair
    try:
        melted_data = pd.melt(
            chart_data, 
            id_vars=['date'], 
            var_name='Feature', 
            value_name='Value'
        )
        
        # Final check for infinite values
        melted_data = melted_data[~np.isinf(melted_data['Value'])]
        
        # Create chart with robust error handling
        combined_chart = alt.Chart(melted_data).mark_line(point=True).encode(
            x=alt.X('date:T', title='Date'),
            y=alt.Y('Value:Q', title='Value', scale=alt.Scale(zero=False)),
            color=alt.Color('Feature:N', legend=alt.Legend(title='Feature')),
            tooltip=['date:T', 'Value:Q', 'Feature:N']
        ).properties(
            title='Fire Evolution Over Time',
            width=600,
            height=300
        ).interactive()
        
        return combined_chart, feature_info
    except Exception as e:
        st.warning(f"Error creating chart: {str(e)}")
        return None

def display_feature_exploration(df, cluster_id, category, current_date=None):
    """
    Display feature exploration interface for the selected cluster.
    
    Args:
        df (pandas.DataFrame): DataFrame with cluster labels
        cluster_id (int): Cluster ID to explore
        category (str): Category of data ('fires', 'flares', 'volcanoes', 'raw data')
        current_date (str, optional): Current date for playback mode
    """
    if df is None or df.empty or cluster_id is None:
        return
    
    # Filter data for the selected cluster
    cluster_data = df[df['cluster'] == cluster_id].copy()
    
    # If in playback mode and a date is provided, filter for that date
    if current_date is not None:
        cluster_data = cluster_data[cluster_data['acq_date'] == current_date].copy()
    
    if cluster_data.empty:
        st.warning(f"No data available for selected {get_category_display_name(category).lower()}.")
        return
    
    # Limit to only 'frp' and 'bright_ti4' features
    available_features = []
    
    if 'frp' in cluster_data.columns:
        available_features.append('frp')
        
    temp_col = get_temp_column(df)
    if temp_col and temp_col in cluster_data.columns:
        available_features.append(temp_col)
    
    # Fixed features with better names
    feature_display_names = {
        'frp': 'Fire Radiative Power',
        '