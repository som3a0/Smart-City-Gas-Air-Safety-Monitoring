"""
Smart City Gas & Air Safety Monitoring Platform
FastAPI Backend  v3.3
Gemini (2.5-flash-lite / flash-latest / 2.5-flash) — key via env var

Changes v3.3:
- /api/risk-by-gov: returns ALL 27 governorates (not TOP 10) ordered by avg_risk_score DESC
  so React & ChatBot match Grafana exactly.
- /api/methane-trend: last 3 minutes only — matches Grafana time window.
- /api/map-data: ROW_NUMBER deduplication per house_id (CRITICAL wins over WARNING).
- /api/active-alerts: ROW_NUMBER deduplication per house_id (CRITICAL wins over WARNING).
- build_live_context: highest_gov now taken from gov_stats, not from alerts table,
  so ChatBot "Highest cluster" matches what React & Grafana show.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pydantic import BaseModel
import urllib.parse
import os
import httpx

app = FastAPI(title="Smart City API", version="3.3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Database ─────────────────────────────────────────────────────────────────
DB_USER = os.environ.get("SQLSERVER_USER", "sa")
DB_PASS = os.environ.get("SQLSERVER_PASSWORD", "SmartCity@2026")
DB_HOST = os.environ.get("SQLSERVER_HOST", "sqlserver")
DB_PORT = os.environ.get("SQLSERVER_PORT", "1433")
DB_NAME = os.environ.get("SQLSERVER_DB", "SmartCityDB")

encoded_pass = urllib.parse.quote_plus(DB_PASS)
DB_URI = (
    f"mssql+pyodbc://{DB_USER}:{encoded_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=no&TrustServerCertificate=yes"
)
engine = create_engine(DB_URI)

# ─── Gemini Config ────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

GEMINI_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-2.5-flash",
]
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"


# ─── Helpers ──────────────────────────────────────────────────────────────────
def get_latest_batch(conn, table="gold.active_alerts"):
    """Returns MAX(batch_id) for the given table. Returns 0 if table is empty."""
    res = conn.execute(text(f"SELECT MAX(batch_id) FROM {table}")).fetchone()
    return res[0] if (res and res[0]) else 0


def detect_root_cause(temp, smoke, methane):
    m = float(methane or 0)
    t = float(temp    or 0)
    s = float(smoke   or 0)
    if m >= 50:  return "GAS_LEAK"
    if t >= 42:  return "HIGH_TEMP"
    if s >= 20:  return "SMOKE_SPIKE"
    return "ELEVATED_RISK"

def build_live_context(requested_batch: int = None) -> str:
    """Pull real-time snapshot from SQL Server for injection into AI prompt.
    
    KEY: highest_gov is taken from gold.gov_stats (same source as Grafana & React),
    NOT from active_alerts — ensures ChatBot 'Highest cluster' matches the dashboard.
    """
    try:
        with engine.connect() as conn:
            if requested_batch:
                lb_alerts = requested_batch
                lb_gov = requested_batch
            else:
                lb_alerts = get_latest_batch(conn, "gold.active_alerts")
                lb_gov    = get_latest_batch(conn, "gold.gov_stats")

            kpi_row = conn.execute(text(f"""
                WITH ranked AS (
                    SELECT alert_status,
                           ROW_NUMBER() OVER (
                               PARTITION BY house_id
                               ORDER BY CASE alert_status WHEN 'CRITICAL' THEN 0 ELSE 1 END, risk_score DESC
                           ) AS rn
                    FROM gold.active_alerts
                    WHERE alert_status != 'NORMAL' AND batch_id={lb_alerts}
                )
                SELECT 
                    SUM(CASE WHEN alert_status = 'CRITICAL' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN alert_status = 'WARNING' THEN 1 ELSE 0 END)
                FROM ranked
                WHERE rn = 1
            """)).fetchone()

            crit = kpi_row[0] if kpi_row and kpi_row[0] else 0
            warn = kpi_row[1] if kpi_row and kpi_row[1] else 0

            avg_risk = conn.execute(text(
                f"SELECT CAST(AVG(avg_risk_score) AS FLOAT) FROM gold.gov_stats "
                f"WHERE batch_id={lb_gov}"
            )).scalar() or 0.0

            # Top 5 critical — deduplicated per house_id
            crit_rows = conn.execute(text(f"""
                WITH ranked AS (
                    SELECT
                        house_id, governorate, zone, alert_status,
                        CAST(risk_score    AS FLOAT) AS risk_score,
                        CAST(methane_ppm   AS FLOAT) AS methane_ppm,
                        CAST(temperature_c AS FLOAT) AS temperature_c,
                        CAST(smoke_level   AS FLOAT) AS smoke_level,
                        CAST(co_ppm        AS FLOAT) AS co_ppm,
                        ROW_NUMBER() OVER (
                            PARTITION BY house_id
                            ORDER BY CASE alert_status WHEN 'CRITICAL' THEN 0 ELSE 1 END, risk_score DESC
                        ) AS rn
                    FROM gold.active_alerts
                    WHERE alert_status='CRITICAL' AND batch_id={lb_alerts}
                )
                SELECT TOP 5
                    house_id, governorate, zone, alert_status,
                    risk_score, methane_ppm, temperature_c, smoke_level, co_ppm
                FROM ranked
                WHERE rn = 1
                ORDER BY risk_score DESC
            """)).fetchall()

            # Top 5 warning — deduplicated per house_id
            warn_rows = conn.execute(text(f"""
                WITH ranked AS (
                    SELECT
                        house_id, governorate, zone, alert_status,
                        CAST(risk_score    AS FLOAT) AS risk_score,
                        CAST(methane_ppm   AS FLOAT) AS methane_ppm,
                        CAST(temperature_c AS FLOAT) AS temperature_c,
                        CAST(smoke_level   AS FLOAT) AS smoke_level,
                        CAST(co_ppm        AS FLOAT) AS co_ppm,
                        ROW_NUMBER() OVER (
                            PARTITION BY house_id
                            ORDER BY risk_score DESC
                        ) AS rn
                    FROM gold.active_alerts
                    WHERE alert_status='WARNING' AND batch_id={lb_alerts}
                )
                SELECT TOP 5
                    house_id, governorate, zone, alert_status,
                    risk_score, methane_ppm, temperature_c, smoke_level, co_ppm
                FROM ranked
                WHERE rn = 1
                ORDER BY risk_score DESC
            """)).fetchall()

            # ALL govs ordered by avg_risk_score DESC — (Deduplicated for Chatbot)
            gov_rows = conn.execute(text(f"""
                WITH dedup_alerts AS (
                    SELECT governorate, alert_status,
                           ROW_NUMBER() OVER (
                               PARTITION BY house_id
                               ORDER BY CASE alert_status WHEN 'CRITICAL' THEN 0 ELSE 1 END, risk_score DESC
                           ) AS rn
                    FROM gold.active_alerts
                    WHERE alert_status != 'NORMAL' AND batch_id={lb_alerts}
                ),
                agg_alerts AS (
                    SELECT governorate,
                           SUM(CASE WHEN alert_status = 'CRITICAL' THEN 1 ELSE 0 END) AS critical_count,
                           SUM(CASE WHEN alert_status = 'WARNING' THEN 1 ELSE 0 END) AS warning_count
                    FROM dedup_alerts
                    WHERE rn = 1
                    GROUP BY governorate
                ),
                gov_risk AS (
                    SELECT governorate,
                           CAST(AVG(avg_risk_score) AS FLOAT) AS avg_risk,
                           MAX(gov_risk_level) AS gov_risk_level
                    FROM gold.gov_stats
                    WHERE batch_id={lb_gov}
                    GROUP BY governorate
                )
                SELECT 
                    g.governorate,
                    g.avg_risk,
                    COALESCE(a.critical_count, 0) AS critical_count,
                    COALESCE(a.warning_count, 0) AS warning_count,
                    g.gov_risk_level
                FROM gov_risk g
                LEFT JOIN agg_alerts a ON g.governorate = a.governorate
                ORDER BY g.avg_risk DESC
            """)).fetchall()

            # Methane trend — last 1 minute
            trend_rows = conn.execute(text("""
                SELECT TOP 5
                    snapshot_time,
                    CAST(AVG(avg_methane_ppm) AS FLOAT) AS avg_methane_ppm
                FROM gold.zone_stats
                WHERE snapshot_time >= DATEADD(MINUTE, -1, GETDATE())
                GROUP BY snapshot_time
                ORDER BY snapshot_time DESC
            """)).fetchall()


            # Top 5 warning — deduplicated per house_id
            warn_rows = conn.execute(text(f"""
                WITH ranked AS (
                    SELECT
                        house_id, governorate, zone, alert_status,
                        CAST(risk_score    AS FLOAT) AS risk_score,
                        CAST(methane_ppm   AS FLOAT) AS methane_ppm,
                        CAST(temperature_c AS FLOAT) AS temperature_c,
                        CAST(smoke_level   AS FLOAT) AS smoke_level,
                        CAST(co_ppm        AS FLOAT) AS co_ppm,
                        ROW_NUMBER() OVER (
                            PARTITION BY house_id
                            ORDER BY risk_score DESC
                        ) AS rn
                    FROM gold.active_alerts
                    WHERE alert_status='WARNING' AND batch_id={lb_alerts}
                )
                SELECT TOP 5
                    house_id, governorate, zone, alert_status,
                    risk_score, methane_ppm, temperature_c, smoke_level, co_ppm
                FROM ranked
                WHERE rn = 1
                ORDER BY risk_score DESC
            """)).fetchall()

            # ALL govs ordered by avg_risk_score DESC — same as Grafana & React
            gov_rows = conn.execute(text(f"""
                SELECT
                    governorate,
                    CAST(AVG(avg_risk_score) AS FLOAT) AS avg_risk,
                    SUM(critical_count)                AS critical_count,
                    SUM(warning_count)                 AS warning_count,
                    MAX(gov_risk_level)                AS gov_risk_level
                FROM gold.gov_stats
                WHERE batch_id={lb_gov}
                GROUP BY governorate
                ORDER BY AVG(avg_risk_score) DESC
            """)).fetchall()

            # Methane trend — last 1 minute, matches Grafana time window
            trend_rows = conn.execute(text("""
                SELECT TOP 5
                    snapshot_time,
                    CAST(AVG(avg_methane_ppm) AS FLOAT) AS avg_methane_ppm
                FROM gold.zone_stats
                WHERE snapshot_time >= DATEADD(MINUTE, -1, GETDATE())
                GROUP BY snapshot_time
                ORDER BY snapshot_time DESC
            """)).fetchall()

        lines = [
            "=== LIVE SYSTEM SNAPSHOT ===",
            f"Total monitored houses : 3000",
            f"Critical threats       : {crit}",
            f"Warning signals        : {warn}",
            f"Average risk score     : {round(avg_risk, 1)} / 100",
            f"Normal houses          : {3000 - crit - warn}",
            "",
        ]

        if crit_rows:
            lines.append("--- TOP CRITICAL INCIDENTS ---")
            for r in crit_rows:
                house, gov, zone, status = r[0], r[1], r[2], r[3]
                risk, meth, temp, smoke, co = r[4], r[5], r[6], r[7], r[8]
                cause = detect_root_cause(temp, smoke, meth)
                lines.append(
                    f"  [{status}] {house} | {gov}/{zone} | "
                    f"Risk={round(risk,1)} | CH4={round(meth,1)}ppm | "
                    f"Temp={round(temp,1)}C | Smoke={round(smoke,1)} | "
                    f"CO={round(co,1)}ppm | Cause={cause}"
                )
            lines.append("")

        if warn_rows:
            lines.append("--- TOP WARNING INCIDENTS ---")
            for r in warn_rows:
                house, gov, zone, status = r[0], r[1], r[2], r[3]
                risk, meth, temp, smoke, co = r[4], r[5], r[6], r[7], r[8]
                cause = detect_root_cause(temp, smoke, meth)
                lines.append(
                    f"  [{status}] {house} | {gov}/{zone} | "
                    f"Risk={round(risk,1)} | CH4={round(meth,1)}ppm | "
                    f"Temp={round(temp,1)}C | Smoke={round(smoke,1)} | "
                    f"CO={round(co,1)}ppm | Cause={cause}"
                )
            lines.append("")

        if gov_rows:
            lines.append("--- GOVERNORATE RISK RANKING (all, ordered by avg_risk_score DESC) ---")
            for r in gov_rows:
                gov, avg_r, crit_c, warn_c, level = r
                lines.append(
                    f"  {gov}: avg_risk={round(avg_r or 0,1)} | "
                    f"critical={crit_c or 0} | warning={warn_c or 0} | "
                    f"level={level or 'LOW'}"
                )
            lines.append("")

        if trend_rows:
            vals = [round(r[1] or 0, 2) for r in trend_rows]
            trend_dir = "RISING" if vals[0] > vals[-1] else "FALLING" if vals[0] < vals[-1] else "STABLE"
            lines.append(f"--- METHANE TREND (last 3 min, newest first) ---")
            lines.append(f"  Values: {vals}  |  Direction: {trend_dir}")

        return "\n".join(lines)

    except Exception as e:
        return f"[DB context unavailable: {str(e)}]"


SYSTEM_PROMPT = """You are ARIA (Automated Risk Intelligence Assistant), the friendly AI Operations Copilot for the Smart City Gas & Air Safety Monitoring Platform in Egypt.

