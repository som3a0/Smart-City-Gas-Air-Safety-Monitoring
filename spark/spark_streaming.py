"""
spark_streaming.py
==================
Smart City Gas & Air Safety Monitoring Platform
Spark Structured Streaming Job

Flow:
  Kafka (sensor_data_stream, 3 partitions)
       ↓
  Bronze  → Parquet  (raw data, no changes)
       ↓
  Silver  → Parquet  (cleaned + validated + enriched)
       ↓
  Gold    → SQL Server  (aggregations for Grafana)

Checkpoints:
  /opt/spark-data/checkpoints/bronze/
  /opt/spark-data/checkpoints/silver/
  /opt/spark-data/checkpoints/gold/
"""

import logging
import os
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, FloatType,
    BooleanType, DoubleType, TimestampType
)

# ============================================================
# ⚙️ CONFIGURATION
# ============================================================
KAFKA_BROKER   = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
KAFKA_TOPIC    = "sensor_data_stream"

SQLSERVER_HOST = os.environ.get("SQLSERVER_HOST",     "sqlserver")
SQLSERVER_PORT = os.environ.get("SQLSERVER_PORT",     "1433")
SQLSERVER_DB   = os.environ.get("SQLSERVER_DB",       "SmartCityDB")
SQLSERVER_USER = os.environ.get("SQLSERVER_USER",     "sa")
SQLSERVER_PASS = os.environ.get("SQLSERVER_PASSWORD", "SmartCity@2026")

JDBC_URL = (
    f"jdbc:sqlserver://{SQLSERVER_HOST}:{SQLSERVER_PORT};"
    f"databaseName={SQLSERVER_DB};"
    f"encrypt=false;"
    f"trustServerCertificate=true;"
)
JDBC_PROPS = {
    "user":   SQLSERVER_USER,
    "password": SQLSERVER_PASS,
    "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver",
}

# Storage paths
BASE_PATH       = "/opt/spark-data"
BRONZE_PATH     = f"{BASE_PATH}/bronze/sensor_raw"
SILVER_PATH     = f"{BASE_PATH}/silver/sensor_clean"
GOLD_PATH       = f"{BASE_PATH}/gold"
CHECKPOINT_BASE = f"{BASE_PATH}/checkpoints"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("SparkStreaming")


# ============================================================
# 🔧 SPARK SESSION
# ============================================================

def create_spark_session() -> SparkSession:
    return (
        SparkSession.builder
        .appName("SmartCity-Streaming")
        .config("spark.sql.shuffle.partitions", "3")
        .config("spark.streaming.stopGracefullyOnShutdown", "true")
        .config("spark.sql.streaming.checkpointLocation", CHECKPOINT_BASE)
        # Parquet optimizations
        .config("spark.sql.parquet.compression.codec", "snappy")
        .config("spark.sql.parquet.mergeSchema", "false")
        .getOrCreate()
    )


# ============================================================
# 📐 KAFKA MESSAGE SCHEMA (26 fields)
# ============================================================

SENSOR_SCHEMA = StructType([
    StructField("event_id",           StringType(),  True),
    StructField("timestamp",          StringType(),  True),
    StructField("batch_id",           IntegerType(), True),
    StructField("house_id",           StringType(),  True),
    StructField("governorate",        StringType(),  True),
    StructField("zone",               StringType(),  True),
    StructField("latitude",           DoubleType(),  True),
    StructField("longitude",          DoubleType(),  True),
    StructField("building_type",      StringType(),  True),
    StructField("year_built",         IntegerType(), True),
    StructField("risk_profile",       StringType(),  True),
    StructField("has_gas_connection", BooleanType(), True),
    StructField("temperature_c",      FloatType(),   True),
    StructField("humidity_pct",       FloatType(),   True),
    StructField("methane_ppm",        FloatType(),   True),
    StructField("lpg_ppm",            FloatType(),   True),
    StructField("gas_pressure_kpa",   FloatType(),   True),
    StructField("co_ppm",             FloatType(),   True),
    StructField("smoke_level",        FloatType(),   True),
    StructField("aqi",                IntegerType(), True),
    StructField("co2_ppm",            IntegerType(), True),
    StructField("pm25_ugm3",          FloatType(),   True),
    StructField("pm10_ugm3",          FloatType(),   True),
    StructField("alert_status",       StringType(),  True),
    StructField("risk_score",         FloatType(),   True),
    StructField("is_anomaly",         IntegerType(), True),
])


