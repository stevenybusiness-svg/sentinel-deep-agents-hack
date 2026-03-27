#!/bin/bash
# Sentinel — Install Systemd Service for Auto-Restart
# Run this on EC2 to enable auto-restart on reboot

set -e

echo "🔧 Installing Sentinel Systemd Service"
echo "======================================="
echo ""

# Check if running as ec2-user
if [ "$USER" != "ec2-user" ]; then
    echo "⚠️  Warning: This script should be run as ec2-user"
fi

# Get current directory
CURRENT_DIR=$(pwd)

# Check if we're in the sentinel directory
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "❌ Error: docker-compose.prod.yml not found"
    echo "Please run this script from the sentinel project directory"
    exit 1
fi

# Create systemd service file
echo "📝 Creating systemd service file..."
sudo tee /etc/systemd/system/sentinel.service > /dev/null <<EOF
[Unit]
Description=Sentinel Docker Compose Application
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${CURRENT_DIR}
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
ExecReload=/usr/local/bin/docker-compose -f docker-compose.prod.yml restart
User=ec2-user
Group=ec2-user
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file created at /etc/systemd/system/sentinel.service"
echo ""

# Reload systemd
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service
echo "✅ Enabling sentinel service..."
sudo systemctl enable sentinel.service

# Check if services are currently running
if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo "✅ Services already running"
else
    echo "🚀 Starting services..."
    sudo systemctl start sentinel.service
fi

# Check status
echo ""
echo "📊 Service Status:"
sudo systemctl status sentinel.service --no-pager || true

echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 Service commands:"
echo "   sudo systemctl start sentinel    # Start services"
echo "   sudo systemctl stop sentinel     # Stop services"
echo "   sudo systemctl restart sentinel  # Restart services"
echo "   sudo systemctl status sentinel   # Check status"
echo ""
echo "🔄 Auto-restart on reboot: ENABLED"
echo ""
echo "🧪 Test reboot:"
echo "   sudo reboot"
echo "   # After reboot, check: docker-compose -f docker-compose.prod.yml ps"
echo ""