You assist control room operators, supervisors, and executives with real-time safety insights about 3,000 monitored buildings across Egypt's 27 governorates.

CAPABILITIES:
1. Explain current system status and KPIs
2. Identify the most dangerous areas/houses
3. Explain WHY an incident is happening (root cause analysis)
4. Give operational safety recommendations
5. Summarize sensor trends (methane, temperature, smoke, CO, AQI)
6. Compare governorate risk levels
7. Generate executive summaries on demand
8. Respond naturally to greetings and casual conversation (e.g. "السلام عليكم", "hi", "thanks") — be warm and human, then gently offer to help with system data

SENSOR THRESHOLDS:
- Methane (CH4): Normal <8ppm | Warning ≥50ppm | Critical ≥150ppm
- Temperature:   Normal <35C  | Warning ≥42C   | Critical ≥55C
- Smoke Level:   Normal <10   | Warning ≥20    | Critical ≥45
- CO:            Normal <3ppm | Warning ≥9ppm  | Critical ≥35ppm
- AQI:           Normal <90   | Warning ≥100   | Critical ≥150

DATA SOURCE NOTE:
- Governorate rankings shown in the dashboard come from gold.gov_stats (avg_risk_score per governorate per batch).
- "Highest cluster" in the insight banner refers to the governorate with the highest avg_risk_score from gold.gov_stats — same source as the bar chart.
- When asked about which governorate has highest risk, always use the GOVERNORATE RISK RANKING from the live snapshot below.