# ============================================================
# 📥 READ FROM KAFKA
# ============================================================

def read_kafka_stream(spark: SparkSession):
    """
    Reads the sensor_data_stream topic from Kafka.
    Each Kafka message value is a JSON string.
    Returns a parsed DataFrame.
    """
    raw = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BROKER)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )

    # Parse JSON value → structured DataFrame
    parsed = (
        raw
        .select(
            F.col("partition").alias("kafka_partition"),
            F.col("offset").alias("kafka_offset"),
            F.from_json(
                F.col("value").cast("string"),
                SENSOR_SCHEMA
            ).alias("data")
        )
        .select("kafka_partition", "kafka_offset", "data.*")
    )

    # Convert timestamp string → proper timestamp type
    parsed = parsed.withColumn(
        "event_time",
        F.to_timestamp(F.col("timestamp"), "yyyy-MM-dd HH:mm:ss")
    )

    return parsed


# ============================================================
# 🥉 BRONZE — Raw data, no transformations
# ============================================================

def start_bronze_stream(parsed_df):
    """
    Writes raw data to Parquet files exactly as received.
    Partitioned by date and hour for efficient querying.
    """

    def write_bronze(batch_df, batch_id):
        if batch_df.isEmpty():
            return

        rows = batch_df.count()
        log.info(f"  🥉 Bronze batch #{batch_id}: {rows:,} rows")

        (
            batch_df
            .withColumn("ingested_at", F.current_timestamp())
            .withColumn("year",  F.year("event_time"))
            .withColumn("month", F.month("event_time"))
            .withColumn("day",   F.dayofmonth("event_time"))
            .withColumn("hour",  F.hour("event_time"))
            .write
            .mode("append")
            .partitionBy("year", "month", "day", "hour")
            .parquet(BRONZE_PATH)
        )

    return (
        parsed_df.writeStream
        .foreachBatch(write_bronze)
        .outputMode("append")
        .option("checkpointLocation", f"{CHECKPOINT_BASE}/bronze")
        .trigger(processingTime="10 seconds")
        .start()
    )


# ============================================================
# 🥈 SILVER — Cleaned + Validated + Enriched
# ============================================================

