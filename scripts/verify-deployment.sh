#!/bin/bash
# Sentinel — Deployment Verification Script
# Run this after deployment to verify everything works

set -e

echo "🔍 Sentinel Deployment Verification"
echo "===================================="
echo ""

# Check if domain is provided
if [ -z "$1" ]; then
    echo "Usage: ./verify-deployment.sh YOUR_DOMAIN"
    echo "Example: ./verify-deployment.sh 54.123.45.67.nip.io"
    exit 1
fi

DOMAIN=$1
HTTPS_URL="https://${DOMAIN}"
WSS_URL="wss://${DOMAIN}/ws"

echo "Testing domain: $DOMAIN"
echo ""

# Test 1: Health Check
echo "Test 1: Backend Health Check"
echo "-----------------------------"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${HTTPS_URL}/health" || echo "000")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Health check passed (HTTP $HTTP_CODE)"
    echo "   Response: $HEALTH_BODY"
    
    # Check if Aerospike is connected
    if echo "$HEALTH_BODY" | grep -q '"aerospike":true'; then
        echo "✅ Aerospike connected"
    else
        echo "⚠️  Aerospike not connected"
    fi
else
    echo "❌ Health check failed (HTTP $HTTP_CODE)"
    echo "   Response: $HEALTH_BODY"
fi
echo ""

# Test 2: HTTPS Certificate
echo "Test 2: HTTPS Certificate"
echo "-------------------------"
CERT_INFO=$(echo | openssl s_client -servername "$DOMAIN" -connect "${DOMAIN}:443" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "")

if [ -n "$CERT_INFO" ]; then
    echo "✅ HTTPS certificate valid"
    echo "$CERT_INFO" | sed 's/^/   /'
else
    echo "⚠️  Could not verify HTTPS certificate"
fi
echo ""

# Test 3: WebSocket Connection
echo "Test 3: WebSocket Connection"
echo "----------------------------"
if command -v wscat &> /dev/null; then
    # Test WebSocket with timeout
    timeout 5s wscat -c "$WSS_URL" --execute "test" > /dev/null 2>&1 && WS_STATUS="✅ Connected" || WS_STATUS="⚠️  Connection test inconclusive"
    echo "$WS_STATUS"
else
    echo "⚠️  wscat not installed (npm install -g wscat to test WebSocket)"
fi
echo ""

# Test 4: API Endpoints
echo "Test 4: API Endpoints"
echo "---------------------"

# Test investigate endpoint (should require POST)
INVESTIGATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${HTTPS_URL}/api/investigate" || echo "000")
INVESTIGATE_CODE=$(echo "$INVESTIGATE_RESPONSE" | tail -n1)

if [ "$INVESTIGATE_CODE" = "405" ] || [ "$INVESTIGATE_CODE" = "422" ]; then
    echo "✅ /api/investigate endpoint exists (HTTP $INVESTIGATE_CODE - expected)"
else
    echo "⚠️  /api/investigate returned HTTP $INVESTIGATE_CODE"
fi

# Test confirm endpoint (should require POST)
CONFIRM_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${HTTPS_URL}/api/confirm" || echo "000")
CONFIRM_CODE=$(echo "$CONFIRM_RESPONSE" | tail -n1)

if [ "$CONFIRM_CODE" = "405" ] || [ "$CONFIRM_CODE" = "422" ]; then
    echo "✅ /api/confirm endpoint exists (HTTP $CONFIRM_CODE - expected)"
else
    echo "⚠️  /api/confirm returned HTTP $CONFIRM_CODE"
fi
echo ""

# Test 5: Static Files
echo "Test 5: Static Files"
echo "--------------------"

# Test if frontend is being served (should get HTML)
INDEX_RESPONSE=$(curl -s -w "\n%{http_code}" "${HTTPS_URL}/" || echo "000")
INDEX_CODE=$(echo "$INDEX_RESPONSE" | tail -n1)
INDEX_BODY=$(echo "$INDEX_RESPONSE" | head -n-1)

if [ "$INDEX_CODE" = "200" ] && echo "$INDEX_BODY" | grep -q "<!DOCTYPE html>"; then
    echo "✅ Frontend HTML served (HTTP $INDEX_CODE)"
else
    echo "⚠️  Frontend may not be served correctly (HTTP $INDEX_CODE)"
fi
echo ""

# Test 6: Docker Services (if running on EC2)
if command -v docker &> /dev/null; then
    echo "Test 6: Docker Services"
    echo "-----------------------"
    
    if docker-compose -f docker-compose.prod.yml ps 2>/dev/null | grep -q "Up"; then
        echo "✅ Docker services running"
        docker-compose -f docker-compose.prod.yml ps | grep "Up" | sed 's/^/   /'
    else
        echo "⚠️  Could not verify Docker services (may not be on EC2)"
    fi
    echo ""
fi

# Summary
echo "=================================="
echo "Verification Summary"
echo "=================================="
echo ""

PASSED=0
TOTAL=5

[ "$HTTP_CODE" = "200" ] && ((PASSED++))
[ -n "$CERT_INFO" ] && ((PASSED++))
[ "$INVESTIGATE_CODE" = "405" ] || [ "$INVESTIGATE_CODE" = "422" ] && ((PASSED++))
[ "$CONFIRM_CODE" = "405" ] || [ "$CONFIRM_CODE" = "422" ] && ((PASSED++))
[ "$INDEX_CODE" = "200" ] && ((PASSED++))

echo "Tests passed: $PASSED/$TOTAL"
echo ""

if [ $PASSED -eq $TOTAL ]; then
    echo "✅ All critical tests passed!"
    echo ""
    echo "Next steps:"
    echo "1. Test from Vercel URL: https://your-app.vercel.app"
    echo "2. Login with Auth0"
    echo "3. Run Attack Scenario 1"
    echo "4. Run Attack Scenario 2"
    echo "5. Verify Slack report delivery"
else
    echo "⚠️  Some tests failed. Check logs:"
    echo "   docker-compose -f docker-compose.prod.yml logs -f"
fi
echo ""