RESPONSE RULES:
- If the user greets you or makes small talk, respond warmly and naturally first — do NOT immediately dump data on them
- For data questions, be concise and action-oriented (2-5 sentences max unless asked for a full report)
- Always use the live snapshot data below to give SPECIFIC answers (mention actual governorates/houses by name when relevant)
- Respond in the SAME language the user writes in (Arabic or English) — match their tone too
- For urgent situations prefix response with: 🔴 URGENT:
- For warnings prefix with: 🟡 ATTENTION:
- For stable status prefix with: 🟢 STABLE:
- Never hallucinate data not present in the snapshot
- Stay focused on smart city safety topics, but you can be conversational and personable"""


# ─── Pydantic Models ──────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    history: list = []
    batch_id: int = None

class ChatResponse(BaseModel):
    response: str
    data_context: str = ""


# ─── /api/chat ────────────────────────────────────────────────────────────────
import logging
import asyncio

log = logging.getLogger("ARIA")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    live_ctx = build_live_context(req.batch_id)
    log.info(f"[ARIA] Question: {req.message[:60]!r} | Locked to Batch: {req.batch_id}")

    if not GEMINI_API_KEY:
        log.warning("[ARIA] GEMINI_API_KEY is not set — skipping AI, using static fallback")
        return ChatResponse(
            response=_build_static_fallback(req.message, live_ctx),
            data_context="fallback"
        )

    full_system = f"{SYSTEM_PROMPT}\n\n{live_ctx}"

    contents = []
    for turn in req.history[-6:]:
        role = "user" if turn.get("role") == "user" else "model"
        text_val = turn.get("text", "")
        if text_val:
            contents.append({"role": role, "parts": [{"text": text_val}]})
    contents.append({"role": "user", "parts": [{"text": req.message}]})

    payload = {
        "system_instruction": {"parts": [{"text": full_system}]},
        "contents": contents,
        "generationConfig": {
            "temperature":     0.6,
            "maxOutputTokens": 500,
            "topP":            0.9,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT",        "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH",       "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ],
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=10.0)) as client:
        for model in GEMINI_MODELS:
            log.info(f"[ARIA] Trying model: {model}")
            url = f"{GEMINI_BASE}{model}:generateContent?key={GEMINI_API_KEY}"
            try:
                resp = await client.post(
                    url, json=payload,
                    headers={"Content-Type": "application/json"}
                )
                log.info(f"[ARIA] {model} → HTTP {resp.status_code}")

                if resp.status_code == 429:
                    await asyncio.sleep(1)
                    continue

                if not resp.is_success:
                    log.warning(f"[ARIA] {model} error body: {resp.text[:300]}")
                    continue

                data = resp.json()
                candidates = data.get("candidates", [])

                if not candidates:
                    log.warning(f"[ARIA] {model} no candidates.")
                    continue

                parts  = candidates[0].get("content", {}).get("parts", [])
                answer = "".join(p.get("text", "") for p in parts).strip()

                if answer:
                    log.info(f"[ARIA] Success via {model}: {answer[:60]!r}")
                    return ChatResponse(response=answer, data_context="ok")

                log.warning(f"[ARIA] {model} returned empty content")

            except httpx.TimeoutException:
                log.warning(f"[ARIA] {model} timed out")
            except Exception as e:
                log.warning(f"[ARIA] {model} exception: {e}")

    log.warning("[ARIA] All Gemini models failed — using static fallback")
    return ChatResponse(
        response=_build_static_fallback(req.message, live_ctx),
        data_context="fallback"
    )


def _build_static_fallback(question: str, live_ctx: str) -> str:
    q = question.lower().strip()
    lines = live_ctx.split("\n")

    greetings_ar = ["سلام", "اهلا", "أهلا", "مرحبا", "هاي", "هلا"]
    greetings_en = ["hi", "hello", "hey", "good morning", "good evening"]
    if any(g in q for g in greetings_ar) or any(q == g or q.startswith(g) for g in greetings_en):
        return (
            "وعليكم السلام! 👋 أنا ARIA، جاهزة لمساعدتك في مراقبة النظام.\n\n"
            "_(ملاحظة: خدمة الذكاء الاصطناعي الكاملة غير متاحة حالياً، لكن يمكنني عرض بيانات حية من قاعدة البيانات)_"
        )

    def extract(prefix):
        for line in lines:
            if prefix in line:
                parts = line.split(":")
                return parts[-1].strip() if len(parts) > 1 else ""
        return "N/A"

    crit  = extract("Critical threats")
    warn  = extract("Warning signals")
    risk  = extract("Average risk score")
    total = extract("Total monitored houses")

    # Top governorate from gov_stats ranking (same source as dashboard)
    top_gov = "N/A"
    top_gov_risk = "N/A"
    in_gov  = False
    for line in lines:
        if "GOVERNORATE RISK RANKING" in line:
            in_gov = True
            continue
        if in_gov and line.strip().startswith("  ") and "avg_risk=" in line:
            parts = line.strip().split(":")
            top_gov = parts[0].strip()
            # extract avg_risk value
            for seg in line.split("|"):
                if "avg_risk=" in seg:
                    top_gov_risk = seg.split("=")[1].strip()
                    break
            break

    top_crit = "N/A"
    for line in lines:
        if "[CRITICAL]" in line:
            top_crit = line.strip()
            break

    if any(w in q for w in ["status", "summary", "حالة", "ملخص", "overview"]):
        return (
            f"📊 **Live System Status**\n\n"
            f"• Total Monitored: {total} houses\n"
            f"• 🔴 Critical: {crit} houses\n"
            f"• 🟡 Warning:  {warn} houses\n"
            f"• Avg Risk Score: {risk}\n"
            f"• Highest Risk Governorate: {top_gov} (avg risk {top_gov_risk})\n\n"
            f"_AI analysis temporarily unavailable — showing live DB data directly._"
        )
    elif any(w in q for w in ["critical", "حرج", "danger", "خطر", "urgent"]):
        return (
            f"🔴 **Critical Incidents ({crit} total)**\n\n"
            f"Top incident:\n`{top_crit}`\n\n"
            f"Check the Active Incident Feed on the right panel for full list.\n\n"
            f"_AI analysis temporarily unavailable._"
        )
    elif any(w in q for w in ["gov", "محافظ", "region", "area", "highest", "cluster"]):
        gov_lines = []
        in_section = False
        for l in lines:
            if "GOVERNORATE RISK RANKING" in l:
                in_section = True
                continue
            if in_section and l.strip().startswith("  ") and "|" in l:
                gov_lines.append(l.strip())
            if in_section and not l.strip() and gov_lines:
                break
        result = "\n".join(gov_lines[:5]) or "No data available."
        return f"🗺️ **Top Risk Governorates (same as dashboard):**\n\n{result}\n\n_AI temporarily unavailable._"
    elif any(w in q for w in ["methane", "ch4", "gas", "ميثان", "غاز"]):
        trend_line = extract("Values")
        trend_dir  = extract("Direction")
        return (
            f"☣️ **Methane Status**\n\n"
            f"• Trend: {trend_dir}\n"
            f"• Recent readings (last 3 min): {trend_line}\n"
            f"• Warning threshold: 50 ppm | Critical: 150 ppm\n\n"
            f"_AI temporarily unavailable — showing raw sensor data._"
        )
    else:
        return (
            f"📡 **Live Data Summary** _(AI temporarily unavailable)_\n\n"
            f"Critical: **{crit}** | Warning: **{warn}** | Avg Risk: **{risk}**\n"
            f"Highest Risk: **{top_gov}** (avg risk {top_gov_risk})\n\n"
            f"Please retry your question in a moment for full AI analysis."
        )


# ─── /api/kpis ────────────────────────────────────────────────────────────────
@app.get("/api/kpis")
def get_kpis():
    with engine.connect() as conn:
        lb = get_latest_batch(conn)
        lb_gov = get_latest_batch(conn, "gold.gov_stats")
        
        kpi_row = conn.execute(text(f"""
            WITH ranked AS (
                SELECT alert_status,
                       ROW_NUMBER() OVER (
                           PARTITION BY house_id
                           ORDER BY CASE alert_status WHEN 'CRITICAL' THEN 0 ELSE 1 END, risk_score DESC
                       ) AS rn
                FROM gold.active_alerts
                WHERE alert_status != 'NORMAL' AND batch_id = {lb}
            )
            SELECT 
                SUM(CASE WHEN alert_status = 'CRITICAL' THEN 1 ELSE 0 END),
                SUM(CASE WHEN alert_status = 'WARNING' THEN 1 ELSE 0 END)
            FROM ranked
            WHERE rn = 1
        """)).fetchone()
        
        crit = kpi_row[0] if kpi_row and kpi_row[0] else 0
        warn = kpi_row[1] if kpi_row and kpi_row[1] else 0
        
        risk = conn.execute(text(
            f"SELECT CAST(AVG(avg_risk_score) AS FLOAT) FROM gold.gov_stats "
            f"WHERE batch_id = {lb_gov}"
        )).scalar()
        
    return {
        "batch_id":     lb,
        "CRITICAL":     crit,
        "WARNING":      warn,
        "avg_risk":     round(risk or 0, 1),
        "TOTAL_HOUSES": 3000,
    }


# ─── /api/map-data ────────────────────────────────────────────────────────────
# Uses ROW_NUMBER to deduplicate: if a house_id appears as both CRITICAL and WARNING
# (due to multiple batch rows), only the CRITICAL row is kept.
@app.get("/api/map-data")
def get_map_data():
    with engine.connect() as conn:
        lb = get_latest_batch(conn)
        rows = conn.execute(text(f"""
            WITH ranked AS (
                SELECT
                    latitude, longitude, risk_score, alert_status,
                    governorate, zone, house_id,
                    methane_ppm, temperature_c, smoke_level, co_ppm,
                    ROW_NUMBER() OVER (
                        PARTITION BY house_id
                        ORDER BY CASE alert_status WHEN 'CRITICAL' THEN 0 ELSE 1 END, risk_score DESC
                    ) AS rn
                FROM gold.active_alerts
                WHERE alert_status != 'NORMAL'
                  AND latitude IS NOT NULL
                  AND batch_id = {lb}
            )
            SELECT latitude, longitude, risk_score, alert_status,
                   governorate, zone, house_id,
                   methane_ppm, temperature_c, smoke_level, co_ppm
            FROM ranked
            WHERE rn = 1
        """)).fetchall()

    data = []
    for r in rows:
        lat, lon, risk, status, gov, zone, house_id = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
        methane, temp, smoke, co = r[7], r[8], r[9], r[10]
        trigger = detect_root_cause(temp, smoke, methane)
        data.append({
            "coordinates":     [lon, lat],
            "risk_score":      round(risk    or 0, 1),
            "alert_status":    status,
            "governorate":     gov,
            "zone":            zone,
            "house_id":        house_id,
            "primary_trigger": trigger,
            "sensors": {
                "methane": round(methane or 0, 1),
                "temp":    round(temp    or 0, 1),
                "smoke":   round(smoke   or 0, 1),
                "co":      round(co      or 0, 1),
            },
        })
    return data


# ─── /api/active-alerts ───────────────────────────────────────────────────────
# ROW_NUMBER deduplication: CRITICAL beats WARNING for same house_id.
@app.get("/api/active-alerts")
def get_active_alerts():
    with engine.connect() as conn:
        lb = get_latest_batch(conn)
        rows = conn.execute(text(f"""
            WITH ranked AS (
                SELECT
                    house_id, governorate, zone, alert_status,
                    CAST(risk_score    AS FLOAT) AS risk_score,
                    CAST(methane_ppm   AS FLOAT) AS methane_ppm,
                    CAST(temperature_c AS FLOAT) AS temperature_c,
                    CAST(smoke_level   AS FLOAT) AS smoke_level,
                    CAST(co_ppm        AS FLOAT) AS co_ppm,
                    latitude,
                    longitude,
                    ROW_NUMBER() OVER (
                        PARTITION BY house_id
                        ORDER BY CASE alert_status WHEN 'CRITICAL' THEN 0 ELSE 1 END, risk_score DESC
                    ) AS rn
                FROM gold.active_alerts
                WHERE alert_status != 'NORMAL' AND batch_id = {lb}
            )
            SELECT
                house_id, governorate, zone, alert_status,
                risk_score, methane_ppm, temperature_c, smoke_level, co_ppm,
                latitude, longitude
            FROM ranked
            WHERE rn = 1
            ORDER BY
                CASE alert_status WHEN 'CRITICAL' THEN 0 ELSE 1 END,
                risk_score DESC
        """)).fetchall()

    data = []
    for r in rows:
        house_id, gov, zone, status = r[0], r[1], r[2], r[3]
        risk, methane, temp, smoke, co = r[4], r[5], r[6], r[7], r[8]
        lat, lon = r[9], r[10]
        trigger = detect_root_cause(temp, smoke, methane)
        data.append({
            "house_id":        house_id,
            "governorate":     gov,
            "zone":            zone,
            "alert_status":    status,
            "risk_score":      round(risk    or 0, 1),
            "primary_trigger": trigger,
            "latitude":        lat,
            "longitude":       lon,
            "sensors": {
                "methane": round(methane or 0, 1),
                "temp":    round(temp    or 0, 1),
                "smoke":   round(smoke   or 0, 1),
                "co":      round(co      or 0, 1),
            },
        })
    return data


# ─── /api/risk-by-gov ─────────────────────────────────────────────────────────
# Returns ALL governorates ordered by avg_risk_score DESC.
# Matches Grafana "Risk by Governorate" chart exactly.
# React shows same data as Grafana; ChatBot uses same ranking.
@app.get("/api/risk-by-gov")
def get_risk_by_gov():
    with engine.connect() as conn:
        lb = get_latest_batch(conn, "gold.gov_stats")
        rows = conn.execute(text(f"""
            SELECT
                governorate,
                CAST(AVG(avg_risk_score)  AS FLOAT) AS avg_risk_score,
                CAST(MAX(max_risk_score)  AS FLOAT) AS max_risk_score,
                SUM(critical_count)                 AS critical_count,
                SUM(warning_count)                  AS warning_count,
                MAX(gov_risk_level)                 AS gov_risk_level
            FROM gold.gov_stats
            WHERE batch_id = {lb}
            GROUP BY governorate
            ORDER BY AVG(avg_risk_score) DESC
        """)).fetchall()

    return [
        {
            "name":          r[0],
            "avgRisk":       round(r[1] or 0, 1),
            "maxRisk":       round(r[2] or 0, 1),
            "criticalCount": int(r[3] or 0),
            "warningCount":  int(r[4] or 0),
            "riskLevel":     r[5] or "LOW",
        }
        for r in rows
    ]


# ─── /api/methane-trend ───────────────────────────────────────────────────────
# Last 3 minute only — matches Grafana time window (now-3m to now).
@app.get("/api/methane-trend")
def get_methane_trend():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT TOP 50
                snapshot_time,
                CAST(AVG(avg_methane_ppm) AS FLOAT) AS avg_methane_ppm
            FROM gold.zone_stats
            WHERE snapshot_time >= DATEADD(MINUTE, -5, GETDATE())
            GROUP BY snapshot_time
            ORDER BY snapshot_time DESC
        """)).fetchall()
    return [
        {"time": row[0].strftime("%H:%M:%S") if row[0] else "", "value": round(row[1] or 0, 2)}
        for row in reversed(rows)
    ]


# ─── /health ──────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "version": "3.3", "ai": "gemini", "ai_configured": bool(GEMINI_API_KEY)}
