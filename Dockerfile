# Use the official Airflow image as a base
FROM apache/airflow:2.10.3

# Switch to root user to set environment variables
USER root

# Set JAVA_HOME and PATH environment variables
ENV JAVA_HOME=/opt/jdk1.8.0_302
ENV PATH=$JAVA_HOME/bin:$PATH

# Switch back to the airflow user
USER airflow

# Install PySpark and Airflow provider for Spark
RUN pip install apache-airflow-providers-mongo
RUN pip install pandas
RUN pip install apache-airflow-providers-google google-cloud-bigquery

# Set the default command to start the airflow webserver
CMD ["bash"]