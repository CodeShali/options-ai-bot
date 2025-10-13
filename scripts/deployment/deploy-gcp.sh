#!/bin/bash

# Deploy Options Trading Bot to Google Cloud Platform
# This script handles the complete deployment process

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Options Trading Bot - GCP Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found. Please install it first:${NC}"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Configuration
read -p "Enter your GCP Project ID: " PROJECT_ID
read -p "Enter region (default: us-central1): " REGION
REGION=${REGION:-us-central1}
read -p "Enter service name (default: options-trading-bot): " SERVICE_NAME
SERVICE_NAME=${SERVICE_NAME:-options-trading-bot}

echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service: $SERVICE_NAME"
echo ""

read -p "Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# Set project
echo -e "${YELLOW}📋 Setting GCP project...${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required APIs...${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com \
    cloudscheduler.googleapis.com

# Create secrets (if they don't exist)
echo -e "${YELLOW}🔐 Setting up secrets...${NC}"

create_secret() {
    local SECRET_NAME=$1
    local SECRET_DESCRIPTION=$2
    
    if gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &>/dev/null; then
        echo "  ✅ Secret $SECRET_NAME already exists"
    else
        echo "  📝 Creating secret: $SECRET_NAME"
        read -sp "  Enter value for $SECRET_DESCRIPTION: " SECRET_VALUE
        echo
        echo -n "$SECRET_VALUE" | gcloud secrets create $SECRET_NAME \
            --data-file=- \
            --replication-policy="automatic" \
            --project=$PROJECT_ID
        echo "  ✅ Created $SECRET_NAME"
    fi
}

create_secret "alpaca-api-key" "Alpaca API Key"
create_secret "alpaca-secret-key" "Alpaca Secret Key"
create_secret "discord-token" "Discord Bot Token"
create_secret "openai-api-key" "OpenAI API Key"
create_secret "anthropic-api-key" "Anthropic API Key"
create_secret "news-api-key" "NewsAPI Key"

# Build and push container
echo -e "${YELLOW}🐳 Building container image...${NC}"
gcloud builds submit \
    --tag gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --project=$PROJECT_ID \
    --timeout=20m

# Deploy to Cloud Run
echo -e "${YELLOW}🚀 Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --max-instances 1 \
    --min-instances 1 \
    --port 8000 \
    --cpu-throttling=false \
    --set-env-vars TRADING_MODE=paper \
    --set-secrets ALPACA_API_KEY=alpaca-api-key:latest,ALPACA_SECRET_KEY=alpaca-secret-key:latest,DISCORD_TOKEN=discord-token:latest,OPENAI_API_KEY=openai-api-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,NEWS_API_KEY=news-api-key:latest \
    --project=$PROJECT_ID

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --format 'value(status.url)' \
    --project=$PROJECT_ID)

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Service URL:${NC} $SERVICE_URL"
echo -e "${YELLOW}Health Check:${NC} $SERVICE_URL/health"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Test the health endpoint:"
echo "   curl $SERVICE_URL/health"
echo ""
echo "2. View logs:"
echo "   gcloud run services logs read $SERVICE_NAME --region=$REGION --project=$PROJECT_ID"
echo ""
echo "3. Monitor the service:"
echo "   https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME?project=$PROJECT_ID"
echo ""
echo -e "${GREEN}🎉 Your trading bot is now running on GCP!${NC}"
