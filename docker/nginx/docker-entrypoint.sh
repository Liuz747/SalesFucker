#!/bin/sh

HTTPS_CONFIG=''

if [ "${NGINX_HTTPS_ENABLED}" = "true" ]; then
    if [ -f "/etc/ssl/${NGINX_SSL_CERT_FILENAME}" ] && [ -f "/etc/ssl/${NGINX_SSL_CERT_KEY_FILENAME}" ]; then
        SSL_CERTIFICATE_PATH="/etc/ssl/${NGINX_SSL_CERT_FILENAME}"
        SSL_CERTIFICATE_KEY_PATH="/etc/ssl/${NGINX_SSL_CERT_KEY_FILENAME}"
        export SSL_CERTIFICATE_PATH
        export SSL_CERTIFICATE_KEY_PATH

        # Inject HTTPS config
        HTTPS_CONFIG=$(envsubst < /etc/nginx/https.conf.template)
        export HTTPS_CONFIG
    else
        echo "WARNING: NGINX_HTTPS_ENABLED is true but SSL certificates not found"
        echo "Expected: /etc/ssl/${NGINX_SSL_CERT_FILENAME} and /etc/ssl/${NGINX_SSL_CERT_KEY_FILENAME}"
    fi
fi
export HTTPS_CONFIG

# Get all environment variables and substitute them in the template
env_vars=$(printenv | cut -d= -f1 | sed 's/^/$/g' | paste -sd, -)

# Process proxy.conf template
envsubst "$env_vars" < /etc/nginx/proxy.conf.template > /etc/nginx/proxy.conf

# Process main nginx.conf template
envsubst "$env_vars" < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Start Nginx
exec nginx -g 'daemon off;'