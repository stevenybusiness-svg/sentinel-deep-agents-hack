# Sentinel — Production Deployment Guide

Complete guide for deploying Sentinel to AWS EC2 + Vercel for the Deep Agents Hackathon demo.

## Architecture Overview

```
User Browser
    ↓
Vercel (Frontend - React SPA)
    ↓ /api/* rewrites
AWS EC2 Instance
    ↓
Caddy (HTTPS + Reverse Proxy)
    ↓
FastAPI (Backend)
    ↓
Aerospike (Database)
```

## Prerequisites

- AWS account with EC2 access
- Vercel account
- Domain or use free nip.io DNS
- Anthropic API key
- Auth0 account (already configured)
- Slack webhook URL (already configured)

## Quick Start

### 1. Launch EC2 Instance

**AWS Console → EC2 → Launch Instance:**

- **Name:** sentinel-backend
- **AMI:** Amazon Linux 2023
- **Instance Type:** t3.medium
- **Key Pair:** Create or select existing
- **Network Settings:**
  - Allow HTTPS (443) from 0.0.0.0/0
  - Allow HTTP (80) from 0.0.0.0/0
  - Allow SSH (22) from your IP
- **Storage:** 20 GB gp3
- **Launch Instance**

**Allocate Elastic IP:**
1. EC2 → Elastic IPs → Allocate Elastic IP address
2. Actions → Associate Elastic IP address
3. Select your instance
4. Note the Elastic IP (e.g., 54.123.45.67)

### 2. Connect and Setup

```bash
# SSH into instance
ssh -i your-key.pem ec2-user@YOUR_ELASTIC_IP

# Run initial setup
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/sentinel/main/scripts/setup-ec2-instance.sh | bash

# Log out and back in for Docker group
exit
ssh -i your-key.pem ec2-user@YOUR_ELASTIC_IP
```

### 3. Clone and Configure

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/sentinel.git
cd sentinel

# Create environment file
cp .env.example .env
nano .env
```

**Edit .env with your values:**
```bash
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
AEROSPIKE_HOST=aerospike
AEROSPIKE_PORT=3000
AEROSPIKE_NAMESPACE=sentinel
VITE_AUTH0_DOMAIN=dev-ofumehudzqxsxkzh.us.auth0.com
VITE_AUTH0_CLIENT_ID=LvVkv13yfh3f9RytnH2OcownWd67k21E
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
PUBLIC_HOST=https://YOUR_ELASTIC_IP.nip.io
```

### 4. Deploy Backend

```bash
# Run deployment script
./scripts/deploy-ec2.sh
```

The script will:
- Install Docker and Docker Compose
- Validate environment variables
- Configure domain (using nip.io for free DNS)
- Build and start services
- Wait for health check
- Display deployment info

**Verify deployment:**
```bash
# Check health
curl https://YOUR_ELASTIC_IP.nip.io/health

# Should return:
# {"status":"ok","aerospike":true}
```

### 5. Deploy Frontend to Vercel

**Update vercel.json:**
```bash
# Replace YOUR_EC2_DOMAIN with your actual domain
sed -i '' 's/YOUR_EC2_DOMAIN/YOUR_ELASTIC_IP.nip.io/g' vercel.json
```

**Commit changes:**
```bash
git add vercel.json
git commit -m "Update EC2 domain for production"
git push
```

**Deploy to Vercel:**

Option A - Via Vercel Dashboard:
1. Go to vercel.com
2. Import your GitHub repository
3. Set environment variables:
   - `VITE_API_URL=https://YOUR_ELASTIC_IP.nip.io`
   - `VITE_WS_URL=wss://YOUR_ELASTIC_IP.nip.io/ws`
   - `VITE_AUTH0_DOMAIN=dev-ofumehudzqxsxkzh.us.auth0.com`
   - `VITE_AUTH0_CLIENT_ID=LvVkv13yfh3f9RytnH2OcownWd67k21E`
4. Deploy

Option B - Via CLI:
```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Set environment variables
vercel env add VITE_API_URL production
# Enter: https://YOUR_ELASTIC_IP.nip.io

vercel env add VITE_WS_URL production
# Enter: wss://YOUR_ELASTIC_IP.nip.io/ws

vercel env add VITE_AUTH0_DOMAIN production
# Enter: dev-ofumehudzqxsxkzh.us.auth0.com

vercel env add VITE_AUTH0_CLIENT_ID production
# Enter: LvVkv13yfh3f9RytnH2OcownWd67k21E

# Deploy
vercel --prod
```

### 6. Update Auth0 Configuration

1. Go to Auth0 Dashboard → Applications → Your App
2. Add your Vercel URL to:
   - **Allowed Callback URLs:** `https://your-app.vercel.app/callback`
   - **Allowed Logout URLs:** `https://your-app.vercel.app`
   - **Allowed Web Origins:** `https://your-app.vercel.app`
3. Save changes

### 7. Test End-to-End

