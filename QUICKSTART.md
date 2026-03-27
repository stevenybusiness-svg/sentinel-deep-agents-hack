# Sentinel — Quick Start Guide

Get Sentinel running in 10 minutes.

## Local Development

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/sentinel.git
cd sentinel

# 2. Create environment file
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Start backend + Aerospike
docker-compose up

# 4. Start frontend (new terminal)
cd frontend
npm install
npm run dev

# 5. Open browser
open http://localhost:5173
```

## Production Deployment (AWS + Vercel)

### Prerequisites
- AWS account
- Vercel account
- Anthropic API key
- Auth0 credentials (already configured)
- Slack webhook (already configured)

### Deploy Backend to EC2

```bash
# 1. Launch EC2 instance
#    - t3.medium, Amazon Linux 2023
#    - Security: 443, 80, 22
#    - Allocate Elastic IP

# 2. SSH into instance
ssh -i your-key.pem ec2-user@YOUR_ELASTIC_IP

# 3. Run setup
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/sentinel/main/scripts/setup-ec2-instance.sh | bash
exit
ssh -i your-key.pem ec2-user@YOUR_ELASTIC_IP

# 4. Clone and configure
git clone https://github.com/YOUR_USERNAME/sentinel.git
cd sentinel
cp .env.example .env
nano .env  # Add ANTHROPIC_API_KEY

# 5. Deploy
./scripts/deploy-ec2.sh

# 6. Verify
./scripts/verify-deployment.sh YOUR_ELASTIC_IP.nip.io
```

### Deploy Frontend to Vercel

```bash
# Run locally
./scripts/deploy-vercel.sh YOUR_ELASTIC_IP.nip.io

# Or manually:
# 1. Update vercel.json with EC2 domain
# 2. Push to GitHub
# 3. Import to Vercel
# 4. Set env vars (VITE_API_URL, VITE_WS_URL, VITE_AUTH0_*)
# 5. Deploy
```

### Update Auth0

```
Auth0 Dashboard → Your App → Settings
Add Vercel URL to:
- Allowed Callback URLs
- Allowed Logout URLs
- Allowed Web Origins
```

### Test

```
1. Open https://your-app.vercel.app
2. Login with Auth0
3. Run Attack 1 → Should block + generate rule
4. Run Attack 2 → Should block with generated rule
5. Check Slack for report
```

## Architecture

```
Browser → Vercel (Frontend) → EC2 (Backend) → Aerospike (Database)
                               ↓
                            Caddy (HTTPS)
```

## Key Endpoints

- **Health:** `https://YOUR_DOMAIN/health`
- **WebSocket:** `wss://YOUR_DOMAIN/ws`
- **API:** `https://YOUR_DOMAIN/api/*`

## Common Commands

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart
docker-compose -f docker-compose.prod.yml restart

# Stop
docker-compose -f docker-compose.prod.yml down

# Update
git pull && docker-compose -f docker-compose.prod.yml up -d --build
```

## Troubleshooting

**Backend not responding:**
```bash
docker-compose -f docker-compose.prod.yml logs sentinel
docker-compose -f docker-compose.prod.yml restart
```

**WebSocket fails:**
```bash
wscat -c wss://YOUR_DOMAIN/ws
docker-compose -f docker-compose.prod.yml logs caddy
```

**Frontend can't reach backend:**
- Check Vercel env vars
- Verify vercel.json rewrites
- Test: `curl https://YOUR_DOMAIN/health`

## Documentation

- **DEPLOYMENT.md** - Complete deployment guide
- **scripts/README.md** - Script documentation
- **scripts/quick-deploy.md** - Quick reference
- **.planning/phases/09-aws-deployment/** - Detailed plans

## Cost

- EC2 t3.medium: ~$30/month
- Vercel: Free tier
- **Total: ~$35/month**

## Support

For issues:
1. Run `./scripts/verify-deployment.sh YOUR_DOMAIN`
2. Check logs: `docker-compose -f docker-compose.prod.yml logs`
3. Review DEPLOYMENT.md troubleshooting section

---

**Ready to deploy? See DEPLOYMENT.md for detailed instructions.**
