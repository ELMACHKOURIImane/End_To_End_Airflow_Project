from datetime import datetime
from airflow import DAG
from airflow.providers.mongo.hooks.mongo import MongoHook
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook
import pandas as pd
import json
import os
from google.cloud import bigquery

# Function to fetch data from MongoDB and convert it to a JSON file
def fetch_data_from_mongo():
    # Fetch data from MongoDB
    hook = MongoHook(conn_id='mongo_default')
    db = 'AcademicAnalyzer'
    collection = hook.get_conn()[db]['Articles']
    
    # Projection to exclude 'ISSN', 'quartile' and 'pays'
    projection = {
        '_id': 0,
        'ISSN': 0,
        'quartile': 0,
        'pays': 0
    }
    
    # Extract data excluding certain fields
    data_list = list(collection.find({}, projection))
    
    # Write each document as a separate line
    file_path = '/tmp/mongo_data.json'
    with open(file_path, 'w') as json_file:
        for document in data_list:
            json.dump(document, json_file, default=str)
            json_file.write('\n')  # Write a newline after each document
    
    return file_path

# Function to load data to Google Cloud Storage (GCS)
def load_data_to_gcs(local_file_path: str, bucket_name: str, object_name: str):
    gcs_hook = GCSHook()
    gcs_hook.upload(bucket_name, object_name, local_file_path)
    return f"gs://{bucket_name}/{object_name}"


# Function to load data to BigQuery
def load_data_to_bigquery(mongo_data_file_path: str, dataset_id: str, table_id: str):
    bq_hook = BigQueryHook()
    client = bigquery.Client()

    # Bucket name and object name in GCS
    bucket_name = "airflow_bucket_name"
    object_name = "transformed_data/mongo_data.json"

    # Upload file to GCS
    gcs_hook = GCSHook()
    gcs_hook.upload(bucket_name, object_name, mongo_data_file_path)

    # Define schema for BigQuery based on MongoDB fields
    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("journal", "STRING"),
            bigquery.SchemaField("indexation", "STRING"),
            bigquery.SchemaField("publication", "STRING"),
            bigquery.SchemaField("doi", "STRING"),
            bigquery.SchemaField("titre", "STRING"),
            bigquery.SchemaField("chercheurs", "STRING"),
            bigquery.SchemaField("laboratoires", "STRING"),
            bigquery.SchemaField("abstract", "STRING"),
        ],
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,  # Format JSON line by line
        write_disposition="WRITE_APPEND",  # Append new data without overwriting
    )

    # URI of the file in GCS
    uri = f"gs://{bucket_name}/{object_name}"

    # Load data from GCS into BigQuery
    load_job = client.load_table_from_uri(uri, f"{dataset_id}.{table_id}", job_config=job_config)
    load_job.result()  # Wait for the job to complete

    return f"Data loaded to BigQuery: {dataset_id}.{table_id}"

# DAG and task definitions
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2024, 11, 9),
}

dag = DAG(
    'mongodb_atlas_fetch_load',
    default_args=default_args,
    description='Fetch data from MongoDB Atlas and load to Google BigQuery',
    schedule_interval=None,
)

# Task for fetching data from MongoDB
fetch_data_task = PythonOperator(
    task_id='fetch_data',
    python_callable=fetch_data_from_mongo,
    dag=dag,
)

# Task for loading and validating data
def load_and_validate():
    local_file_path = fetch_data_from_mongo()  # Get the file path from MongoDB task
    gcs_uri = load_data_to_gcs(local_file_path, "airflow_bucket_name", "raw_data/api_combined_data.json")
    return gcs_uri

load_and_validate_task = PythonOperator(
    task_id='load_and_validate',
    python_callable=load_and_validate,
    dag=dag,
)

# Task for loading data into BigQuery
def load_to_bigquery():
    local_file_path = fetch_data_from_mongo()  # Get the file path from MongoDB task
    load_data_to_bigquery(local_file_path, "arcticls_dataset", "Articls")

load_to_bigquery_task = PythonOperator(
    task_id='load_to_bigquery',
    python_callable=load_to_bigquery,
    dag=dag,
)

# Set task dependencies
fetch_data_task >> load_and_validate_task >> load_to_bigquery_task
