"""
utils.py  v3 — Alert status and risk score calculations.
"""
from metadata_config import THRESHOLDS


def calculate_alert_status(
    methane: float, lpg: float, co2: float,
    smoke: float, aqi: float, co: float, temperature: float
) -> str:
    readings = {
        "methane": methane, "lpg": lpg, "co2": co2,
        "smoke": smoke, "aqi": aqi, "co": co, "temperature": temperature,
    }
    for sensor, value in readings.items():
        if value >= THRESHOLDS[sensor]["critical"]:
            return "CRITICAL"
    for sensor, value in readings.items():
        if value >= THRESHOLDS[sensor]["warning"]:
            return "WARNING"
    return "NORMAL"


def calculate_risk_score(
    methane: float, lpg: float, co2: float, smoke: float,
    aqi: float, co: float, temperature: float, risk_profile: str
) -> float:
    score = (
        min(methane     / THRESHOLDS["methane"]["critical"],     1.0) * 35 +
        min(lpg         / THRESHOLDS["lpg"]["critical"],         1.0) * 20 +
        min(smoke       / THRESHOLDS["smoke"]["critical"],       1.0) * 20 +
        min(co          / THRESHOLDS["co"]["critical"],          1.0) * 10 +
        min(aqi         / THRESHOLDS["aqi"]["critical"],         1.0) * 10 +
        min(co2         / THRESHOLDS["co2"]["critical"],         1.0) * 3  +
        min(temperature / THRESHOLDS["temperature"]["critical"], 1.0) * 2
    )
    multiplier = {"low": 0.85, "medium": 1.0, "high": 1.15}
    return round(min(score * multiplier.get(risk_profile, 1.0), 100.0), 2)
