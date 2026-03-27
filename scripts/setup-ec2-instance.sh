#!/bin/bash
# Sentinel — Initial EC2 Instance Setup
# Run this FIRST on a fresh EC2 instance before deploying

set -e

echo "🔧 Sentinel EC2 Initial Setup"
echo "=============================="

# Update system
echo "📦 Updating system packages..."
sudo yum update -y

# Install git
echo "📦 Installing git..."
sudo yum install -y git

# Install Docker
echo "📦 Installing Docker..."
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user

# Install Docker Compose
echo "📦 Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install useful tools
echo "📦 Installing utilities..."
sudo yum install -y htop curl wget

echo ""
echo "✅ Initial setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Log out and log back in for Docker group to take effect:"
echo "      exit"
echo "      ssh -i your-key.pem ec2-user@YOUR_ELASTIC_IP"
echo ""
echo "   2. Clone the repository:"
echo "      git clone https://github.com/YOUR_USERNAME/sentinel.git"
echo "      cd sentinel"
echo ""
echo "   3. Create .env file:"
echo "      cp .env.example .env"
echo "      nano .env  # Add your secrets"
echo ""
echo "   4. Run deployment script:"
echo "      ./scripts/deploy-ec2.sh"
echo ""
