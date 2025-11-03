#!/bin/sh

# Run cleanup script before running migrations
# Check if DATABASE_URL is not set
if [ -z "$DATABASE_URL" ]; then
    # Check if all required variables are provided
    if [ -n "$DATABASE_HOST" ] && [ -n "$DATABASE_USERNAME" ] && [ -n "$DATABASE_PASSWORD" ]  && [ -n "$DATABASE_NAME" ]; then
        # Construct DATABASE_URL from the provided variables
        DATABASE_URL="postgresql://${DATABASE_USERNAME}:${DATABASE_PASSWORD}@${DATABASE_HOST}"
    else
        echo "Error: Required database environment variables are not set. Provide a postgres url for DATABASE_URL."
        exit 1
    fi
fi

# At this point, DATABASE_URL should be the base URL
case "${DATABASE_URL%/}" in
    *://*/*)
        echo "Error: DATABASE_URL should be a base URL without database name."
        exit 1
        ;;
    *) DATABASE_URL="${DATABASE_URL%/}" ;;
esac

# Construct final DATABASE_URL with target database
DATABASE_URL="${DATABASE_URL}/${DATABASE_NAME}"

if [ -n "$DATABASE_ARGS" ]; then
    # Append ARGS to DATABASE_URL
    DATABASE_URL="${DATABASE_URL}?$DATABASE_ARGS"
fi

export DATABASE_URL

# Run the command passed to the docker image on start
exec "$@"
