#!/bin/bash
# Sentinel — Complete Deployment Orchestrator
# Run this locally to guide through the entire deployment process

set -e

echo "🚀 Sentinel Complete Deployment"
echo "================================"
echo ""
echo "This script will guide you through deploying Sentinel to AWS + Vercel"
echo ""

# Step 1: Pre-flight check
echo "Step 1: Pre-Flight Check"
echo "------------------------"
./scripts/preflight-check.sh
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Pre-flight check failed. Please fix errors and try again."
    exit 1
fi
echo ""

# Step 2: AWS Setup Instructions
echo "Step 2: AWS EC2 Setup"
echo "---------------------"
echo ""
echo "Please complete these steps in AWS Console:"
echo ""
echo "1. Go to EC2 → Launch Instance"
echo "   - Name: sentinel-backend"
echo "   - AMI: Amazon Linux 2023"
echo "   - Instance Type: t3.medium"
echo "   - Key Pair: Select or create"
echo ""
echo "2. Configure Security Group:"
echo "   - Port 443 (HTTPS) - Source: 0.0.0.0/0"
echo "   - Port 80 (HTTP) - Source: 0.0.0.0/0"
echo "   - Port 22 (SSH) - Source: Your IP"
echo ""
echo "3. Storage: 20 GB gp3"
echo ""
echo "4. Launch Instance"
echo ""
echo "5. Allocate Elastic IP:"
echo "   - EC2 → Elastic IPs → Allocate"
echo "   - Actions → Associate with your instance"
echo ""
read -p "Press Enter when EC2 instance is ready..."
echo ""

# Get EC2 details
read -p "Enter your EC2 Elastic IP: " ELASTIC_IP
read -p "Enter path to your SSH key (.pem file): " SSH_KEY

if [ ! -f "$SSH_KEY" ]; then
    echo "❌ SSH key not found: $SSH_KEY"
    exit 1
fi

# Test SSH connection
echo ""
echo "🔌 Testing SSH connection..."
if ssh -i "$SSH_KEY" -o ConnectTimeout=5 -o StrictHostKeyChecking=no ec2-user@"$ELASTIC_IP" "echo 'Connection successful'" 2>/dev/null; then
    echo "✅ SSH connection successful"
else
    echo "❌ SSH connection failed"
    echo "Please check:"
    echo "  - Elastic IP is correct"
    echo "  - SSH key has correct permissions (chmod 400)"
    echo "  - Security group allows SSH from your IP"
    exit 1
fi
echo ""

# Step 3: Deploy to EC2
echo "Step 3: Deploy Backend to EC2"
echo "------------------------------"
echo ""
echo "The following commands will be executed on your EC2 instance:"
echo "1. Run initial setup (install Docker, git, etc.)"
echo "2. Clone repository"
echo "3. Configure environment"
echo "4. Deploy services"
echo ""
read -p "Proceed with EC2 deployment? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 1
fi

# Get repository URL
echo ""
read -p "Enter your GitHub repository URL: " REPO_URL

# Create deployment commands
DEPLOY_COMMANDS=$(cat <<'EOF'
# Initial setup
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/sentinel/main/scripts/setup-ec2-instance.sh | bash

# Wait for Docker group to take effect
echo "Logging out and back in for Docker group..."
EOF
)

echo ""
echo "🚀 Running initial setup on EC2..."
ssh -i "$SSH_KEY" ec2-user@"$ELASTIC_IP" "bash -s" <<EOF
sudo yum update -y
sudo yum install -y git docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
echo "✅ Initial setup complete"
EOF

echo ""
echo "📦 Cloning repository and deploying..."
ssh -i "$SSH_KEY" ec2-user@"$ELASTIC_IP" "bash -s" <<EOF
# Clone repository
if [ ! -d "sentinel" ]; then
    git clone $REPO_URL sentinel
fi
cd sentinel

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️  .env created from template - you need to add secrets"
fi

# Run deployment
./scripts/deploy-ec2.sh
EOF

DOMAIN="${ELASTIC_IP}.nip.io"
echo ""
echo "✅ EC2 deployment complete!"
echo ""
echo "Backend URL: https://${DOMAIN}"
echo ""

# Step 4: Verify EC2 deployment
echo "Step 4: Verify EC2 Deployment"
echo "------------------------------"
echo ""
read -p "Run verification tests? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    ./scripts/verify-deployment.sh "$DOMAIN"
fi
echo ""

# Step 5: Deploy to Vercel
echo "Step 5: Deploy Frontend to Vercel"
echo "----------------------------------"
echo ""
read -p "Deploy to Vercel now? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    ./scripts/deploy-vercel.sh "$DOMAIN"
else
    echo "Skipping Vercel deployment"
    echo ""
    echo "To deploy later, run:"
    echo "  ./scripts/deploy-vercel.sh $DOMAIN"
fi
echo ""

# Step 6: Final instructions
echo "Step 6: Final Configuration"
echo "---------------------------"
echo ""
echo "📝 Complete these final steps:"
echo ""
echo "1. Update Auth0 configuration:"
echo "   → Auth0 Dashboard → Applications → Your App"
echo "   → Add your Vercel URL to:"
echo "     - Allowed Callback URLs"
echo "     - Allowed Logout URLs"
echo "     - Allowed Web Origins"
echo ""
echo "2. Test end-to-end:"
echo "   → Open your Vercel URL"
echo "   → Login with Auth0"
echo "   → Run Attack Scenario 1"
echo "   → Run Attack Scenario 2"
echo "   → Verify Slack report"
echo ""
echo "3. Configure auto-restart (on EC2):"
echo "   ssh -i $SSH_KEY ec2-user@$ELASTIC_IP"
echo "   cd sentinel"
echo "   ./scripts/install-systemd-service.sh"
echo ""
echo "✅ Deployment orchestration complete!"
echo ""
echo "📋 Deployment Summary:"
echo "   EC2 Domain: https://${DOMAIN}"
echo "   WebSocket: wss://${DOMAIN}/ws"
echo ""
echo "For troubleshooting, see DEPLOYMENT.md"
echo ""
