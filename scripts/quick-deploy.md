# Sentinel — Quick Deployment Reference

## 🚀 Deploy in 10 Minutes

### Step 1: Launch EC2 (2 min)
```
AWS Console → EC2 → Launch Instance
- AMI: Amazon Linux 2023
- Type: t3.medium
- Security: 443, 80, 22
- Storage: 20 GB
→ Allocate Elastic IP → Associate
```

### Step 2: Initial Setup (3 min)
```bash
ssh -i key.pem ec2-user@YOUR_ELASTIC_IP
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/sentinel/main/scripts/setup-ec2-instance.sh | bash
exit
ssh -i key.pem ec2-user@YOUR_ELASTIC_IP
```

### Step 3: Clone & Configure (2 min)
```bash
git clone https://github.com/YOUR_USERNAME/sentinel.git
cd sentinel
cp .env.example .env
nano .env  # Add ANTHROPIC_API_KEY and other secrets
```

### Step 4: Deploy Backend (2 min)
```bash
./scripts/deploy-ec2.sh
# Script auto-configures domain, builds, and starts services
```

### Step 5: Deploy Frontend (1 min)
```bash
# Update vercel.json with your EC2 domain
sed -i 's/YOUR_EC2_DOMAIN/YOUR_ELASTIC_IP.nip.io/g' vercel.json

# Deploy to Vercel
vercel --prod

# Or use Vercel dashboard:
# 1. Import repo
# 2. Set env vars (VITE_API_URL, VITE_WS_URL, VITE_AUTH0_*)
# 3. Deploy
```

### Step 6: Update Auth0
```
Auth0 Dashboard → Your App → Settings
Add Vercel URL to:
- Allowed Callback URLs
- Allowed Logout URLs  
- Allowed Web Origins
```

### Step 7: Test
```
1. Open https://your-app.vercel.app
2. Login
3. Run Attack 1 → Should block + generate rule
4. Run Attack 2 → Should block with generated rule
5. Check Slack for report
```

## 🔍 Quick Checks

```bash
# Backend health
curl https://YOUR_ELASTIC_IP.nip.io/health

# WebSocket
wscat -c wss://YOUR_ELASTIC_IP.nip.io/ws

# Service status
docker-compose -f docker-compose.prod.yml ps

# Logs
docker-compose -f docker-compose.prod.yml logs -f
```

## 🛠️ Common Fixes

**Backend not responding:**
```bash
docker-compose -f docker-compose.prod.yml restart
```

**HTTPS issues:**
```bash
docker-compose -f docker-compose.prod.yml logs caddy
```

**Aerospike connection:**
```bash
docker-compose -f docker-compose.prod.yml exec aerospike asinfo -v status
```

**Frontend can't reach backend:**
- Check Vercel env vars
- Verify vercel.json rewrites
- Test backend directly: `curl https://YOUR_ELASTIC_IP.nip.io/health`

## 📋 Deployment Checklist

- [ ] EC2 instance launched with Elastic IP
- [ ] Security group allows 443, 80, 22
- [ ] Docker and Docker Compose installed
- [ ] Repository cloned
- [ ] .env configured with all secrets
- [ ] Backend deployed and healthy
- [ ] HTTPS certificate valid
- [ ] WebSocket connects
- [ ] vercel.json updated with EC2 domain
- [ ] Vercel env vars configured
- [ ] Frontend deployed to Vercel
- [ ] Auth0 URLs updated
- [ ] End-to-end test passed
- [ ] Auto-restart on reboot configured

## 🎯 Success Criteria

✅ `curl https://YOUR_DOMAIN/health` returns `{"status":"ok","aerospike":true}`
✅ WebSocket connects from browser
✅ Auth0 login works
✅ Attack 1 blocks and generates rule
✅ Attack 2 blocks with generated rule
✅ Slack report delivered
✅ Aerospike latency < 10ms
✅ No console errors

## 💰 Cost

- EC2 t3.medium: ~$30/month
- Elastic IP: Free
- Data transfer: ~$5/month
- Vercel: Free tier
- **Total: ~$35/month**

## 📞 Support

**View logs:**
```bash
docker-compose -f docker-compose.prod.yml logs -f
```

**Restart:**
```bash
docker-compose -f docker-compose.prod.yml restart
```

**Update:**
```bash
git pull
docker-compose -f docker-compose.prod.yml up -d --build
```

---

**For detailed instructions, see DEPLOYMENT.md**
