#!/bin/bash

# Environment Management Script
# Usage: ./manage-env.sh [development|staging|production]

set -e

ENVIRONMENT=${1:-development}

echo "🚀 Setting up environment: $ENVIRONMENT"

case $ENVIRONMENT in
  "development")
    echo "📝 Using development configuration (.env)"
    if [ ! -f .env ]; then
      echo "❌ .env file not found!"
      exit 1
    fi
    docker-compose up -d
    ;;
    
  "staging")
    echo "📝 Using staging configuration (.env.staging)"
    if [ ! -f .env.staging ]; then
      echo "❌ .env.staging file not found!"
      echo "💡 Copy .env.staging template and configure it"
      exit 1
    fi
    docker-compose --env-file .env.staging up -d
    ;;
    
  "production")
    echo "📝 Using production configuration (.env.production)"
    if [ ! -f .env.production ]; then
      echo "❌ .env.production file not found!"
      echo "💡 Copy .env.production template and configure it"
      exit 1
    fi
    docker-compose --env-file .env.production up -d
    ;;
    
  *)
    echo "❌ Invalid environment: $ENVIRONMENT"
    echo "💡 Usage: ./manage-env.sh [development|staging|production]"
    exit 1
    ;;
esac

echo "✅ Environment $ENVIRONMENT is running!"
echo "🔍 Check status with: docker-compose ps"
echo "📋 View logs with: docker-compose logs -f"