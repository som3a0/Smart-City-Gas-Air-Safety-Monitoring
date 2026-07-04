@echo off
title Docker Services Manager

echo ========================================================
echo 1. Stopping and removing old containers and volumes...
echo ========================================================
docker compose down -v

echo.
echo ========================================================
echo 2. Installing Python Requirements...
echo ========================================================
pip install -r requirements.txt
py -m pip install pandas numpy kafka-python
docker compose build --no-cache iot-producer


echo.
echo ========================================================
echo 2. Starting containers in detached mode...
echo ========================================================
docker compose up -d

echo.
echo ========================================================
echo Waiting 40  seconds for SQL Server to fully start...
echo ========================================================
timeout /t 40 /nobreak

echo.
echo ========================================================
echo 3. Copying and Executing init.sql in SQL Server...
echo ========================================================
docker cp ../database/init.sql sqlserver:/tmp/init.sql
docker exec sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "SmartCity@2026" -No -i /tmp/init.sql

echo.
echo ========================================================
echo open SSMS
echo select authentication : sql server authentication 
echo server name : localhost,1433
echo user name : sa
echo password : SmartCity@2026
echo ========================================================
echo grafana 
echo username : admin
echo password : SmartCity@2026
echo ========================================================

:menu
echo.
echo ========================================================
echo Services URLs
echo ========================================================
echo Kafka   : http://localhost:8080
echo Spark   : http://localhost:4040
echo Grafana : http://localhost:3000
echo ========================================================

echo.
echo ========================================================
echo Options Menu
echo ========================================================
echo 1: Show kafka logs
echo 2: Show spark logs
echo 3: Remove containers (docker compose down -v)
echo 4: Exit
echo.

set /p choice="Enter your choice (1, 2, 3, or 4): "

if "%choice%"=="1" goto kafka
if "%choice%"=="2" goto spark
if "%choice%"=="3" goto remove
if "%choice%"=="4" goto end

echo Invalid choice! Please try again.
goto menu

:kafka
echo.
echo ========================================================
echo Showing Kafka logs (Press Ctrl+C, then N to return to menu)
echo ========================================================
docker compose logs -f iot-producer
goto menu

:spark
echo.
echo ========================================================
echo Showing Spark logs (Press Ctrl+C, then N to return to menu)
echo ========================================================
docker compose logs -f spark-consumer
goto menu

:remove
echo.
echo ========================================================
echo Removing containers and volumes...
echo ========================================================
docker compose down -v 

echo.
echo ========================================================
echo Cleaning up kafka-storage...
echo ========================================================
if exist "kafka-storage" (
    rmdir /s /q "kafka-storage"
    echo kafka-storage removed successfully.
) else (
    echo kafka-storage folder not found.
)


:end
echo Exiting...