FROM apache/airflow:3.3.2-python3.12

# Spark runs on the JVM: install a headless Java runtime.
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/default-java

# Install the netbench package (the pipeline logic) into Airflow's Python.
USER airflow
COPY --chown=airflow:root pyproject.toml /opt/netbench/pyproject.toml
COPY --chown=airflow:root src /opt/netbench/src
RUN pip install --no-cache-dir /opt/netbench
