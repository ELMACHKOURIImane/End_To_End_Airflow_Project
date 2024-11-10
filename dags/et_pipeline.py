from datetime import datetime
from airflow import DAG
from airflow.providers.mongo.hooks.mongo import MongoHook
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
import pandas as pd
import os

# Function to fetch data from MongoDB and convert it to a DataFrame
def fetch_data_from_mongo():
    # Fetch data and save to /tmp/mongo_data.csv
    hook = MongoHook(conn_id='mongo_default')
    db = 'AcademicAnalyzer'
    collection = hook.get_conn()[db]['Articles']
    data_list = list(collection.find({}, {'_id': 0}))
    df = pd.DataFrame(data_list)
    file_path = '/tmp/mongo_data.csv'
    df.to_csv(file_path, index=False)
    return file_path

# Function to configure BigQuery load job
def gcp_load(file_path, **kwargs):
    if not file_path or not isinstance(file_path, str):
        raise ValueError("Invalid file path provided to gcp_load.")

    job = BigQueryInsertJobOperator(
        task_id='load_data',
        configuration={
            "load": {
                "sourceUris": [f"gs://my-bucket-name/{os.path.basename(file_path)}"],
                "destinationTable": {
                    "projectId": "buoyant-genre-441010-b2",
                    "datasetId": "my_dataset",
                    "tableId": "my_table"
                },
                "sourceFormat": "CSV",
                "writeDisposition": "WRITE_TRUNCATE",
            }
        },
        gcp_conn_id='gcp_key_in_connection',
        dag=kwargs['dag'],
    )
    job.execute(kwargs)

# DAG and task definitions
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2024, 11, 9),
}

dag = DAG(
    'mongodb_atlas_fetch_load_data',
    default_args=default_args,
    description='Fetch data from MongoDB Atlas and load to Google BigQuery',
    schedule_interval=None,
)

fetch_data_task = PythonOperator(
    task_id='fetch_data',
    python_callable=fetch_data_from_mongo,
    dag=dag,
)

load_data_task = PythonOperator(
    task_id='load_data',
    python_callable=lambda **kwargs: gcp_load(kwargs['ti'].xcom_pull(task_ids='fetch_data'), **kwargs),
    provide_context=True,
    dag=dag,
)

fetch_data_task 
