# Sentinel — Demo Day Runbook

## Pre-Demo Checklist (1 hour before)

### System Status
- [ ] EC2 instance running
- [ ] Health check passes: `curl https://YOUR_DOMAIN/health`
- [ ] WebSocket connects: `wscat -c wss://YOUR_DOMAIN/ws`
- [ ] Vercel deployment live
- [ ] Auth0 login tested
- [ ] Slack webhook tested

### Browser Setup
- [ ] Open Vercel URL in Chrome/Firefox
- [ ] Login to Auth0
- [ ] Verify dashboard loads
- [ ] Open browser DevTools (F12)
- [ ] Check WebSocket connection in Network tab
- [ ] No console errors

### Backup Plan
- [ ] Local deployment tested: `docker-compose up`
- [ ] Local frontend tested: `cd frontend && npm run dev`
- [ ] Backup laptop ready
- [ ] Mobile hotspot available (if WiFi fails)

### Demo Environment
- [ ] Screen sharing tested
- [ ] Audio tested
- [ ] Browser zoom at 100%
- [ ] Close unnecessary tabs
- [ ] Disable notifications
- [ ] Full screen mode ready

## Demo Script (3 minutes)

### Opening (15 seconds)

**Say:**
> "We're going to show you two attacks on an autonomous payment agent. The first one hides malicious instructions inside an invoice image — invisible to humans, but the agent reads it. The second is completely different: a malicious agent impersonating a trusted one inside the pipeline, sending a fake clearance message. Our system catches the second attack using a rule it wrote itself from the first, 90 seconds earlier."

**Do:**
- Show the intro screen (clean vs forensic invoice side-by-side)
- Point out the hidden text is invisible to humans

### Attack 1: Hidden Text (60 seconds)

**Say:**
> "This invoice looks clean. But there's white text on the white background telling the agent to redirect the payment."

**Do:**
1. Click "Run Attack 1: Hidden Text in Invoice"
2. Watch investigation tree animate
3. Point out sub-agents running in parallel
4. Show verdict board with mismatches
5. Show forensic scan with hidden text highlighted
6. Show Gate decision: NO-GO
7. Point out rule generation starting

**Key moment:**
> "The system just wrote a rule. Not a signature — a behavioral pattern. Let's see if it generalizes."

### Attack 2: Agent Spoofing (60 seconds)

**Say:**
> "Now a completely different attack. No document. A fake agent is impersonating our KYC system, sending a fraudulent clearance message."

**Do:**
1. Click "Run Attack 2: Agent Identity Spoofing"
2. Watch investigation tree
3. Show verdict board with different mismatches
4. Point to Generated Rule #001 node
5. Show Gate decision: NO-GO
6. Show attribution: "Blocked by Generated Rule #001"

**Key moment:**
> "Same rule. Different attack. The system learned to detect when an agent is lying, regardless of how the lie got there."

### Closing (30 seconds)

**Say:**
> "The investigation tree has one more node than when we started. That node wasn't programmed — it was written by the system after watching one attack. The system is harder to fool now than it was three minutes ago, and nobody pushed an update."

**Do:**
- Show rule source code panel
- Show Slack report (if delivered)
- Show Aerospike latency (< 10ms)

### Q&A Prep

**"Isn't this just calling Claude to write code?"**
> "Yes — Opus writes the Python function. But the function didn't exist before the incident. It's stored, versioned, attributed to the episode that produced it, and runs on every future transaction without any LLM calls. You can read it on the dashboard right now. The contribution isn't the prompt — it's the architecture that takes that output and makes it an operational detection capability."

**"How do you prevent false positives?"**
> "The generated rule operates on the verdict board — structured field comparisons between what the payment agent claimed and what independent investigators found. It returns False on clean transactions where all claims match. We test every generated function against clean baselines before deployment."

**"What if the generated rule is wrong?"**
> "The operator confirms every incident before rule generation. If a generated rule produces false positives in testing, we regenerate with a different prompt variant. The Safety Gate also runs hardcoded rules first — generated rules are additive, not replacements."

**"Does this work for other domains besides payments?"**
> "Yes. The architecture is domain-agnostic. Any autonomous agent that makes claims about the world can be supervised by independent investigators checking those claims. Payments are the demo because they're irreversible and high-stakes — the properties that make supervision critical."

**"How does this compare to existing guardrails?"**
> "Static guardrails catch attacks you imagined in advance. Sentinel catches attacks by checking if the agent's story holds up under independent scrutiny. That's a behavioral check, not a signature. It generalizes to attack vectors you didn't anticipate."

## Emergency Procedures

### Demo Fails to Load

1. Check EC2 health: `curl https://YOUR_DOMAIN/health`
2. Check Vercel deployment status
3. Check browser console for errors
4. Fallback: Switch to local deployment
   - `docker-compose up` (backend)
   - `cd frontend && npm run dev` (frontend)
   - Update demo URL to localhost:5173

### WebSocket Disconnects

1. Check EC2 logs: `docker-compose -f docker-compose.prod.yml logs caddy`
2. Refresh browser
3. Check browser DevTools Network tab
4. Fallback: Show pre-recorded video

### Attack Scenario Fails

1. Check backend logs: `docker-compose -f docker-compose.prod.yml logs sentinel`
2. Verify Anthropic API key valid
3. Check Aerospike connection
4. Fallback: Show screenshots of expected behavior

### Rule Generation Fails

1. Check Supervisor logs
2. Verify Opus 4.6 API access
3. Show rule source from previous run
4. Explain the generation process

## Timing

- Opening: 15 seconds
- Attack 1: 60 seconds
- Transition: 15 seconds
- Attack 2: 60 seconds
- Closing: 30 seconds
- **Total: 3 minutes**
- **Buffer: 15 seconds**

## What to Emphasize

1. **Parallel investigation** - Sub-agents run simultaneously
2. **Independent verification** - Each agent checks independently
3. **Behavioral pattern** - Not signature matching
4. **Generalization** - Different attack, same rule
5. **Transparency** - Full rule source visible
6. **Learning** - System improves without updates

## What NOT to Say

- "AI-powered" (overused)
- "Revolutionary" (hyperbole)
- "Best-in-class" (unverifiable)
- "Unbreakable" (false claim)
- "Production-ready" (it's a demo)

## Post-Demo

- [ ] Thank judges
- [ ] Offer to show rule source code
- [ ] Offer to show Aerospike latency
- [ ] Offer to show Slack report
- [ ] Answer questions
- [ ] Provide GitHub link
- [ ] Provide demo URL for judges to test

## Contact Info

- **GitHub:** YOUR_USERNAME/sentinel
- **Demo URL:** https://your-app.vercel.app
- **Email:** YOUR_EMAIL

## Backup Materials

- Screenshots of successful runs
- Pre-recorded video (if live demo fails)
- Slide deck with architecture diagrams
- Rule source code examples
- Verdict board examples

---

**Good luck! 🚀**
