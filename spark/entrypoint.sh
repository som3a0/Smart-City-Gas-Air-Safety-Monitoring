#!/bin/bash
echo "⏳ Waiting 30s for all services to initialize..."
sleep 30

echo "📁 Creating required directories..."
mkdir -p /opt/spark-data/bronze/sensor_raw
mkdir -p /opt/spark-data/silver/sensor_clean
mkdir -p /opt/spark-data/gold
mkdir -p /opt/spark-data/checkpoints/bronze
mkdir -p /opt/spark-data/checkpoints/silver
mkdir -p /opt/spark-data/checkpoints/gold
chmod -R 777 /opt/spark-data

echo "✅ Starting Spark Streaming Job..."
/opt/spark/bin/spark-submit \
  --master local[*] \
  --deploy-mode client \
  --driver-memory 1g \
  --executor-memory 1g \
  /opt/spark-apps/spark_streaming.py
