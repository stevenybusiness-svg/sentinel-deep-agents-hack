# Sentinel Deployment Scripts

Automated scripts for deploying Sentinel to AWS EC2 + Vercel.

## Scripts Overview

### 1. setup-ec2-instance.sh
**Purpose:** Initial EC2 instance setup (run once on fresh instance)

**What it does:**
- Updates system packages
- Installs Docker and Docker Compose
- Installs git and utilities
- Configures Docker group permissions

**Usage:**
```bash
# On fresh EC2 instance
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/sentinel/main/scripts/setup-ec2-instance.sh | bash

# Or after cloning
./scripts/setup-ec2-instance.sh
```

**When to use:** First time setting up a new EC2 instance

---

### 2. deploy-ec2.sh
**Purpose:** Deploy Sentinel backend to EC2

**What it does:**
- Validates environment variables
- Detects EC2 public IP
- Configures domain (using nip.io)
- Updates Caddyfile
- Builds Docker images
- Starts services (FastAPI + Aerospike + Caddy)
- Waits for health check
- Displays deployment info

**Usage:**
```bash
# After setup-ec2-instance.sh and .env configuration
./scripts/deploy-ec2.sh
```

**Prerequisites:**
- Docker and Docker Compose installed
- .env file configured with secrets
- Repository cloned

**When to use:** 
- Initial deployment
- Redeployment after code changes
- After configuration updates

---

### 3. deploy-vercel.sh
**Purpose:** Deploy frontend to Vercel

**What it does:**
- Verifies EC2 backend is healthy
- Updates vercel.json with EC2 domain
- Deploys to Vercel (CLI or manual instructions)
- Sets environment variables
- Displays next steps

**Usage:**
```bash
# Run locally after EC2 is deployed
./scripts/deploy-vercel.sh YOUR_EC2_DOMAIN

# Example
./scripts/deploy-vercel.sh 54.123.45.67.nip.io
```

**Prerequisites:**
- EC2 backend deployed and healthy
- Vercel CLI installed (optional)
- Git repository pushed

**When to use:**
- After EC2 deployment
- When updating frontend
- When changing EC2 domain

---

### 4. verify-deployment.sh
**Purpose:** Verify deployment is working correctly

**What it does:**
- Tests backend health endpoint
- Verifies HTTPS certificate
- Tests WebSocket connection
- Checks API endpoints
- Verifies static files served
- Checks Docker services (if on EC2)
- Provides summary report

**Usage:**
```bash
# Run on EC2 or locally
./scripts/verify-deployment.sh YOUR_DOMAIN

# Example
./scripts/verify-deployment.sh 54.123.45.67.nip.io
```

**Prerequisites:**
- Deployment completed
- curl installed
- wscat installed (optional, for WebSocket test)

**When to use:**
- After deployment
- When troubleshooting
- Before demo
- After configuration changes

---

## Deployment Workflow

### Complete Deployment (First Time)

```bash
# 1. Launch EC2 instance in AWS Console
#    - t3.medium, Amazon Linux 2023
#    - Security group: 443, 80, 22
#    - Allocate Elastic IP

# 2. SSH into instance
ssh -i your-key.pem ec2-user@YOUR_ELASTIC_IP

# 3. Run initial setup
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/sentinel/main/scripts/setup-ec2-instance.sh | bash

# 4. Log out and back in
exit
ssh -i your-key.pem ec2-user@YOUR_ELASTIC_IP

# 5. Clone repository
git clone https://github.com/YOUR_USERNAME/sentinel.git
cd sentinel

# 6. Configure environment
cp .env.example .env
nano .env  # Add your secrets

# 7. Deploy backend
./scripts/deploy-ec2.sh

# 8. Verify backend (on EC2)
./scripts/verify-deployment.sh YOUR_ELASTIC_IP.nip.io

# 9. Deploy frontend (run locally)
./scripts/deploy-vercel.sh YOUR_ELASTIC_IP.nip.io

# 10. Update Auth0 with Vercel URL

# 11. Test end-to-end from Vercel URL
```

