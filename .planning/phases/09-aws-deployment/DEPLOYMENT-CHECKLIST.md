# Phase 9: AWS Deployment Checklist

## Pre-Deployment

- [ ] AWS account with EC2 access
- [ ] Vercel account
- [ ] Anthropic API key ready
- [ ] Auth0 credentials ready
- [ ] Slack webhook URL ready
- [ ] SSH key pair for EC2
- [ ] Git repository accessible

## EC2 Setup

- [ ] Launch EC2 instance (t3.medium, Amazon Linux 2023)
- [ ] Configure security group (443, 80, 22)
- [ ] Allocate and associate Elastic IP
- [ ] Note Elastic IP address: `___________________`
- [ ] SSH connection works: `ssh -i key.pem ec2-user@ELASTIC_IP`

## Initial Configuration

- [ ] Run setup script: `./scripts/setup-ec2-instance.sh`
- [ ] Log out and back in for Docker group
- [ ] Clone repository: `git clone ...`
- [ ] Create .env from .env.example
- [ ] Add ANTHROPIC_API_KEY to .env
- [ ] Add Auth0 credentials to .env
- [ ] Add Slack webhook to .env
- [ ] Verify .env has all required values

## Backend Deployment

- [ ] Run deployment script: `./scripts/deploy-ec2.sh`
- [ ] Script completes without errors
- [ ] Health check passes: `curl https://DOMAIN/health`
- [ ] Response shows `"status":"ok"`
- [ ] Response shows `"aerospike":true`
- [ ] WebSocket test passes: `wscat -c wss://DOMAIN/ws`
- [ ] Docker services running: `docker-compose -f docker-compose.prod.yml ps`
- [ ] No errors in logs: `docker-compose -f docker-compose.prod.yml logs`

## Frontend Deployment

- [ ] Update vercel.json with EC2 domain
- [ ] Commit changes: `git add vercel.json && git commit`
- [ ] Push to GitHub: `git push`
- [ ] Deploy to Vercel (CLI or Dashboard)
- [ ] Set VITE_API_URL in Vercel
- [ ] Set VITE_WS_URL in Vercel
- [ ] Set VITE_AUTH0_DOMAIN in Vercel
- [ ] Set VITE_AUTH0_CLIENT_ID in Vercel
- [ ] Vercel deployment succeeds
- [ ] Note Vercel URL: `___________________`

## Auth0 Configuration

- [ ] Open Auth0 Dashboard
- [ ] Navigate to Applications → Your App → Settings
- [ ] Add Vercel URL to Allowed Callback URLs
- [ ] Add Vercel URL to Allowed Logout URLs
- [ ] Add Vercel URL to Allowed Web Origins
- [ ] Save changes

## End-to-End Testing

### Basic Connectivity
- [ ] Open Vercel URL in browser
- [ ] No console errors
- [ ] WebSocket connects (check browser DevTools)
- [ ] Auth0 login button visible

### Authentication
- [ ] Click "Login with Auth0"
- [ ] Auth0 login page loads
- [ ] Login succeeds
- [ ] Redirected back to app
- [ ] User info displayed

### Attack Scenario 1 (Hidden Text)
- [ ] Click "Run Attack 1" button
- [ ] Investigation starts
- [ ] Investigation tree displays
- [ ] Sub-agents execute (Risk, Compliance, Forensics)
- [ ] Forensics detects hidden text
- [ ] Verdict board shows mismatches
- [ ] Gate decision: NO-GO
- [ ] Forensic scan panel shows side-by-side images
- [ ] Hidden text highlighted in red
- [ ] Rule generation triggered
- [ ] Generated Rule #001 appears in tree
- [ ] Rule source code visible
- [ ] Qualitative analysis panel populated

### Attack Scenario 2 (Agent Spoofing)
- [ ] Click "Run Attack 2" button
- [ ] Investigation starts
- [ ] Sub-agents execute
- [ ] Compliance detects missing KYC record
- [ ] Verdict board shows mismatches
- [ ] Generated Rule #001 fires
- [ ] Gate decision: NO-GO
- [ ] Attribution shows "Blocked by Generated Rule #001"
- [ ] Rule provenance displayed (from Episode #001)
- [ ] Qualitative analysis shows learning

### Integrations
- [ ] Slack report delivered for Attack 1
- [ ] Slack report delivered for Attack 2
- [ ] Aerospike latency panel shows real numbers
- [ ] Latency < 10ms

### UI/UX
- [ ] Investigation tree animates smoothly
- [ ] Node colors correct (green/red/yellow)
- [ ] Edges animate
- [ ] Rule node has pulse animation
- [ ] Verdict board table readable
- [ ] Forensic images load correctly
- [ ] Rule source code syntax highlighted
- [ ] Decision log updates in real-time
- [ ] Trust score bar animates

## Production Readiness

- [ ] Auto-restart on reboot configured
- [ ] Systemd service enabled
- [ ] Test reboot: `sudo reboot`
- [ ] After reboot, services auto-start
- [ ] Health check passes after reboot
- [ ] Backup strategy documented
- [ ] Monitoring configured (optional)
- [ ] CloudWatch logs enabled (optional)

## Documentation

- [ ] EC2 Elastic IP documented
- [ ] Vercel URL documented
- [ ] Auth0 configuration documented
- [ ] Environment variables documented
- [ ] Deployment commands documented
- [ ] Troubleshooting steps documented

## Performance Verification

- [ ] Backend response time < 500ms
- [ ] WebSocket latency < 100ms
- [ ] Aerospike latency < 10ms
- [ ] Frontend loads in < 3s
- [ ] Investigation completes in < 30s
- [ ] No memory leaks (check `docker stats`)
- [ ] CPU usage reasonable (< 50% idle)

## Security Verification

- [ ] HTTPS certificate valid (no warnings)
- [ ] Security group properly configured
- [ ] SSH restricted to your IP
- [ ] No secrets in git history
- [ ] .env not committed
- [ ] API keys rotated if exposed
- [ ] Aerospike not publicly accessible

## Final Verification

- [ ] Run verification script: `./scripts/verify-deployment.sh DOMAIN`
- [ ] All tests pass
- [ ] Demo rehearsal completed
- [ ] Timing verified (< 3 minutes for full demo)
- [ ] Backup plan if demo fails
- [ ] Fallback to local if needed

## Demo Day Checklist

- [ ] EC2 instance running
- [ ] Vercel deployment live
- [ ] Auth0 working
- [ ] Slack webhook working
- [ ] Test login before demo
- [ ] Clear any test data
- [ ] Reset to clean state
- [ ] Browser tabs prepared
- [ ] Screen sharing tested
- [ ] Audio tested
- [ ] Backup laptop ready
- [ ] Local fallback tested

## Rollback Plan

If deployment fails:
- [ ] Revert vercel.json changes
- [ ] Deploy frontend locally: `cd frontend && npm run dev`
- [ ] Run backend locally: `docker-compose up`
- [ ] Update demo to use localhost
- [ ] Test local setup works

## Success Criteria

✅ All checklist items completed
✅ Full demo arc works end-to-end
✅ Both attacks block correctly
✅ Rule generation and firing works
✅ Slack reports delivered
✅ No errors in production
✅ Performance acceptable
✅ Security verified
✅ Documentation complete

## Notes

**EC2 Elastic IP:** ___________________

**Vercel URL:** ___________________

**Deployment Date:** ___________________

**Deployed By:** ___________________

**Issues Encountered:**
- 
- 
- 

**Resolutions:**
- 
- 
- 

---

**Status:** [ ] Not Started | [ ] In Progress | [ ] Complete | [ ] Verified
