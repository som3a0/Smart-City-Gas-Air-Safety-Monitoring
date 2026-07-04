-- ═══════════════════════════════════════════════════════════
--  Smart City Gas & Air Safety Monitoring Platform
--  SQL Server — Gold Layer Tables
--  (Bronze & Silver are Parquet files, only Gold goes to SQL)
-- ═══════════════════════════════════════════════════════════

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'SmartCityDB')
    CREATE DATABASE SmartCityDB;
GO

USE SmartCityDB;
GO

-- Create gold schema
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'gold')
    EXEC('CREATE SCHEMA gold');
GO

-- ─────────────────────────────────────────────────────────────
-- Zone-level aggregations (updated every 30s by Spark)
-- ─────────────────────────────────────────────────────────────
IF OBJECT_ID('gold.zone_stats', 'U') IS NULL
CREATE TABLE gold.zone_stats (
    id                  BIGINT IDENTITY(1,1) PRIMARY KEY,
    snapshot_time       DATETIME2 DEFAULT GETDATE(),
    batch_id            INT,
    governorate         NVARCHAR(100),
    zone                NVARCHAR(100),
    avg_methane_ppm     FLOAT,
    max_methane_ppm     FLOAT,
    avg_temperature_c   FLOAT,
    avg_smoke_level     FLOAT,
    avg_co_ppm          FLOAT,
    avg_aqi             FLOAT,
    max_aqi             INT,
    avg_risk_score      FLOAT,
    max_risk_score      FLOAT,
    total_readings      INT,
    critical_count      INT,
    warning_count       INT,
    anomaly_count       INT,
    zone_risk_level     VARCHAR(10)
);
GO

CREATE INDEX IX_zone_snapshot  ON gold.zone_stats (snapshot_time DESC);
CREATE INDEX IX_zone_gov_zone  ON gold.zone_stats (governorate, zone);
CREATE INDEX IX_zone_risk      ON gold.zone_stats (zone_risk_level);
GO

-- ─────────────────────────────────────────────────────────────
-- Governorate-level aggregations
-- ─────────────────────────────────────────────────────────────
IF OBJECT_ID('gold.gov_stats', 'U') IS NULL
CREATE TABLE gold.gov_stats (
    id                  BIGINT IDENTITY(1,1) PRIMARY KEY,
    snapshot_time       DATETIME2 DEFAULT GETDATE(),
    batch_id            INT,
    governorate         NVARCHAR(100),
    avg_risk_score      FLOAT,
    max_risk_score      FLOAT,
    avg_methane_ppm     FLOAT,
    avg_aqi             FLOAT,
    avg_temperature_c   FLOAT,
    total_houses        INT,
    critical_count      INT,
    warning_count       INT,
    total_anomalies     INT,
    gov_risk_level      VARCHAR(10)
);
GO

CREATE INDEX IX_gov_snapshot ON gold.gov_stats (snapshot_time DESC);
CREATE INDEX IX_gov_name     ON gold.gov_stats (governorate);
GO

-- ─────────────────────────────────────────────────────────────
-- Active alerts (WARNING + CRITICAL only)
-- ─────────────────────────────────────────────────────────────
IF OBJECT_ID('gold.active_alerts', 'U') IS NULL
CREATE TABLE gold.active_alerts (
    id              BIGINT IDENTITY(1,1) PRIMARY KEY,
    batch_id        INT,
    event_id        VARCHAR(50),
    house_id        VARCHAR(10),
    governorate     NVARCHAR(100),
    zone            NVARCHAR(100),
    latitude        FLOAT,
    longitude       FLOAT,
    building_type   VARCHAR(20),
    alert_status    VARCHAR(10),
    risk_score      FLOAT,
    methane_ppm     FLOAT,
    smoke_level     FLOAT,
    co_ppm          FLOAT,
    temperature_c   FLOAT,
    aqi             INT,
    is_anomaly      INT,
    alert_time      DATETIME2
);
GO

CREATE INDEX IX_alerts_time    ON gold.active_alerts (alert_time DESC);
CREATE INDEX IX_alerts_status  ON gold.active_alerts (alert_status);
CREATE INDEX IX_alerts_gov     ON gold.active_alerts (governorate, zone);
GO

PRINT '✅ SmartCityDB Gold tables created successfully';
PRINT '   gold.zone_stats';
PRINT '   gold.gov_stats';
PRINT '   gold.active_alerts';
GO
