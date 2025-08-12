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
    # --- CHANGE 1: Add 'Tested' to the list of required columns ---
    required_cols = [
        'Name', 'Sex', 'Event', 'Equipment', 'Country',
        'Date', 'WeightClassKg', 'Best3BenchKg', 'Tested'
    ]

    r = requests.get(DATA_URL)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(r.content)
        tmp_path = tmp.name
    with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
        csv_name = [f for f in zip_ref.namelist() if f.endswith('.csv')][0]
        extract_path = tempfile.gettempdir()
        zip_ref.extract(csv_name, extract_path)
        csv_path = f"{extract_path}/{csv_name}"
        
    df = pd.read_csv(csv_path, usecols=required_cols)
    df['Year'] = pd.to_datetime(df['Date'], errors='coerce').dt.year
    df['Best3BenchKg'] = pd.to_numeric(df['Best3BenchKg'], errors='coerce')
    
    # --- CHANGE 2: Add 'Tested' to the dropna list ---
    df = df.dropna(subset=['Best3BenchKg', 'Year', 'Country', 'WeightClassKg', 'Event', 'Tested'])

    df['Year'] = df['Year'].astype(int)
    return df

@st.cache_data
# --- CHANGE 1: Add 'tested_status' to the function signature ---
def preprocess(df, sex, event, equipment, weight_class, year, country, tested_status):
    df_filtered = df.copy()
    
    # Apply standard filters
    df_filtered = df_filtered[df_filtered['Sex'] == sex]
    
    if event != "All":
        df_filtered = df_filtered[df_filtered['Event'] == event]

    if equipment != "All":
        df_filtered = df_filtered[df_filtered['Equipment'] == equipment]
        
    if weight_class != "All":
        df_filtered = df_filtered[df_filtered['WeightClassKg'] == weight_class]

    if year != "All":
        df_filtered = df_filtered[df_filtered['Year'] == year]
        
    if country != "All":
        df_filtered = df_filtered[df_filtered['Country'] == country]
        
    # --- CHANGE 2: Add the new filtering logic for 'Tested' status ---
    if tested_status != "All":
        df_filtered = df_filtered[df_filtered['Tested'] == tested_status]
        
    if df_filtered.empty:
        return df_filtered

    df_processed = df_filtered.groupby('Name', as_index=False)['Best3BenchKg'].max()
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
    
    TRADITIONAL_MEN_CLASSES = ['All', '52', '56', '60', '67.5', '75', '82.5', '90', '100', '110', '125', '140', '140+']
    TRADITIONAL_WOMEN_CLASSES = ['All', '44', '48', '52', '56', '60', '67.5', '75', '82.5', '90', '90+']

    # --- FINALIZED: The complete and correct display mapping ---
    EVENT_DISPLAY_MAP = {
        "All": "All",
        "SBD": "Full Power",
        "B": "Bench Only",
        "BD": "Push-Pull",
        "SB": "Squat & Bench"
    }
    event_codes = list(EVENT_DISPLAY_MAP.keys())

    country_list = ["All"] + sorted(df['Country'].dropna().unique().tolist())
    year_list = ["All"] + sorted(df['Year'].dropna().unique().tolist(), reverse=True)

    # First row of filters
    col1, col2, col3 = st.columns(3)
    with col1:
        sex = st.selectbox("Sex", ["M", "F"])
    with col2:
        # This selectbox now uses the finalized mapping
        event = st.selectbox(
            "Event",
            options=event_codes,
            format_func=lambda code: EVENT_DISPLAY_MAP[code]
        )
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
        country = st.selectbox("Country 🌍", country_list, index=default_country_index)

    # --- CHANGE 1: Add a third row for the 'Tested' filter ---
    col7, col8, col9 = st.columns(3)
    with col7:
        tested_status = st.selectbox("Tested", ["All", "Yes", "No"])
        
    # --- CHANGE 2: Pass the new 'tested_status' to the preprocess function ---
    filtered_df = preprocess(df, sex, event, equipment, weight_class, year, country, tested_status)
    
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