def start_silver_stream(parsed_df):
    """
    Applies data quality rules and feature engineering.
    Writes cleaned data to Parquet.
    """

    def write_silver(batch_df, batch_id):
        if batch_df.isEmpty():
            return

        # ── Data Cleaning ────────────────────────────────────
        clean = (
            batch_df
            # Drop rows with null house_id or timestamp
            .dropna(subset=["house_id", "event_time"])
            # Cap sensor values to valid ranges
            .withColumn("temperature_c",
                F.when(F.col("temperature_c").between(-10, 65),
                       F.col("temperature_c")).otherwise(None))
            .withColumn("humidity_pct",
                F.when(F.col("humidity_pct").between(0, 100),
                       F.col("humidity_pct")).otherwise(None))
            .withColumn("methane_ppm",
                F.when(F.col("methane_ppm") >= 0,
                       F.col("methane_ppm")).otherwise(0.0))
            .withColumn("aqi",
                F.when(F.col("aqi").between(0, 500),
                       F.col("aqi")).otherwise(None))
            # Fill nulls with safe defaults
            .fillna({
                "temperature_c":  25.0,
                "humidity_pct":   50.0,
                "methane_ppm":    0.0,
                "lpg_ppm":        0.0,
                "co_ppm":         0.0,
                "smoke_level":    0.0,
                "aqi":            50,
                "co2_ppm":        400,
                "pm25_ugm3":      10.0,
                "pm10_ugm3":      20.0,
            })
        )

        # ── Feature Engineering ──────────────────────────────
        enriched = (
            clean
            # Building age
            .withColumn("building_age",
                F.lit(2026) - F.col("year_built"))

            # Gas leak flag
            .withColumn("gas_leak_flag",
                F.when(
                    (F.col("methane_ppm") > 350) |
                    (F.col("lpg_ppm") > 300),
                    True
                ).otherwise(False))

            # Fire risk flag
            .withColumn("fire_risk_flag",
                F.when(
                    (F.col("temperature_c") > 50) &
                    (F.col("smoke_level") > 50),
                    True
                ).otherwise(False))

            # Air pollution flag
            .withColumn("pollution_flag",
                F.when(F.col("aqi") > 150, True).otherwise(False))

            # Risk level category
            .withColumn("risk_level",
                F.when(F.col("risk_score") >= 70, "CRITICAL")
                 .when(F.col("risk_score") >= 40, "HIGH")
                 .when(F.col("risk_score") >= 20, "MEDIUM")
                 .otherwise("LOW"))

            # Date parts for partitioning
            .withColumn("year",  F.year("event_time"))
            .withColumn("month", F.month("event_time"))
            .withColumn("day",   F.dayofmonth("event_time"))
            .withColumn("hour",  F.hour("event_time"))

            .withColumn("processed_at", F.current_timestamp())
        )

        rows = enriched.count()
        log.info(f"  🥈 Silver batch #{batch_id}: {rows:,} rows")

        (
            enriched.write
            .mode("append")
            .partitionBy("year", "month", "day", "hour")
            .parquet(SILVER_PATH)
        )

    return (
        parsed_df.writeStream
        .foreachBatch(write_silver)
        .outputMode("append")
        .option("checkpointLocation", f"{CHECKPOINT_BASE}/silver")
        .trigger(processingTime="10 seconds")
        .start()
    )


# ============================================================
# 🥇 GOLD — Aggregations → SQL Server
# ============================================================

