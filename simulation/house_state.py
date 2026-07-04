"""
house_state.py  v3 — Realistic IoT Simulation
Smart City Gas & Air Safety Monitoring Platform

Normal: ~91% | Warning: ~8% | Critical: ~1%
Methane normal: 1-6 ppm | Anomaly peak: 150-350 ppm
"""

import random
import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict

from metadata_config import (
    GOVERNORATES, BUILDING_TYPES,
    HIGH_RISK_ZONES, MEDIUM_RISK_ZONES,
    NORMAL_RANGES, WALK_DELTA,
    ANOMALY_ESCALATION, ANOMALY_PEAKS, ANOMALY_DURATION,
    GOV_BOUNDS,ZONE_COORDS,
)


@dataclass
class HouseState:
    # Static metadata
    house_id:           str
    governorate:        str
    zone:               str
    latitude:           float
    longitude:          float
    building_type:      str
    year_built:         int
    risk_profile:       str
    has_gas_connection: bool

    # Live sensor state
    temperature_c:      float = 25.0
    humidity_pct:       float = 50.0
    methane_ppm:        float = 3.0
    lpg_ppm:            float = 5.0
    gas_pressure_kpa:   float = 1.4
    co_ppm:             float = 0.8
    smoke_level:        float = 2.0
    aqi:                float = 60.0
    co2_ppm:            float = 480.0
    pm25_ugm3:          float = 15.0
    pm10_ugm3:          float = 28.0

    # Anomaly state
    anomaly_active:       bool          = False
    anomaly_type:         Optional[str] = None
    anomaly_batches_left: int           = 0

    def update(self, hour: int, month: int, anomaly_rate: float) -> Dict:
        # Maybe start anomaly
        if not self.anomaly_active and self.has_gas_connection:
            prob = anomaly_rate
            if self.risk_profile == "high":
                prob *= 2.5
            elif self.risk_profile == "medium":
                prob *= 1.3
            else:
                prob *= 0.4

            if random.random() < prob:
                self.anomaly_active       = True
                self.anomaly_type         = random.choice(list(ANOMALY_ESCALATION.keys()))
                self.anomaly_batches_left = random.randint(
                    ANOMALY_DURATION["min"], ANOMALY_DURATION["max"]
                )

        if self.anomaly_active:
            self._apply_anomaly_step()
            self.anomaly_batches_left -= 1
            if self.anomaly_batches_left <= 0:
                self.anomaly_active = False
                self.anomaly_type   = None
        else:
            self._apply_random_walk(hour, month)

        return {
            "temperature_c":    round(self.temperature_c,    1),
            "humidity_pct":     round(self.humidity_pct,     1),
            "methane_ppm":      round(self.methane_ppm,      2),
            "lpg_ppm":          round(self.lpg_ppm,          2),
            "gas_pressure_kpa": round(self.gas_pressure_kpa, 2),
            "co_ppm":           round(self.co_ppm,           2),
            "smoke_level":      round(self.smoke_level,      1),
            "aqi":              int(round(self.aqi)),
            "co2_ppm":          int(round(self.co2_ppm)),
            "pm25_ugm3":        round(self.pm25_ugm3,        1),
            "pm10_ugm3":        round(self.pm10_ugm3,        1),
            "is_anomaly":       1 if self.anomaly_active else 0,
            "anomaly_type":     self.anomaly_type or "none",
        }

    def _apply_random_walk(self, hour: int, month: int):
        from metadata_config import HOURLY_ACTIVITY, MONTHLY_TEMP

        activity   = HOURLY_ACTIVITY[hour]
        is_cooking = hour in {7, 8, 12, 13, 19, 20}
        t_range    = MONTHLY_TEMP[month]
        t_center   = (t_range["min"] + t_range["max"]) / 2.0
        age_factor = min((2026 - self.year_built) / 80.0, 1.0)

        # Multipliers — kept small for realism
        gas_m  = 1.5 if self.building_type == "factory" else \
                 1.2 if self.building_type == "commercial" else 1.0
        risk_m = 1.05 if self.risk_profile == "high" else 1.0

        def walk(current, key, center, lo, hi):
            delta = random.uniform(-WALK_DELTA[key], WALK_DELTA[key])
            pull  = (center - current) * 0.10   # stronger pull to center
            return max(lo, min(hi, current + delta + pull))

        # Temperature
        self.temperature_c = walk(
            self.temperature_c, "temperature_c",
            t_center, t_range["min"] - 1, t_range["max"] + 4,
        )

        # Humidity
        hum_c = 60 - (self.temperature_c - 20) * 0.7
        self.humidity_pct = walk(self.humidity_pct, "humidity_pct", hum_c, 25, 85)

        # Gas sensors — REALISTIC baseline
        if self.has_gas_connection:
            # Normal: 1-6 ppm. Cooking adds tiny boost (max +2 ppm)
            meth_c = (2.0 + age_factor * 1.0 + (1.5 if is_cooking else 0) * activity) * gas_m * risk_m
            self.methane_ppm = walk(self.methane_ppm, "methane_ppm", meth_c, 0.5, 12.0)

            lpg_c = meth_c * 0.7
            self.lpg_ppm = walk(self.lpg_ppm, "lpg_ppm", lpg_c, 0.5, 15.0)

            p_c = max(0.9, 1.35 - age_factor * 0.15)
            self.gas_pressure_kpa = walk(self.gas_pressure_kpa, "gas_pressure_kpa", p_c, 0.6, 1.9)
        else:
            self.methane_ppm = 0.0
            self.lpg_ppm     = 0.0
            self.gas_pressure_kpa = 0.0

        # CO — urban background 0.1-2.5 ppm
        co_c = (0.4 + activity * 1.2 + age_factor * 0.3) * gas_m
        self.co_ppm = walk(self.co_ppm, "co_ppm", co_c, 0.05, 4.0)

        # CO2 — indoor 400-600 ppm
        co2_c = (420 + activity * 120 + (15 if is_cooking else 0)) * (1.3 if self.building_type == "factory" else 1.0)
        self.co2_ppm = walk(self.co2_ppm, "co2_ppm", co2_c, 390, 750)

        # Smoke — very low normally
        smoke_c = (0.5 + is_cooking * 3 * activity + (3 if self.building_type == "factory" else 0))
        self.smoke_level = walk(self.smoke_level, "smoke_level", smoke_c, 0, 10)

        # AQI — Cairo realistic 50-90
        traffic = 18 if hour in {8, 9, 17, 18, 19} else 2
        aqi_c = 58 + (self.temperature_c - 22) * 0.6 + traffic * activity
        self.aqi = walk(self.aqi, "aqi", aqi_c, 30, 100)

        # PM
        pm_c = 12 + activity * 10 + age_factor * 4
        self.pm25_ugm3 = walk(self.pm25_ugm3, "pm25_ugm3", pm_c, 2, 35)
        self.pm10_ugm3 = walk(self.pm10_ugm3, "pm10_ugm3", pm_c * 1.7, 5, 65)

    def _apply_anomaly_step(self):
        escalation = ANOMALY_ESCALATION[self.anomaly_type]
        for sensor, delta in escalation.items():
            current = getattr(self, sensor)
            peak    = ANOMALY_PEAKS.get(sensor, 9999)
            setattr(self, sensor, min(current + delta, peak))


