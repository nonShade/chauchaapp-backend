#!/bin/bash
# ============================================================
# ChauchaApp Database Initialization Script
# ============================================================
# This script runs when the PostgreSQL container starts for the
# first time (mounted in /docker-entrypoint-initdb.d/).
#
# It performs:
# 1. Creates QA and Production databases
# 2. Applies the full schema to ALL databases (dev, qa, prod)
# 3. Grants permissions
# ============================================================

set -e

echo "=== ChauchaApp: Starting database initialization ==="

# ---------------------------------------------------------
# 1. Create additional databases for QA and Production
# ---------------------------------------------------------
echo "Creating QA and Production databases..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE chauchaapp_db_qa;
    CREATE DATABASE chauchaapp_db_prod;
EOSQL

# ---------------------------------------------------------
# 2. Apply schema to ALL databases
# ---------------------------------------------------------
SCHEMA_FILE="/docker-scripts/schema.sql"

if [ ! -f "$SCHEMA_FILE" ]; then
    echo "ERROR: Schema file not found at $SCHEMA_FILE"
    exit 1
fi

for db in "$POSTGRES_DB" chauchaapp_db_qa chauchaapp_db_prod; do
    echo "Applying schema to database: $db"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" -f "$SCHEMA_FILE"
    echo "Schema applied successfully to $db"
done

# ---------------------------------------------------------
# 3. Apply QA seed data (to QA + Production databases)
# ---------------------------------------------------------
SEED_FILE="/docker-scripts/seed-qa.sql"

if [ -f "$SEED_FILE" ]; then
    for db in chauchaapp_db_qa chauchaapp_db_prod; do
        echo "Applying QA seed data to $db..."
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" -f "$SEED_FILE"
        echo "QA seed data applied successfully to $db"
    done
else
    echo "No QA seed file found, skipping..."
fi

# ---------------------------------------------------------
# 4. Grant permissions
# ---------------------------------------------------------
echo "Granting permissions..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE chauchaapp_db_qa TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE chauchaapp_db_prod TO $POSTGRES_USER;
EOSQL

echo "=== ChauchaApp: Database initialization complete ==="
