#!/bin/sh

# Run cleanup script before running migrations
# Check if DATABASE_URL is not set
if [ -z "$DATABASE_URL" ]; then
    # Check if all required variables are provided
    if [ -n "$DATABASE_HOST" ] && [ -n "$DATABASE_USERNAME" ] && [ -n "$DATABASE_PASSWORD" ]  && [ -n "$DATABASE_NAME" ]; then
        # Construct DATABASE_URL from the provided variables
        DATABASE_URL="postgresql://${DATABASE_USERNAME}:${DATABASE_PASSWORD}@${DATABASE_HOST}/${DATABASE_NAME}"
        export DATABASE_URL
    else
        echo "Error: Required database environment variables are not set. Provide a postgres url for DATABASE_URL."
        exit 1
    fi
    if [ -n "$DATABASE_ARGS" ]; then
        # Append ARGS to DATABASE_URL
        DATABASE_URL="${DATABASE_URL}?$DATABASE_ARGS"
        export DATABASE_URL
    fi
fi

# Auto-construct NEXTAUTH_URL from nginx config if not provided
if [ -z "$NEXTAUTH_URL" ]; then
    if [ -n "$NGINX_SERVER_NAME" ] && [ "$NGINX_SERVER_NAME" != "_" ]; then
        # Determine protocol based on HTTPS setting
        if [ "$NGINX_HTTPS_ENABLED" = "true" ]; then
            PROTOCOL="https"
        else
            PROTOCOL="http"
        fi
        NEXTAUTH_URL="${PROTOCOL}://${NGINX_SERVER_NAME}"
        export NEXTAUTH_URL
        echo "Auto-generated NEXTAUTH_URL: $NEXTAUTH_URL"
    else
        echo "Warning: NEXTAUTH_URL not set and cannot be auto-generated (NGINX_SERVER_NAME is '_' or not 
set)"
        echo "Falling back to default: http://localhost:3000"
        NEXTAUTH_URL="http://localhost:3000"
        export NEXTAUTH_URL
    fi
fi

# Check if CLICKHOUSE_URL is not set
if [ -z "$CLICKHOUSE_URL" ]; then
    echo "Error: CLICKHOUSE_URL is not configured. Migrating from V2? Check out migration guide: https://langfuse.com/self-hosting/upgrade-guides/upgrade-v2-to-v3"
    exit 1
fi

# Set DIRECT_URL to the value of DATABASE_URL if it is not set, required for migrations
if [ -z "$DIRECT_URL" ]; then
    export DIRECT_URL="${DATABASE_URL}"
fi

# Ensure target Postgres database exists before running migrations.
DB_NO_QUERY="${DATABASE_URL%%\?*}"
TARGET_DB="${DATABASE_NAME:-${DB_NO_QUERY##*/}}"
ADMIN_URL="${DB_NO_QUERY%/*}/${POSTGRES_MAINTENANCE_DB:-postgres}"
prisma db execute --url "$ADMIN_URL" -f "./frontend/scripts/create_database.sql"

# Always execute the postgres migration, except when disabled.
if [ "$LANGFUSE_AUTO_POSTGRES_MIGRATION_DISABLED" != "true" ]; then
    prisma db execute --url "$DIRECT_URL" --file "./packages/shared/scripts/cleanup.sql"

    # Apply migrations
    prisma migrate deploy --schema=./packages/shared/prisma/schema.prisma
fi
status=$?

# If migration fails (returns non-zero exit status), exit script with that status
if [ $status -ne 0 ]; then
    echo "Applying database migrations failed. This is mostly caused by the database being unavailable."
    echo "Exiting..."
    exit $status
fi

# Execute the Clickhouse migration, except when disabled.
if [ "$LANGFUSE_AUTO_CLICKHOUSE_MIGRATION_DISABLED" != "true" ]; then
    # Apply Clickhouse migrations
    cd ./packages/shared
    sh ./clickhouse/scripts/up.sh
    status=$?
    cd ../../
fi

# If migration fails (returns non-zero exit status), exit script with that status
if [ $status -ne 0 ]; then
    echo "Applying clickhouse migrations failed. This is mostly caused by the database being unavailable."
    echo "Exiting..."
    exit $status
fi

# Run the command passed to the docker image on start
exec "$@"