1. Navigate to your Vercel URL: `https://your-app.vercel.app`
2. Login with Auth0
3. Run Attack Scenario 1 (Hidden Text)
4. Verify rule generation
5. Run Attack Scenario 2 (Agent Spoofing)
6. Verify generated rule fires
7. Check Slack for report

## Verification Checklist

- [ ] Backend health check returns OK
- [ ] HTTPS works without certificate warnings
- [ ] WebSocket connects successfully
- [ ] Auth0 login works
- [ ] Attack 1 blocks and generates rule
- [ ] Attack 2 blocks with generated rule
- [ ] Investigation tree displays correctly
- [ ] Verdict board shows mismatches
- [ ] Forensic scan visible
- [ ] Generated rule source displayed
- [ ] Slack report delivered
- [ ] Aerospike latency < 10ms

## Troubleshooting

### Backend Issues

```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build
```

### Frontend Issues

```bash
# Check Vercel deployment logs
vercel logs

# Verify environment variables
vercel env ls

# Redeploy
vercel --prod --force
```

### WebSocket Issues

```bash
# Test WebSocket connection
npm install -g wscat
wscat -c wss://YOUR_ELASTIC_IP.nip.io/ws

# Check Caddy logs
docker-compose -f docker-compose.prod.yml logs caddy
```

### Aerospike Issues

```bash
# Check Aerospike status
docker-compose -f docker-compose.prod.yml exec aerospike asinfo -v status

# Check connectivity
docker-compose -f docker-compose.prod.yml exec sentinel ping aerospike
```

## Auto-Restart on Reboot

```bash
# Create systemd service
sudo tee /etc/systemd/system/sentinel.service > /dev/null <<EOF
[Unit]
Description=Sentinel Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ec2-user/sentinel
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
User=ec2-user

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl enable sentinel.service
sudo systemctl start sentinel.service

# Test reboot
sudo reboot
```

## Maintenance

### View Logs
```bash
docker-compose -f docker-compose.prod.yml logs -f
```

### Update Deployment
```bash
git pull
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### Monitor Resources
```bash
docker stats
htop
```

### Backup Data
```bash
# Backup Aerospike
docker-compose -f docker-compose.prod.yml exec aerospike \
  asbackup --namespace sentinel --directory /opt/aerospike/data/backup

# Copy backup to local
docker cp $(docker-compose -f docker-compose.prod.yml ps -q aerospike):/opt/aerospike/data/backup ./backup
```

## Security Best Practices

1. **Restrict SSH access** to your IP only
2. **Rotate API keys** regularly
3. **Use AWS Secrets Manager** for production (not .env)
4. **Enable CloudWatch** logging
5. **Set up AWS Backup** for EC2 snapshots
6. **Monitor CloudTrail** for suspicious activity
7. **Keep Docker images updated**

## Cost Estimate

- **EC2 t3.medium:** ~$30/month
- **Elastic IP:** Free (when associated)
- **Data transfer:** ~$1-5/month
- **Vercel:** Free tier
- **Total:** ~$35/month

## Architecture Details

### Ports

| Port | Service | Exposure |
|------|---------|----------|
| 443 | Caddy HTTPS | Public |
| 80 | Caddy HTTP redirect | Public |
| 8000 | FastAPI | Internal (via Caddy) |
| 3000 | Aerospike | Internal only |

### Docker Compose Services

- **aerospike:** Database for episodes, rules, verdicts
- **sentinel:** FastAPI backend + React static files
- **caddy:** HTTPS reverse proxy with auto Let's Encrypt

### Environment Variables

**Backend (.env on EC2):**
- `ANTHROPIC_API_KEY` - Claude API access
- `AEROSPIKE_HOST` - Database host (aerospike)
- `AEROSPIKE_NAMESPACE` - Database namespace
- `SLACK_WEBHOOK_URL` - Slack notifications
- `PUBLIC_HOST` - Public URL for callbacks

**Frontend (Vercel dashboard):**
- `VITE_API_URL` - Backend API URL
- `VITE_WS_URL` - WebSocket URL
- `VITE_AUTH0_DOMAIN` - Auth0 tenant
- `VITE_AUTH0_CLIENT_ID` - Auth0 app ID

## Support

For issues during deployment:
1. Check logs: `docker-compose -f docker-compose.prod.yml logs`
2. Verify health: `curl https://YOUR_DOMAIN/health`
3. Test WebSocket: `wscat -c wss://YOUR_DOMAIN/ws`
4. Review security groups in AWS Console
5. Check Vercel deployment logs

## Success Criteria

✅ Backend responds to health checks
✅ HTTPS certificate valid
✅ WebSocket connects
✅ Auth0 login works
✅ Both attack scenarios run successfully
✅ Rule generation and firing works
✅ Slack reports delivered
✅ Services auto-restart on reboot
✅ Aerospike latency < 10ms
✅ No errors in production logs

---

**Ready for Demo Day! 🚀**
