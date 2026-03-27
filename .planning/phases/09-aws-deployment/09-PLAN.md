# Phase 9: AWS Deployment via Kiro

**Goal:** Deploy backend + Aerospike to AWS EC2 using Kiro IDE. Connect Vercel frontend to EC2 backend. Verify full demo arc works from the deployed Vercel URL.

## Requirements

- DEPLOY-01: EC2 instance running Docker Compose with FastAPI + Aerospike, auto-restart on reboot
- DEPLOY-02: HTTPS with valid cert (Caddy auto-TLS or Let's Encrypt via nginx)
- DEPLOY-03: WebSocket upgrade works over HTTPS from browser to EC2
- DEPLOY-04: Vercel frontend deployed and `vercel.json` rewrites route `/api/*` to EC2
- DEPLOY-05: Full demo arc works end-to-end from the Vercel URL — login, both attacks, self-improvement, Slack delivery
- DEPLOY-06: Aerospike latency panel shows real numbers from EC2 instance

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VERCEL (Frontend)                         │
│  - Serves React static files from frontend/dist             │
│  - Rewrites /api/* → EC2 backend                            │
│  - WebSocket connects directly to EC2 (no proxy)            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTPS (443)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    AWS EC2 Instance                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Caddy (Port 443)                                      │  │
│  │  - Auto HTTPS with Let's Encrypt                     │  │
│  │  - Reverse proxy to FastAPI                          │  │
│  │  - WebSocket upgrade support                         │  │
│  └─────────────────────┬─────────────────────────────────┘  │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐  │
│  │ FastAPI Container (Port 8000)                         │  │
│  │  - Sentinel backend                                   │  │
│  │  - Serves API endpoints                               │  │
│  │  - WebSocket server                                   │  │
│  │  - Serves static frontend (fallback)                  │  │
│  └─────────────────────┬─────────────────────────────────┘  │
│                        │                                     │
│  ┌─────────────────────▼─────────────────────────────────┐  │
│  │ Aerospike Container (Port 3000)                       │  │
│  │  - Episode storage                                    │  │
│  │  - Verdict boards                                     │  │
│  │  - Generated rules                                    │  │
│  │  - Trust baselines                                    │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Step-by-Step Deployment

### 1. EC2 Instance Setup

**Launch EC2 Instance:**
- AMI: Amazon Linux 2023
- Instance Type: t3.medium (2 vCPU, 4 GB RAM)
- Region: us-east-1 (or your preferred region)
- Storage: 20 GB gp3
- Security Group:
  - Port 443 (HTTPS) - 0.0.0.0/0
  - Port 80 (HTTP) - 0.0.0.0/0 (for Let's Encrypt challenge)
  - Port 22 (SSH) - Your IP only
  - Port 3000 (Aerospike) - Internal only (not exposed)

**Allocate Elastic IP:**
```bash
# In AWS Console: EC2 → Elastic IPs → Allocate
# Associate with your instance
```

**Connect to Instance:**
```bash
ssh -i your-key.pem ec2-user@YOUR_ELASTIC_IP
```

### 2. Clone Repository and Configure

```bash
# Install git
sudo yum install -y git

# Clone repository
git clone https://github.com/YOUR_USERNAME/sentinel.git
cd sentinel

# Create .env from template
cp .env.example .env

# Edit .env with your secrets
nano .env
```

**Required .env values:**
```bash
ANTHROPIC_API_KEY=sk-ant-your-actual-key
AEROSPIKE_HOST=aerospike
AEROSPIKE_PORT=3000
AEROSPIKE_NAMESPACE=sentinel
VITE_AUTH0_DOMAIN=dev-ofumehudzqxsxkzh.us.auth0.com
VITE_AUTH0_CLIENT_ID=LvVkv13yfh3f9RytnH2OcownWd67k21E
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
PUBLIC_HOST=https://YOUR_ELASTIC_IP.nip.io
```

### 3. Run Deployment Script

```bash
# Make script executable (if not already)
chmod +x scripts/deploy-ec2.sh

# Run deployment
./scripts/deploy-ec2.sh
```

**What the script does:**
1. Installs Docker and Docker Compose
2. Validates environment variables
3. Detects EC2 public IP
4. Updates Caddyfile with domain (using nip.io for free DNS)
5. Builds Docker images
6. Starts services with docker-compose.prod.yml
7. Waits for health check
8. Displays deployment info and next steps

### 4. Verify Backend Deployment

```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Test health endpoint
curl https://YOUR_ELASTIC_IP.nip.io/health

# Expected response:
# {"status":"ok","aerospike":true}

# Test WebSocket (requires wscat)
npm install -g wscat
wscat -c wss://YOUR_ELASTIC_IP.nip.io/ws
```

### 5. Configure Vercel

**Update vercel.json:**
```json
{
  "buildCommand": "cd frontend && npm run build",
  "outputDirectory": "frontend/dist",
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://YOUR_ELASTIC_IP.nip.io/api/:path*"
    },
    {
      "source": "/health",
      "destination": "https://YOUR_ELASTIC_IP.nip.io/health"
    }
  ]
}
```

**Set Vercel Environment Variables:**

In Vercel Dashboard → Project → Settings → Environment Variables:

```
VITE_API_URL=https://YOUR_ELASTIC_IP.nip.io
VITE_WS_URL=wss://YOUR_ELASTIC_IP.nip.io/ws
VITE_AUTH0_DOMAIN=dev-ofumehudzqxsxkzh.us.auth0.com
VITE_AUTH0_CLIENT_ID=LvVkv13yfh3f9RytnH2OcownWd67k21E
```

**Deploy to Vercel:**
```bash
# Install Vercel CLI if needed
npm install -g vercel

# Deploy
vercel --prod
```

### 6. Update Auth0 Configuration

In Auth0 Dashboard → Applications → Your App → Settings:

**Allowed Callback URLs:**
```
https://your-vercel-app.vercel.app/callback,
http://localhost:5173/callback
```

**Allowed Logout URLs:**
```
https://your-vercel-app.vercel.app,
http://localhost:5173
```

**Allowed Web Origins:**
```
https://your-vercel-app.vercel.app,
http://localhost:5173
```

### 7. End-to-End Verification

**Test from Vercel URL:**

1. Navigate to `https://your-vercel-app.vercel.app`
2. Click "Login with Auth0"
3. Authenticate
4. Run Attack Scenario 1 (Hidden Text in Invoice)
   - Should block with forensic scan showing hidden text
   - Should generate Rule #001
5. Run Attack Scenario 2 (Agent Identity Spoofing)
   - Should block with Generated Rule #001
   - Should show rule attribution
6. Check Slack for report delivery
7. Verify Aerospike latency panel shows real numbers

**Verification Checklist:**

- [ ] HTTPS works (no certificate warnings)
- [ ] WebSocket connects successfully
- [ ] Auth0 login works
- [ ] Attack 1 blocks and generates rule
- [ ] Attack 2 blocks with generated rule
- [ ] Investigation tree animates correctly
- [ ] Verdict board shows mismatches
- [ ] Forensic scan displays side-by-side
- [ ] Generated rule source visible
- [ ] Slack report delivered
- [ ] Aerospike latency < 10ms
- [ ] No console errors in browser

### 8. Auto-Restart on Reboot

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

# Enable service
sudo systemctl enable sentinel.service

# Test reboot
sudo reboot

# After reboot, verify services are running
docker-compose -f docker-compose.prod.yml ps
```

## Troubleshooting

### Backend not responding

```bash
# Check container status
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs sentinel
docker-compose -f docker-compose.prod.yml logs aerospike
docker-compose -f docker-compose.prod.yml logs caddy

# Restart services
docker-compose -f docker-compose.prod.yml restart
```

### Aerospike connection issues

```bash
# Check Aerospike health
docker-compose -f docker-compose.prod.yml exec aerospike asinfo -v status

# Check network connectivity
docker-compose -f docker-compose.prod.yml exec sentinel ping aerospike
```

### HTTPS certificate issues

```bash
# Check Caddy logs
docker-compose -f docker-compose.prod.yml logs caddy

# Verify domain resolves
nslookup YOUR_ELASTIC_IP.nip.io

# Test HTTP (should redirect to HTTPS)
curl -I http://YOUR_ELASTIC_IP.nip.io
```

### WebSocket connection fails

```bash
# Check if WebSocket upgrade is working
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: test" \
  https://YOUR_ELASTIC_IP.nip.io/ws
```

### Frontend can't reach backend

1. Check Vercel deployment logs
2. Verify environment variables in Vercel dashboard
3. Test API endpoint directly: `curl https://YOUR_ELASTIC_IP.nip.io/health`
4. Check browser console for CORS errors
5. Verify vercel.json rewrites are correct

## Maintenance

**View logs:**
```bash
docker-compose -f docker-compose.prod.yml logs -f
```

**Restart services:**
```bash
docker-compose -f docker-compose.prod.yml restart
```

**Update deployment:**
```bash
git pull
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

**Backup Aerospike data:**
```bash
docker-compose -f docker-compose.prod.yml exec aerospike \
  asbackup --namespace sentinel --directory /opt/aerospike/data/backup
```

**Monitor resource usage:**
```bash
docker stats
```

## Cost Estimate

- EC2 t3.medium: ~$30/month
- Elastic IP: Free (when associated)
- Data transfer: ~$1-5/month (demo usage)
- Vercel: Free tier (hobby)
- Total: ~$35/month

## Security Considerations

1. Keep security group restricted (only 443, 80, 22)
2. Use Elastic IP (not public DNS that changes)
3. Rotate Anthropic API key regularly
4. Monitor CloudWatch logs for suspicious activity
5. Keep Docker images updated
6. Use secrets manager for production (not .env)

## Success Criteria

✅ All DEPLOY-01 through DEPLOY-06 requirements met
✅ Full demo arc works from Vercel URL
✅ Services auto-restart on reboot
✅ HTTPS with valid certificate
✅ WebSocket works over HTTPS
✅ Aerospike latency < 10ms
✅ No errors in production logs
