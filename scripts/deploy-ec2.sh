#!/bin/bash
# Sentinel — EC2 Deployment Script
# Run this on your EC2 instance after initial setup

set -e

echo "🚀 Sentinel EC2 Deployment Script"
echo "=================================="

# Check if running on EC2
if [ ! -f /sys/hypervisor/uuid ] || ! grep -q ec2 /sys/hypervisor/uuid 2>/dev/null; then
    echo "⚠️  Warning: This doesn't appear to be an EC2 instance"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    sudo yum update -y
    sudo yum install -y docker
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -a -G docker ec2-user
    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose installed"
else
    echo "✅ Docker Compose already installed"
fi

# Check for .env file
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please create .env from .env.example and add your secrets"
    exit 1
fi

# Validate required env vars
echo "🔍 Validating environment variables..."
required_vars=("ANTHROPIC_API_KEY" "AEROSPIKE_NAMESPACE")
missing_vars=()

for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" .env || grep -q "^${var}=$" .env || grep -q "^${var}=.*your.*here" .env; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "❌ Missing or invalid environment variables:"
    printf '   - %s\n' "${missing_vars[@]}"
    exit 1
fi

echo "✅ Environment variables validated"

# Get Elastic IP or public IP
echo "🌐 Detecting public IP..."
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 || echo "")
if [ -z "$PUBLIC_IP" ]; then
    echo "⚠️  Could not detect EC2 public IP"
    read -p "Enter your EC2 public IP or domain: " PUBLIC_IP
fi

# Use nip.io for free DNS with Let's Encrypt
DOMAIN="${PUBLIC_IP}.nip.io"
echo "📍 Using domain: $DOMAIN"

# Update Caddyfile with actual domain
echo "📝 Updating Caddyfile..."
sed -i.bak "s/YOUR_DOMAIN/${DOMAIN}/g" Caddyfile
echo "✅ Caddyfile updated"

# Update .env with PUBLIC_HOST
if ! grep -q "^PUBLIC_HOST=" .env; then
    echo "PUBLIC_HOST=https://${DOMAIN}" >> .env
else
    sed -i.bak "s|^PUBLIC_HOST=.*|PUBLIC_HOST=https://${DOMAIN}|" .env
fi
echo "✅ PUBLIC_HOST updated in .env"

# Build and start services
echo "🏗️  Building Docker images..."
docker-compose -f docker-compose.prod.yml build

echo "🚀 Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health
echo "🏥 Checking service health..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend is healthy"
        break
    fi
    attempt=$((attempt + 1))
    echo "   Attempt $attempt/$max_attempts..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Backend failed to become healthy"
    echo "📋 Checking logs..."
    docker-compose -f docker-compose.prod.yml logs --tail=50
    exit 1
fi

# Display deployment info
echo ""
echo "✅ Deployment Complete!"
echo "======================="
echo ""
echo "🌐 Your Sentinel backend is running at:"
echo "   https://${DOMAIN}"
echo ""
echo "🔍 Health check:"
echo "   curl https://${DOMAIN}/health"
echo ""
echo "📡 WebSocket endpoint:"
echo "   wss://${DOMAIN}/ws"
echo ""
echo "📝 Next steps:"
echo "   1. Update Vercel environment variables:"
echo "      VITE_API_URL=https://${DOMAIN}"
echo "      VITE_WS_URL=wss://${DOMAIN}/ws"
echo ""
echo "   2. Update vercel.json rewrites:"
echo "      Replace YOUR_EC2_DOMAIN with: ${DOMAIN}"
echo ""
echo "   3. Deploy to Vercel:"
echo "      cd frontend && vercel --prod"
echo ""
echo "📊 View logs:"
echo "   docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "🔄 Restart services:"
echo "   docker-compose -f docker-compose.prod.yml restart"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose -f docker-compose.prod.yml down"
echo ""