def start_gold_stream(parsed_df):
    """
    Computes zone-level and city-level aggregations.
    Writes results to SQL Server for Grafana.
    """

    def write_gold(batch_df, batch_id):
        if batch_df.isEmpty():
            return

        now = F.current_timestamp()

        # ── 1. Zone-level stats ──────────────────────────────
        zone_stats = (
            batch_df
            .groupBy("governorate", "zone")
            .agg(
                F.avg("methane_ppm")   .alias("avg_methane_ppm"),
                F.max("methane_ppm")   .alias("max_methane_ppm"),
                F.avg("temperature_c") .alias("avg_temperature_c"),
                F.avg("smoke_level")   .alias("avg_smoke_level"),
                F.avg("co_ppm")        .alias("avg_co_ppm"),
                F.avg("aqi")           .alias("avg_aqi"),
                F.max("aqi")           .alias("max_aqi"),
                F.avg("risk_score")    .alias("avg_risk_score"),
                F.max("risk_score")    .alias("max_risk_score"),
                F.count("*")           .alias("total_readings"),
                F.sum(F.when(F.col("alert_status") == "CRITICAL", 1).otherwise(0))
                 .alias("critical_count"),
                F.sum(F.when(F.col("alert_status") == "WARNING",  1).otherwise(0))
                 .alias("warning_count"),
                F.sum("is_anomaly")    .alias("anomaly_count"),
            )
            .withColumn("snapshot_time", now)
            .withColumn("batch_id", F.lit(batch_id))
            .withColumn("zone_risk_level",
                F.when(F.col("critical_count") > 0,                        "CRITICAL")
                 .when(F.col("warning_count") > 0,                         "WARNING")
                 .when(F.col("avg_risk_score") >= 15.0,                    "MEDIUM")
                 .otherwise("LOW"))
        )

        # ── 2. Governorate-level stats ───────────────────────
        gov_stats = (
            batch_df
            .groupBy("governorate")
            .agg(
                F.avg("risk_score")    .alias("avg_risk_score"),
                F.max("risk_score")    .alias("max_risk_score"),
                F.avg("methane_ppm")   .alias("avg_methane_ppm"),
                F.avg("aqi")           .alias("avg_aqi"),
                F.avg("temperature_c") .alias("avg_temperature_c"),
                F.count("*")           .alias("total_houses"),
                F.sum(F.when(F.col("alert_status") == "CRITICAL", 1).otherwise(0))
                 .alias("critical_count"),
                F.sum(F.when(F.col("alert_status") == "WARNING",  1).otherwise(0))
                 .alias("warning_count"),
                F.sum("is_anomaly")    .alias("total_anomalies"),
            )
            .withColumn("snapshot_time", now)
            .withColumn("batch_id", F.lit(batch_id))
            .withColumn("gov_risk_level",
                F.when(F.col("critical_count") >= 2,                       "CRITICAL")
                 .when((F.col("warning_count") >= 3) | (F.col("critical_count") == 1), "WARNING")
                 .when(F.col("avg_risk_score") >= 12.0,                    "MEDIUM")
                 .otherwise("LOW"))
        )

        # ── 3. Active alerts ─────────────────────────────────
        active_alerts = (
            batch_df
            .filter(F.col("alert_status").isin("WARNING", "CRITICAL"))
            .select(
                "event_id", "house_id", "governorate", "zone",
                "latitude", "longitude", "building_type",
                "alert_status", "risk_score",
                "methane_ppm", "smoke_level", "co_ppm",
                "temperature_c", "aqi", "is_anomaly",
                F.col("event_time").alias("alert_time"),
            )
            .withColumn("batch_id", F.lit(batch_id))
        )

        # ── Write to SQL Server ──────────────────────────────
        def write_jdbc(df, table):
            (df.write
               .format("jdbc")
               .option("url",      JDBC_URL)
               .option("dbtable",  table)
               .option("driver",   JDBC_PROPS["driver"])
               .option("user",     JDBC_PROPS["user"])
               .option("password", JDBC_PROPS["password"])
               .mode("append")
               .save())

        write_jdbc(zone_stats,    "gold.zone_stats")
        write_jdbc(gov_stats,     "gold.gov_stats")
        write_jdbc(active_alerts, "gold.active_alerts")

        log.info(
            f"  🥇 Gold batch #{batch_id}: "
            f"zones={zone_stats.count()} "
            f"govs={gov_stats.count()} "
            f"alerts={active_alerts.count()}"
        )

    return (
        parsed_df.writeStream
        .foreachBatch(write_gold)
        .outputMode("append")
        .option("checkpointLocation", f"{CHECKPOINT_BASE}/gold")
        .trigger(processingTime="30 seconds")
        .start()
    )


# ============================================================
# 🚀 MAIN
# ============================================================

def main():
    print("═" * 60)
    print("  🏙️  Smart City — Spark Structured Streaming")
    print("  📊  Bronze (Parquet) → Silver (Parquet) → Gold (SQL Server)")
    print("═" * 60)
    print(f"  Kafka  : {KAFKA_BROKER} → {KAFKA_TOPIC}")
    print(f"  Bronze : {BRONZE_PATH}")
    print(f"  Silver : {SILVER_PATH}")
    print(f"  Gold   : SQL Server → {SQLSERVER_HOST}:{SQLSERVER_PORT}")
    print("═" * 60)

    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    log.info(f"Spark version: {spark.version}")

    # Read from Kafka
    parsed_df = read_kafka_stream(spark)

    # Start all 3 layers
    bronze_stream = start_bronze_stream(parsed_df)
    silver_stream = start_silver_stream(parsed_df)
    gold_stream   = start_gold_stream(parsed_df)

    print("\n  ✅ All streams running:")
    print("  ├─ Bronze → Parquet  (every 10s)")
    print("  ├─ Silver → Parquet  (every 10s)")
    print("  └─ Gold   → SQL Server  (every 30s)")
    print(f"\n  🌐 Spark UI → http://localhost:8081")
    print("\n  Press Ctrl+C to stop.\n")

    # Wait for all streams
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
