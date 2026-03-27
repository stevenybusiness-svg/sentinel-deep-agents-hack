#!/bin/bash
# Sentinel — Vercel Deployment Helper
# Run this locally after EC2 is deployed

set -e

echo "🌐 Sentinel Vercel Deployment"
echo "=============================="
echo ""

# Check if EC2 domain is provided
if [ -z "$1" ]; then
    echo "Usage: ./deploy-vercel.sh YOUR_EC2_DOMAIN"
    echo "Example: ./deploy-vercel.sh 54.123.45.67.nip.io"
    exit 1
fi

EC2_DOMAIN=$1
API_URL="https://${EC2_DOMAIN}"
WS_URL="wss://${EC2_DOMAIN}/ws"

echo "EC2 Domain: $EC2_DOMAIN"
echo "API URL: $API_URL"
echo "WebSocket URL: $WS_URL"
echo ""

# Verify EC2 backend is healthy
echo "🔍 Verifying EC2 backend..."
HEALTH_CHECK=$(curl -s "${API_URL}/health" || echo "")

if echo "$HEALTH_CHECK" | grep -q '"status":"ok"'; then
    echo "✅ EC2 backend is healthy"
else
    echo "❌ EC2 backend health check failed"
    echo "   Response: $HEALTH_CHECK"
    echo ""
    echo "Please ensure your EC2 backend is running before deploying to Vercel"
    exit 1
fi
echo ""

# Update vercel.json
echo "📝 Updating vercel.json..."
if grep -q "YOUR_EC2_DOMAIN" vercel.json; then
    sed -i.bak "s/YOUR_EC2_DOMAIN/${EC2_DOMAIN}/g" vercel.json
    echo "✅ vercel.json updated"
else
    echo "⚠️  vercel.json already configured or placeholder not found"
fi
echo ""

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "📦 Vercel CLI not found. Install it?"
    read -p "Install Vercel CLI? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        npm install -g vercel
    else
        echo "Please install Vercel CLI: npm install -g vercel"
        exit 1
    fi
fi

# Prompt for deployment method
echo "Choose deployment method:"
echo "1. Deploy via Vercel CLI (automated)"
echo "2. Show manual instructions for Vercel Dashboard"
echo ""
read -p "Enter choice (1 or 2): " -n 1 -r
echo ""
echo ""

if [[ $REPLY = "1" ]]; then
    echo "🚀 Deploying to Vercel via CLI..."
    echo ""
    
    # Check if logged in
    if ! vercel whoami &> /dev/null; then
        echo "Please login to Vercel:"
        vercel login
    fi
    
    # Set environment variables
    echo "Setting environment variables..."
    vercel env add VITE_API_URL production --force <<< "$API_URL"
    vercel env add VITE_WS_URL production --force <<< "$WS_URL"
    vercel env add VITE_AUTH0_DOMAIN production --force <<< "dev-ofumehudzqxsxkzh.us.auth0.com"
    vercel env add VITE_AUTH0_CLIENT_ID production --force <<< "LvVkv13yfh3f9RytnH2OcownWd67k21E"
    
    echo ""
    echo "Deploying..."
    vercel --prod
    
    echo ""
    echo "✅ Deployment complete!"
    
elif [[ $REPLY = "2" ]]; then
    echo "📋 Manual Deployment Instructions"
    echo "=================================="
    echo ""
    echo "1. Go to vercel.com and import your repository"
    echo ""
    echo "2. Set these environment variables in Vercel Dashboard:"
    echo "   → Settings → Environment Variables"
    echo ""
    echo "   VITE_API_URL=$API_URL"
    echo "   VITE_WS_URL=$WS_URL"
    echo "   VITE_AUTH0_DOMAIN=dev-ofumehudzqxsxkzh.us.auth0.com"
    echo "   VITE_AUTH0_CLIENT_ID=LvVkv13yfh3f9RytnH2OcownWd67k21E"
    echo ""
    echo "3. Commit and push vercel.json changes:"
    echo "   git add vercel.json"
    echo "   git commit -m 'Update EC2 domain for production'"
    echo "   git push"
    echo ""
    echo "4. Deploy from Vercel Dashboard"
    echo ""
else
    echo "Invalid choice"
    exit 1
fi

echo ""
echo "📝 Final Steps:"
echo "==============="
echo ""
echo "1. Update Auth0 configuration:"
echo "   → Auth0 Dashboard → Applications → Your App → Settings"
echo "   → Add your Vercel URL to:"
echo "     - Allowed Callback URLs"
echo "     - Allowed Logout URLs"
echo "     - Allowed Web Origins"
echo ""
echo "2. Test the deployment:"
echo "   → Open your Vercel URL"
echo "   → Login with Auth0"
echo "   → Run Attack Scenario 1"
echo "   → Run Attack Scenario 2"
echo "   → Verify Slack report"
echo ""
echo "🎉 Deployment complete!"
echo ""