def build_houses(num_houses: int = 3000, seed: int = 42) -> list:
    random.seed(seed)
    rng = np.random.default_rng(seed)

    dense = {"Cairo","Giza","Alexandria","Qalyubia","Sharqia","Dakahlia","Gharbia"}

    pool = []
    for gov, info in GOVERNORATES.items():
        w = 3 if gov in dense else 1
        for zone in info["zones"]:
            pool.extend([(gov, zone, info["center"])] * w)

    b_types   = list(BUILDING_TYPES.keys())
    b_weights = [BUILDING_TYPES[b]["weight"] for b in b_types]

    houses = []
    for i in range(1, num_houses + 1):
        gov, zone, (gov_lat, gov_lon) = random.choice(pool)
        b_type = random.choices(b_types, weights=b_weights)[0]

        if zone in ZONE_COORDS:
            base_lat, base_lon = ZONE_COORDS[zone]
        else:
            base_lat, base_lon = gov_lat, gov_lon

        narrow_zones = {"Zamalek", "Ras El Bar", "Port Fouad", "Agouza", "Dokki"}
        
        if zone in narrow_zones:
            offset = 0.0015
        else:
            offset = 0.005

        lat = base_lat + random.uniform(-offset, offset)
        lon = base_lon + random.uniform(-offset, offset)

        if gov in GOV_BOUNDS:
            bounds = GOV_BOUNDS[gov]
            lat = max(bounds["lat_min"], min(lat, bounds["lat_max"]))
            lon = max(bounds["lon_min"], min(lon, bounds["lon_max"]))

        lat = round(lat, 6)
        lon = round(lon, 6)

        if zone in HIGH_RISK_ZONES:
            year_built = int(rng.integers(1960, 2005))
        elif zone in MEDIUM_RISK_ZONES:
            year_built = int(rng.integers(1975, 2015))
        else:
            year_built = int(rng.integers(1990, 2024))

        # Gas connection probabilities
        if b_type == "factory":
            has_gas = rng.random() < 0.60
        elif gov in {"South Sinai","New Valley","Matruh","North Sinai"}:
            has_gas = rng.random() < 0.45
        else:
            has_gas = rng.random() < 0.82

        # Risk profile — mostly low
        if zone in HIGH_RISK_ZONES or year_built < 1980:
            risk = random.choices(["high","medium","low"], weights=[0.20, 0.45, 0.35])[0]
        elif zone in MEDIUM_RISK_ZONES or year_built < 2000:
            risk = random.choices(["high","medium","low"], weights=[0.08, 0.40, 0.52])[0]
        else:
            risk = random.choices(["high","medium","low"], weights=[0.02, 0.18, 0.80])[0]

        r = NORMAL_RANGES
        h = HouseState(
            house_id           = f"H{i:04d}",
            governorate        = gov,
            zone               = zone,
            latitude           = lat,
            longitude          = lon,
            building_type      = b_type,
            year_built         = year_built,
            risk_profile       = risk,
            has_gas_connection = bool(has_gas),
        )

        # Initialize with realistic starting values
        h.temperature_c    = random.uniform(r["temperature_c"]["min"],    r["temperature_c"]["max"])
        h.humidity_pct     = random.uniform(r["humidity_pct"]["min"],     r["humidity_pct"]["max"])
        h.methane_ppm      = random.uniform(r["methane_ppm"]["min"],      r["methane_ppm"]["max"])      if has_gas else 0.0
        h.lpg_ppm          = random.uniform(r["lpg_ppm"]["min"],          r["lpg_ppm"]["max"])          if has_gas else 0.0
        h.gas_pressure_kpa = random.uniform(r["gas_pressure_kpa"]["min"], r["gas_pressure_kpa"]["max"]) if has_gas else 0.0
        h.co_ppm           = random.uniform(r["co_ppm"]["min"],           r["co_ppm"]["max"])
        h.smoke_level      = random.uniform(r["smoke_level"]["min"],      r["smoke_level"]["max"])
        h.aqi              = random.uniform(r["aqi"]["min"],              r["aqi"]["max"])
        h.co2_ppm          = random.uniform(r["co2_ppm"]["min"],          r["co2_ppm"]["max"])
        h.pm25_ugm3        = random.uniform(r["pm25_ugm3"]["min"],        r["pm25_ugm3"]["max"])
        h.pm10_ugm3        = random.uniform(r["pm10_ugm3"]["min"],        r["pm10_ugm3"]["max"])

        houses.append(h)

    with_gas  = sum(1 for h in houses if h.has_gas_connection)
    high_risk = sum(1 for h in houses if h.risk_profile == "high")
    print(f"✅ {len(houses):,} houses built")
    print(f"   Governorates : {len(set(h.governorate for h in houses))}")
    print(f"   Zones        : {len(set(h.zone for h in houses))}")
    print(f"   With gas     : {with_gas:,} ({100*with_gas/len(houses):.0f}%)")
    print(f"   High risk    : {high_risk:,} ({100*high_risk/len(houses):.0f}%)")
    return houses