### Update Deployment

```bash
# On EC2
cd sentinel
git pull
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Verify
./scripts/verify-deployment.sh YOUR_DOMAIN
```

### Redeploy Frontend Only

```bash
# Locally
./scripts/deploy-vercel.sh YOUR_EC2_DOMAIN
```

## Environment Variables

### Required in .env (EC2)

```bash
ANTHROPIC_API_KEY=sk-ant-your-key
AEROSPIKE_HOST=aerospike
AEROSPIKE_PORT=3000
AEROSPIKE_NAMESPACE=sentinel
VITE_AUTH0_DOMAIN=your-tenant.auth0.com
VITE_AUTH0_CLIENT_ID=your-client-id
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
PUBLIC_HOST=https://YOUR_DOMAIN
```

### Required in Vercel Dashboard

```bash
VITE_API_URL=https://YOUR_EC2_DOMAIN
VITE_WS_URL=wss://YOUR_EC2_DOMAIN/ws
VITE_AUTH0_DOMAIN=your-tenant.auth0.com
VITE_AUTH0_CLIENT_ID=your-client-id
```

## Troubleshooting

### Script fails with "Permission denied"

```bash
chmod +x scripts/*.sh
```

### Docker commands fail

```bash
# Log out and back in after setup-ec2-instance.sh
exit
ssh -i your-key.pem ec2-user@YOUR_ELASTIC_IP
```

### Health check fails

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Check services
docker-compose -f docker-compose.prod.yml ps

# Restart
docker-compose -f docker-compose.prod.yml restart
```

### HTTPS certificate issues

```bash
# Check Caddy logs
docker-compose -f docker-compose.prod.yml logs caddy

# Verify domain resolves
nslookup YOUR_DOMAIN

# Check if port 80 is accessible (needed for Let's Encrypt)
curl -I http://YOUR_DOMAIN
```

### WebSocket connection fails

```bash
# Install wscat
npm install -g wscat

# Test connection
wscat -c wss://YOUR_DOMAIN/ws

# Check Caddy WebSocket upgrade
docker-compose -f docker-compose.prod.yml logs caddy | grep -i websocket
```

## Quick Reference

### Common Commands

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Stop services
docker-compose -f docker-compose.prod.yml down

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build

# Check service status
docker-compose -f docker-compose.prod.yml ps

# Check resource usage
docker stats
```

### Health Checks

```bash
# Backend health
curl https://YOUR_DOMAIN/health

# WebSocket
wscat -c wss://YOUR_DOMAIN/ws

# API endpoint
curl https://YOUR_DOMAIN/api/investigate

# Aerospike
docker-compose -f docker-compose.prod.yml exec aerospike asinfo -v status
```

## Additional Resources

- **Full deployment guide:** See `DEPLOYMENT.md` in project root
- **Quick reference:** See `scripts/quick-deploy.md`
- **Deployment checklist:** See `.planning/phases/09-aws-deployment/DEPLOYMENT-CHECKLIST.md`
- **Phase 9 plan:** See `.planning/phases/09-aws-deployment/09-PLAN.md`

## Support

If you encounter issues:

1. Check logs: `docker-compose -f docker-compose.prod.yml logs`
2. Run verification: `./scripts/verify-deployment.sh YOUR_DOMAIN`
3. Review deployment guide: `DEPLOYMENT.md`
4. Check security groups in AWS Console
5. Verify environment variables
6. Test backend directly: `curl https://YOUR_DOMAIN/health`

## Notes

- **nip.io:** Free DNS service that resolves `IP.nip.io` to `IP`
- **Let's Encrypt:** Caddy automatically provisions HTTPS certificates
- **Auto-restart:** Configure systemd service for auto-restart on reboot
- **Cost:** ~$35/month (EC2 t3.medium + data transfer)
- **Backup:** Use AWS snapshots or `docker cp` for Aerospike data

---

**Ready to deploy? Start with `setup-ec2-instance.sh`**
