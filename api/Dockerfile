# Use local base image with Python 3.13
ARG REGISTRY_URL
FROM ${REGISTRY_URL}/api-base:latest

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Copy and set permissions for entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY scripts/database.py /app/scripts/database.py

# Expose port
EXPOSE 8000

# Run the application via entrypoint script
ENTRYPOINT ["/bin/bash", "/entrypoint.sh"] 