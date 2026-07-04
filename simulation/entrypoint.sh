#!/bin/bash
echo "⏳ Waiting 15s for Kafka to fully initialize..."
sleep 15
echo "✅ Starting IoT Producer..."
python3 kafka_producer.py
