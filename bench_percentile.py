import streamlit as st
import pandas as pd
import numpy as np
import tempfile
import zipfile
import requests

# URL for latest OpenPowerlifting dataset
DATA_URL = "https://openpowerlifting.gitlab.io/opl-csv/files/openpowerlifting-latest.zip"

@st.cache_data
def load_data():
    """
    Downloads, extracts, and loads the OpenPowerlifting.org dataset efficiently.
    This function is cached so it only runs once.
    """
    # --- EFFICIENT CHANGE 1: Define required columns beforehand ---
    # This tells pandas to only load the data we actually need.
    required_cols = [
        'Name', 'Sex', 'Event', 'Equipment', 'Country',
        'Date', 'WeightClassKg', 'Best3BenchKg'
    ]

    # Download dataset from the URL
    r = requests.get(DATA_URL)
    
    # Use a temporary file to store the downloaded zip archive
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(r.content)
        tmp_path = tmp.name

    # Extract the CSV file from the ZIP archive
    with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
        csv_name = [f for f in zip_ref.namelist() if f.endswith('.csv')][0]
        extract_path = tempfile.gettempdir()
        zip_ref.extract(csv_name, extract_path)
        csv_path = f"{extract_path}/{csv_name}"

    # --- EFFICIENT CHANGE 2: Use `usecols` to save memory ---
    # Now, pandas will only read the columns specified in required_cols.
    # The `low_memory=False` argument is no longer needed.
    df = pd.read_csv(csv_path, usecols=required_cols)

    # The rest of your processing remains the same
    df['Year'] = pd.to_datetime(df['Date'], errors='coerce').dt.year
    df['Best3BenchKg'] = pd.to_numeric(df['Best3BenchKg'], errors='coerce')
    df = df.dropna(subset=['Best3BenchKg', 'Year', 'Country', 'WeightClassKg'])
    df['Year'] = df['Year'].astype(int)

    return df

@st.cache_data
def preprocess(df, sex, event, equipment, weight_class, year, country):
    # Add a mapping from dropdown options to data codes
    EVENT_MAP = {
        "Full Power": "SBD",
        "Bench Only": "B",
        "Push-Pull": "BD"
    }

    df_filtered = df.copy()
    
    # Apply standard filters
    df_filtered = df_filtered[df_filtered['Sex'] == sex]
    
    # Use the mapping to filter correctly
    if event != "All":
        event_code = EVENT_MAP.get(event)
        df_filtered = df_filtered[df_filtered['Event'] == event_code]

    if equipment != "All":
        df_filtered = df_filtered[df_filtered['Equipment'] == equipment]
        
    if weight_class != "All":
        df_filtered = df_filtered[df_filtered['WeightClassKg'] == weight_class]

    # Apply year and country filters
    if year != "All":
        df_filtered = df_filtered[df_filtered['Year'] == year]
    if country != "All":
        df_filtered = df_filtered[df_filtered['Country'] == country]
        
    df_processed = df_filtered.groupby('Name', as_index=False)['Best3BenchKg'].max()
    
    # --- THE FIX IS ON THIS LINE ---
    df_processed = df_processed.sort_values(by='Best3BenchKg').reset_index(drop=True)

    return df_processed

def main():
    """
    The main function that builds and runs the Streamlit application.
    """
    st.set_page_config(page_title="Bench Press Percentile Calculator", page_icon="🏋️")
    st.title("🏋️ Bench Press Percentile Calculator")
    st.write("Based on the latest **OpenPowerlifting.org** dataset.")
    
    # Show a spinner message during the long initial data load
    with st.spinner('Performing first-time setup... (This may take a few minutes)'):
        df = load_data()
    st.success('Data loaded successfully!')

    st.header("Select Your Category")
    
    # Define the standard IPF weight classes for men and women
    TRADITIONAL_MEN_CLASSES = ['All', '52', '56', '60', '67.5', '75', '82.5', '90', '100', '110', '125', '140', '140+']
    TRADITIONAL_WOMEN_CLASSES = ['All', '44', '48', '52', '56', '60', '67.5', '75', '82.5', '90', '90+']

    # Create lists for the other filters as before
    country_list = ["All"] + sorted(df['Country'].dropna().unique().tolist())
    year_list = ["All"] + sorted(df['Year'].dropna().unique().tolist(), reverse=True)

    # First row of filters
    col1, col2, col3 = st.columns(3)
    with col1:
        sex = st.selectbox("Sex", ["M", "F"])
    with col2:
        event = st.selectbox("Event", ["All", "SBD", "B", "BD"])
    with col3:
        equipment = st.selectbox("Equipment", ["All", "Raw", "Wraps", "Single-ply", "Multi-ply"])

    # Dynamically choose the weight class list based on the selected sex
    if sex == 'M':
        weight_class_list = TRADITIONAL_MEN_CLASSES
    else:
        weight_class_list = TRADITIONAL_WOMEN_CLASSES

     # Find the index of 'USA' in the list to set it as the default
    try:
        default_country_index = country_list.index('USA')
    except ValueError:
        default_country_index = 0 # If 'USA' isn't found, default to 'All'

    # Second row of filters
    col4, col5, col6 = st.columns(3)
    with col4:
        weight_class = st.selectbox("Weight Class (kg) 💪", weight_class_list)
    with col5:
        year = st.selectbox("Year 📅", year_list)
    with col6:
        # Use the 'index' parameter to set the default value
        country = st.selectbox("Country 🌍", country_list, index=default_country_index)
    # Preprocess the data using all the selected filters
    filtered_df = preprocess(df, sex, event, equipment, weight_class, year, country)
    
    # Input for the user's bench press
    st.header("Calculate Your Percentile")
    bench_input = st.number_input("Enter your best bench press (kg):", min_value=0.0, step=1.0)

    # Display the results
    if bench_input > 0:
        if not filtered_df.empty:
            rank = (filtered_df['Best3BenchKg'] <= bench_input).sum()
            total_lifters = len(filtered_df)
            percentile = (rank / total_lifters) * 100 if total_lifters > 0 else 0

            st.subheader(f"Your bench is in the **{percentile:.2f}th percentile**")
            st.write(f"You can lift more than approximately **{int(rank):,}** out of **{int(total_lifters):,}** lifters in this category.")
            st.progress(percentile / 100)
        else:
            st.warning("No data available for the selected filters. Please try a different combination.")
    
    # Add the footer with data attribution
    st.markdown("---")
    st.caption("This page uses data from the OpenPowerlifting project, https://www.openpowerlifting.org.")
    st.caption("You may download a copy of the data at https://data.openpowerlifting.org.")

# Standard entry point for a Python script
if __name__ == "__main__":
    main()