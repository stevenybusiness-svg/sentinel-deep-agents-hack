#!/bin/bash
# Sentinel — Pre-Flight Check
# Run this before deployment to catch issues early

echo "✈️  Sentinel Pre-Flight Check"
echo "=============================="
echo ""

ERRORS=0
WARNINGS=0

# Check 1: Required files exist
echo "📁 Checking required files..."
REQUIRED_FILES=(
    "docker-compose.prod.yml"
    "Dockerfile"
    "Caddyfile"
    "vercel.json"
    ".env.example"
    "requirements.txt"
    "frontend/package.json"
    "sentinel/api/main.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file MISSING"
        ((ERRORS++))
    fi
done
echo ""

# Check 2: .env file exists
echo "🔐 Checking environment configuration..."
if [ -f ".env" ]; then
    echo "   ✅ .env file exists"
    
    # Check required variables
    REQUIRED_VARS=(
        "ANTHROPIC_API_KEY"
        "AEROSPIKE_NAMESPACE"
        "VITE_AUTH0_DOMAIN"
        "VITE_AUTH0_CLIENT_ID"
    )
    
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^${var}=" .env && ! grep -q "^${var}=$" .env && ! grep -q "^${var}=.*your.*here" .env; then
            echo "   ✅ $var configured"
        else
            echo "   ❌ $var missing or invalid"
            ((ERRORS++))
        fi
    done
    
    # Check optional but recommended
    if grep -q "^SLACK_WEBHOOK_URL=https://hooks.slack.com" .env; then
        echo "   ✅ SLACK_WEBHOOK_URL configured"
    else
        echo "   ⚠️  SLACK_WEBHOOK_URL not configured (optional)"
        ((WARNINGS++))
    fi
else
    echo "   ❌ .env file not found"
    echo "   Create it from .env.example: cp .env.example .env"
    ((ERRORS++))
fi
echo ""

# Check 3: Docker configuration
echo "🐳 Checking Docker configuration..."
if command -v docker &> /dev/null; then
    echo "   ✅ Docker installed"
    
    # Check if Docker is running
    if docker ps &> /dev/null; then
        echo "   ✅ Docker daemon running"
    else
        echo "   ❌ Docker daemon not running"
        ((ERRORS++))
    fi
else
    echo "   ⚠️  Docker not installed (will be installed by setup script)"
    ((WARNINGS++))
fi

if command -v docker-compose &> /dev/null; then
    echo "   ✅ Docker Compose installed"
else
    echo "   ⚠️  Docker Compose not installed (will be installed by setup script)"
    ((WARNINGS++))
fi
echo ""

# Check 4: Python dependencies
echo "🐍 Checking Python configuration..."
if [ -f "requirements.txt" ]; then
    echo "   ✅ requirements.txt exists"
    
    # Check for critical dependencies
    CRITICAL_DEPS=("fastapi" "anthropic" "aerospike" "uvicorn")
    for dep in "${CRITICAL_DEPS[@]}"; do
        if grep -q "^${dep}" requirements.txt; then
            echo "   ✅ $dep listed"
        else
            echo "   ❌ $dep missing from requirements.txt"
            ((ERRORS++))
        fi
    done
else
    echo "   ❌ requirements.txt not found"
    ((ERRORS++))
fi
echo ""

# Check 5: Frontend configuration
echo "⚛️  Checking frontend configuration..."
if [ -f "frontend/package.json" ]; then
    echo "   ✅ frontend/package.json exists"
    
    # Check for critical dependencies
    if grep -q '"react"' frontend/package.json; then
        echo "   ✅ React dependency"
    else
        echo "   ❌ React missing"
        ((ERRORS++))
    fi
    
    if grep -q '"@xyflow/react"' frontend/package.json; then
        echo "   ✅ @xyflow/react dependency"
    else
        echo "   ❌ @xyflow/react missing"
        ((ERRORS++))
    fi
    
    if grep -q '"build"' frontend/package.json; then
        echo "   ✅ Build script defined"
    else
        echo "   ❌ Build script missing"
        ((ERRORS++))
    fi
else
    echo "   ❌ frontend/package.json not found"
    ((ERRORS++))
fi
echo ""

# Check 6: Vercel configuration
echo "🌐 Checking Vercel configuration..."
if [ -f "vercel.json" ]; then
    echo "   ✅ vercel.json exists"
    
    if grep -q "YOUR_EC2_DOMAIN" vercel.json; then
        echo "   ⚠️  vercel.json still has placeholder (update after EC2 deployment)"
        ((WARNINGS++))
    else
        echo "   ✅ vercel.json configured with domain"
    fi
    
    if grep -q '"buildCommand"' vercel.json; then
        echo "   ✅ Build command defined"
    else
        echo "   ❌ Build command missing"
        ((ERRORS++))
    fi
else
    echo "   ❌ vercel.json not found"
    ((ERRORS++))
fi
echo ""

# Check 7: Git status
echo "📦 Checking git status..."
if [ -d ".git" ]; then
    echo "   ✅ Git repository initialized"
    
    # Check for uncommitted changes
    if git diff-index --quiet HEAD -- 2>/dev/null; then
        echo "   ✅ No uncommitted changes"
    else
        echo "   ⚠️  Uncommitted changes detected"
        ((WARNINGS++))
    fi
    
    # Check if remote is configured
    if git remote -v | grep -q "origin"; then
        echo "   ✅ Git remote configured"
    else
        echo "   ⚠️  No git remote configured"
        ((WARNINGS++))
    fi
else
    echo "   ❌ Not a git repository"
    ((ERRORS++))
fi
echo ""

# Summary
echo "=================================="
echo "Pre-Flight Summary"
echo "=================================="
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "✅ All checks passed! Ready for deployment."
    echo ""
    echo "Next steps:"
    echo "1. Launch EC2 instance in AWS Console"
    echo "2. Run: ./scripts/setup-ec2-instance.sh"
    echo "3. Run: ./scripts/deploy-ec2.sh"
    echo "4. Run: ./scripts/deploy-vercel.sh YOUR_DOMAIN"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo "⚠️  $WARNINGS warning(s) found, but deployment can proceed"
    echo ""
    echo "Review warnings above and proceed with deployment if acceptable."
    exit 0
else
    echo "❌ $ERRORS error(s) and $WARNINGS warning(s) found"
    echo ""
    echo "Please fix errors before deploying."
    exit 1
fi
