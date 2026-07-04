"""
kafka_producer.py  v3
Smart City Gas & Air Safety Monitoring Platform

anomaly_rate = 0.004 → ~1% critical after risk multipliers
"""

import json
import time
import uuid
import logging
import os
from datetime import datetime

from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from house_state import build_houses
from utils import calculate_alert_status, calculate_risk_score

CONFIG = {
    "kafka_bootstrap_servers": os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    "topic":            "sensor_data_stream",
    "num_houses":       3000,
    "interval_seconds": 30,
    "random_seed":      42,
    "anomaly_rate":     0.004,   # 0.4% base → ~1% effective after risk multipliers
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("KafkaProducer")


def create_producer(retries: int = 15) -> KafkaProducer:
    for attempt in range(1, retries + 1):
        try:
            p = KafkaProducer(
                bootstrap_servers=CONFIG["kafka_bootstrap_servers"],
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retries=3,
                linger_ms=5,
                batch_size=32768,
                compression_type="gzip",
            )
            log.info(f"✅ Connected to Kafka @ {CONFIG['kafka_bootstrap_servers']}")
            return p
        except NoBrokersAvailable:
            log.warning(f"⏳ Kafka not ready ({attempt}/{retries}) — retry in 5s...")
            time.sleep(5)
    raise ConnectionError("❌ Could not connect to Kafka.")


def send_batch(producer, houses, batch_id):
    now   = datetime.now()
    ts    = now.strftime("%Y-%m-%d %H:%M:%S")
    hour  = now.hour
    month = now.month

    stats = {"sent":0,"errors":0,"CRITICAL":0,"WARNING":0,"NORMAL":0,"anomalies":0}

    for house in houses:
        readings = house.update(hour=hour, month=month, anomaly_rate=CONFIG["anomaly_rate"])

        alert = calculate_alert_status(
            readings["methane_ppm"], readings["lpg_ppm"],
            readings["co2_ppm"],     readings["smoke_level"],
            readings["aqi"],         readings["co_ppm"],
            readings["temperature_c"],
        )
        risk_score = calculate_risk_score(
            readings["methane_ppm"], readings["lpg_ppm"],
            readings["co2_ppm"],     readings["smoke_level"],
            readings["aqi"],         readings["co_ppm"],
            readings["temperature_c"], house.risk_profile,
        )

        message = {
            "event_id":           str(uuid.uuid4()),
            "timestamp":          ts,
            "batch_id":           batch_id,
            "house_id":           house.house_id,
            "governorate":        house.governorate,
            "zone":               house.zone,
            "latitude":           house.latitude,
            "longitude":          house.longitude,
            "building_type":      house.building_type,
            "year_built":         house.year_built,
            "risk_profile":       house.risk_profile,
            "has_gas_connection": house.has_gas_connection,
            "temperature_c":      readings["temperature_c"],
            "humidity_pct":       readings["humidity_pct"],
            "methane_ppm":        readings["methane_ppm"],
            "lpg_ppm":            readings["lpg_ppm"],
            "gas_pressure_kpa":   readings["gas_pressure_kpa"],
            "co_ppm":             readings["co_ppm"],
            "smoke_level":        readings["smoke_level"],
            "aqi":                readings["aqi"],
            "co2_ppm":            readings["co2_ppm"],
            "pm25_ugm3":          readings["pm25_ugm3"],
            "pm10_ugm3":          readings["pm10_ugm3"],
            "alert_status":       alert,
            "risk_score":         risk_score,
            "is_anomaly":         readings["is_anomaly"],
        }

        try:
            producer.send(CONFIG["topic"], key=house.house_id, value=message)
            stats["sent"]      += 1
            stats[alert]       += 1
            stats["anomalies"] += readings["is_anomaly"]
        except Exception as e:
            log.error(f"Send error [{house.house_id}]: {e}")
            stats["errors"] += 1

    producer.flush()
    return stats


def print_summary(batch_num, stats, elapsed, houses):
    total = stats["sent"] + stats["errors"]
    print(f"\n{'═'*60}")
    print(f"  📡 Batch #{batch_num:04d}  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'═'*60}")
    print(f"  Houses    : {total:,}")
    print(f"  ├ CRITICAL : {stats['CRITICAL']:,}  ({100*stats['CRITICAL']/max(total,1):.1f}%)")
    print(f"  ├ WARNING  : {stats['WARNING']:,}  ({100*stats['WARNING']/max(total,1):.1f}%)")
    print(f"  └ NORMAL   : {stats['NORMAL']:,}  ({100*stats['NORMAL']/max(total,1):.1f}%)")
    print(f"  Anomalies : {stats['anomalies']:,}")
    print(f"  Time      : {elapsed:.2f}s  |  Next in {CONFIG['interval_seconds']}s")
    active = [h for h in houses if h.anomaly_active]
    if active:
        print(f"\n  🚨 Active Anomalies ({len(active)}):")
        for h in active[:5]:
            print(f"     [{h.governorate}/{h.zone}] {h.house_id} "
                  f"type={h.anomaly_type} CH4={h.methane_ppm:.1f}")
    print(f"{'═'*60}")


def run():
    print("═" * 60)
    print("  🏙️  Smart City — Kafka Producer  v3")
    print(f"  📨  Topic     : {CONFIG['topic']}")
    print(f"  🏠  Houses    : {CONFIG['num_houses']:,}")
    print(f"  ⏱️   Interval  : {CONFIG['interval_seconds']}s")
    print(f"  🚨  Anomaly   : {CONFIG['anomaly_rate']*100:.1f}%  base rate")
    print("═" * 60)

    producer  = create_producer()
    print(f"\n⏳ Building {CONFIG['num_houses']:,} house states...")
    houses    = build_houses(CONFIG["num_houses"], seed=CONFIG["random_seed"])
    print(f"\n  🌐 Kafka UI → http://localhost:8080")
    print(f"  Starting in 3 seconds...\n")
    time.sleep(3)

    batch_num  = 1
    total_sent = 0

    try:
        while True:
            t0      = time.time()
            stats   = send_batch(producer, houses, batch_id=batch_num)
            elapsed = time.time() - t0
            total_sent += stats["sent"]
            print_summary(batch_num, stats, elapsed, houses)
            log.info(f"Total messages sent: {total_sent:,}")
            batch_num += 1
            time.sleep(max(0, CONFIG["interval_seconds"] - elapsed))
    except KeyboardInterrupt:
        print(f"\n🛑 Stopped. Total: {batch_num-1} batches, {total_sent:,} messages")
        producer.close()


if __name__ == "__main__":
    run()
