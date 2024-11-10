import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from google.cloud import bigquery
import plotly.express as px
from collections import Counter

st.set_page_config(page_title="Academic Articles Analysis", layout="wide")

# Create API client
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials)

# Perform query with caching
@st.cache_data(ttl=600)
def run_query(query):
    try:
        query_job = client.query(query)
        rows_raw = query_job.result()
        rows = [dict(row) for row in rows_raw]
        return rows
    except Exception as e:
        st.error(f"Error querying BigQuery: {str(e)}")
        return []

# Get data
query = """
SELECT 
    COALESCE(journal, 'Unknown') as journal,
    COALESCE(indexation, 'Unknown') as indexation,
    COALESCE(publication, 'Unknown') as publication,
    COALESCE(doi, 'Unknown') as doi,
    COALESCE(titre, 'Unknown') as titre,
    COALESCE(chercheurs, 'Unknown') as chercheurs,
    COALESCE(laboratoires, 'Unknown') as laboratoires,
    COALESCE(abstract, 'Unknown') as abstract,
    ISSN,
    quartile,
    COALESCE(pays, 'Unknown') as pays
FROM `buoyant-genre-441010-b2.AcademicAnalyzer.Articles`
WHERE pays IS NOT NULL  -- Only include records with country information
"""

rows = run_query(query)

if not rows:
    st.error("No data available. Please check your connection and try again.")
    st.stop()

# Process the data
def process_quartile_data(rows):
    processed_data = []
    for row in rows:
        # Check if quartile data exists and is not empty
        if row.get('quartile') and isinstance(row['quartile'], list):
            for q in row['quartile']:
                # Verify that both année and quartil exist and are not null
                if q.get('année') and q.get('quartil'):
                    try:
                        # Convert quartile to float for proper sorting
                        quartile_value = float(q['quartil'])
                        processed_data.append({
                            'pays': row['pays'],
                            'année': q['année'],
                            'quartile': quartile_value,
                            'journal': row['journal']
                        })
                    except (ValueError, TypeError):
                        continue  # Skip invalid quartile values
    return pd.DataFrame(processed_data)

# Create DataFrame
df = process_quartile_data(rows)

if df.empty:
    st.error("No valid data after processing. Please check your data format.")
    st.stop()

# Main title
st.title("Academic Articles Analysis Dashboard")

# Sidebar filters
st.sidebar.header("Filters")

# Get available years and countries (excluding null/invalid values)
available_years = sorted(df['année'].unique())
available_countries = sorted(df['pays'].unique())

if not available_years or not available_countries:
    st.error("No valid years or countries found in the data.")
    st.stop()

selected_years = st.sidebar.multiselect(
    "Select Years",
    options=available_years,
    default=available_years
)

selected_countries = st.sidebar.multiselect(
    "Select Countries",
    options=available_countries,
    default=available_countries[:5] if len(available_countries) > 5 else available_countries
)

# Filter data based on selections
filtered_df = df[
    (df['année'].isin(selected_years)) &
    (df['pays'].isin(selected_countries))
]

if filtered_df.empty:
    st.warning("No data available for the selected filters. Please adjust your selection.")
    st.stop()

# Create two columns for the visualizations
col1, col2 = st.columns(2)

with col1:
    st.subheader("Articles by Country and Quartile")
    try:
        fig1 = px.scatter(filtered_df,
                         x="pays",
                         y="quartile",
                         color="année",
                         size_max=60,
                         title="Distribution of Articles by Country and Quartile")
        st.plotly_chart(fig1, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating scatter plot: {str(e)}")

with col2:
    st.subheader("Quartile Distribution by Country")
    try:
        fig2 = px.histogram(filtered_df,
                           x="pays",
                           color="quartile",
                           barmode="group",
                           title="Number of Articles by Country and Quartile")
        st.plotly_chart(fig2, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating histogram: {str(e)}")

# Create a third visualization for temporal analysis
st.subheader("Temporal Evolution of Publications")
try:
    temporal_df = filtered_df.groupby(['année', 'pays']).size().reset_index(name='count')
    fig3 = px.line(temporal_df,
                   x="année",
                   y="count",
                   color="pays",
                   title="Publication Trends Over Time")
    st.plotly_chart(fig3, use_container_width=True)
except Exception as e:
    st.error(f"Error creating line chart: {str(e)}")

# Summary statistics
st.subheader("Summary Statistics")
col3, col4, col5 = st.columns(3)

with col3:
    total_articles = len(filtered_df)
    st.metric("Total Articles", total_articles)

with col4:
    try:
        avg_quartile = filtered_df['quartile'].mean()
        st.metric("Average Quartile", f"{avg_quartile:.2f}")
    except Exception as e:
        st.metric("Average Quartile", "N/A")

with col5:
    try:
        top_country = filtered_df['pays'].value_counts().index[0]
        st.metric("Most Published Country", top_country)
    except Exception as e:
        st.metric("Most Published Country", "N/A")

# Add download capability
st.subheader("Download Data")
csv = filtered_df.to_csv(index=False)
st.download_button(
    label="Download filtered data as CSV",
    data=csv,
    file_name="academic_articles_data.csv",
    mime="text/csv"
)

# Data table with error handling
st.subheader("Detailed Data View")
try:
    st.dataframe(filtered_df.style.format({"quartile": "{:.2f}"}))
except Exception as e:
    st.error(f"Error displaying data table: {str(e)}")