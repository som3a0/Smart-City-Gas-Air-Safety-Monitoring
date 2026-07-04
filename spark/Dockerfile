FROM apache/spark:3.5.0

USER root

RUN pip install --no-cache-dir pandas==2.0.3 numpy==1.24.4

RUN curl -fsSL \
  https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.0/spark-sql-kafka-0-10_2.12-3.5.0.jar \
  -o /opt/spark/jars/spark-sql-kafka-0-10_2.12-3.5.0.jar && \
  curl -fsSL \
  https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar \
  -o /opt/spark/jars/kafka-clients-3.4.0.jar && \
  curl -fsSL \
  https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.0/spark-token-provider-kafka-0-10_2.12-3.5.0.jar \
  -o /opt/spark/jars/spark-token-provider-kafka-0-10_2.12-3.5.0.jar && \
  curl -fsSL \
  https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar \
  -o /opt/spark/jars/commons-pool2-2.11.1.jar && \
  curl -fsSL \
  https://repo1.maven.org/maven2/com/microsoft/sqlserver/mssql-jdbc/12.4.2.jre11/mssql-jdbc-12.4.2.jre11.jar \
  -o /opt/spark/jars/mssql-jdbc-12.4.2.jre11.jar

RUN mkdir -p /opt/spark-data/checkpoints && chmod -R 777 /opt/spark-data

COPY spark_streaming.py /opt/spark-apps/spark_streaming.py
COPY entrypoint.sh      /opt/spark-apps/entrypoint.sh
RUN chmod +x /opt/spark-apps/entrypoint.sh

# Stay as root so we can write to volumes
ENTRYPOINT ["/opt/spark-apps/entrypoint.sh"]
