#!/bin/bash

# Docker Development Environment Management Script

set -e

COMPOSE_FILE="docker/docker-compose.yml"

case "$1" in
    "up")
        echo "🚀 Starting MAS development environment..."
        docker compose -f $COMPOSE_FILE up -d
        echo "✅ Services started successfully!"
        echo "📊 Elasticsearch: http://localhost:9200"
        echo "🔴 Redis: localhost:6379"
        echo "🌐 API will be available at: http://localhost:8000"
        ;;
    "down")
        echo "⏹️  Stopping MAS development environment..."
        docker compose -f $COMPOSE_FILE down
        echo "✅ Services stopped successfully!"
        ;;
    "restart")
        echo "🔄 Restarting MAS development environment..."
        docker compose -f $COMPOSE_FILE restart
        echo "✅ Services restarted successfully!"
        ;;
    "logs")
        if [ -n "$2" ]; then
            docker compose -f $COMPOSE_FILE logs -f "$2"
        else
            docker compose -f $COMPOSE_FILE logs -f
        fi
        ;;
    "status")
        docker compose -f $COMPOSE_FILE ps
        ;;
    "clean")
        echo "🧹 Cleaning up MAS development environment..."
        docker compose -f $COMPOSE_FILE down -v --remove-orphans
        docker system prune -f
        echo "✅ Environment cleaned successfully!"
        ;;
    *)
        echo "Usage: $0 {up|down|restart|logs [service]|status|clean}"
        echo ""
        echo "Commands:"
        echo "  up       - Start all services"
        echo "  down     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  logs     - Show logs (optionally for specific service)"
        echo "  status   - Show service status"
        echo "  clean    - Stop services and clean up volumes"
        exit 1
        ;;
esac 