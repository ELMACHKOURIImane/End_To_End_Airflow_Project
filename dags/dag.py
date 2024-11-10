from datetime import datetime, timedelta 
from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator

# Define default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),  # This now works because timedelta is imported
}

# Initialize the DAG
with DAG(
    'create_postgres_table_dag',
    default_args=default_args,
    description='A simple DAG to create a table in a Postgres database',
    schedule_interval=None,  # Run on demand
    start_date=datetime(2024, 11, 8),
    catchup=False,
) as dag:
    
    # Task to test the connection
    test_connection = PostgresOperator(
        task_id='test_connection',
        postgres_conn_id='acticls_connection',  # Replace with your actual connection ID
        sql="SELECT 1;"
    )

    # Define the task to create a table
    create_table = PostgresOperator(
        task_id='create_table',
        postgres_conn_id='acticls_connection',  # Replace with your actual connection ID
        sql="""
        CREATE TABLE IF NOT EXISTS my_table1 (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Set task dependencies if needed
    test_connection >> create_table
