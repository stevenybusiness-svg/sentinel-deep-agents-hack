#!/bin/bash
# Sentinel — EC2 First-Time Init
# Run this once on a fresh EC2 instance. Does everything.
#
# Before running, create .env manually:
#   nano .env
# Add your keys (ANTHROPIC_API_KEY, AEROSPIKE_NAMESPACE, SLACK_WEBHOOK_URL, PUBLIC_HOST)
set -e

echo "=== Sentinel EC2 Init ==="

# Check .env exists
if [ ! -f .env ]; then
  echo "Creating .env — you'll need to paste your API key..."
  read -p "ANTHROPIC_API_KEY: " API_KEY
  read -p "SLACK_WEBHOOK_URL (or press Enter to skip): " SLACK_URL

  {
    echo "ANTHROPIC_API_KEY=$API_KEY"
    echo "AEROSPIKE_NAMESPACE=sentinel"
    echo "PUBLIC_HOST=https://3.20.246.253.nip.io"
    [ -n "$SLACK_URL" ] && echo "SLACK_WEBHOOK_URL=$SLACK_URL"
  } > .env
  echo ".env created"
else
  echo ".env found"
fi

# Fix Caddyfile domain
sed -i 's/YOUR_DOMAIN/3.20.246.253.nip.io/g' Caddyfile 2>/dev/null || true
echo "Caddyfile updated"

# Build and start
sudo docker-compose -f docker-compose.prod.yml build
sudo docker-compose -f docker-compose.prod.yml up -d

# Health check
echo "Waiting for backend..."
for i in $(seq 1 20); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "Backend is healthy!"
    echo ""
    echo "=== Done ==="
    echo "Backend: https://3.20.246.253.nip.io"
    exit 0
  fi
  sleep 3
done
echo "WARNING: Backend not healthy. Check: sudo docker-compose -f docker-compose.prod.yml logs --tail=50"
