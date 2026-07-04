FROM python:3.11-slim-bookworm

# ── System deps ─────────────────────────────────────────────
RUN apt-get update -o Acquire::Check-Valid-Until=false \
                   -o Acquire::Check-Date=false \
 && apt-get install -y curl apt-transport-https gnupg2 unixodbc-dev \
 && rm -rf /var/lib/apt/lists/*

# ── Microsoft ODBC 18 ────────────────────────────────────────
RUN curl -fsSL -k https://packages.microsoft.com/keys/microsoft.asc \
    | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
 && curl -fsSL -k https://packages.microsoft.com/config/debian/12/prod.list \
    | tee /etc/apt/sources.list.d/mssql-release.list

RUN apt-get update -o Acquire::Check-Valid-Until=false \
                   -o Acquire::Check-Date=false \
 && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# ── App ──────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
