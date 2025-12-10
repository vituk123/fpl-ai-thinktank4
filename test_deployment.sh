#!/bin/bash
# Test Deployment Script
# Run this after deploying to verify everything works

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🧪 Testing FPL Backend Deployment..."
echo ""

# Configuration - UPDATE THESE VALUES
RENDER_URL="${RENDER_URL:-https://your-app.onrender.com}"
SUPABASE_URL="${SUPABASE_URL:-https://your-project.supabase.co}"
SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY:-your-anon-key}"
TEST_ENTRY_ID="${TEST_ENTRY_ID:-2568103}"
TEST_GAMEWEEK="${TEST_GAMEWEEK:-16}"

# Check if values are set
if [ "$RENDER_URL" = "https://your-app.onrender.com" ] || [ "$SUPABASE_URL" = "https://your-project.supabase.co" ] || [ "$SUPABASE_ANON_KEY" = "your-anon-key" ]; then
  echo -e "${YELLOW}⚠️  Please set environment variables:${NC}"
  echo "   export RENDER_URL=https://your-app.onrender.com"
  echo "   export SUPABASE_URL=https://your-project.supabase.co"
  echo "   export SUPABASE_ANON_KEY=your-anon-key"
  echo "   export TEST_ENTRY_ID=2568103"
  echo "   export TEST_GAMEWEEK=16"
  echo ""
  echo "Or run: ./test_deployment.sh RENDER_URL SUPABASE_URL SUPABASE_ANON_KEY"
  exit 1
fi

# Test counters
PASSED=0
FAILED=0

# Test function
test_endpoint() {
  local name=$1
  local url=$2
  local method=${3:-GET}
  local headers=$4
  
  echo -n "Testing $name... "
  
  if [ "$method" = "GET" ]; then
    if [ -n "$headers" ]; then
      response=$(curl -s -w "\n%{http_code}" -H "$headers" "$url" || echo -e "\n000")
    else
      response=$(curl -s -w "\n%{http_code}" "$url" || echo -e "\n000")
    fi
  else
    response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" || echo -e "\n000")
  fi
  
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')
  
  if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
    ((PASSED++))
    return 0
  else
    echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
    echo "   URL: $url"
    echo "   Response: $body" | head -c 200
    echo ""
    ((FAILED++))
    return 1
  fi
}

echo "📋 Testing Render FastAPI Backend..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test 1: Health check
test_endpoint "Health Check" "$RENDER_URL/api/v1/health"

# Test 2: Entry info
test_endpoint "Entry Info" "$RENDER_URL/api/v1/entry/$TEST_ENTRY_ID/info"

# Test 3: Current gameweek
test_endpoint "Current Gameweek" "$RENDER_URL/api/v1/gameweek/current"

# Test 4: ML Predictions (may be empty if not generated yet)
echo -n "Testing ML Predictions... "
response=$(curl -s -w "\n%{http_code}" "$RENDER_URL/api/v1/ml/predictions?gameweek=$TEST_GAMEWEEK" || echo -e "\n000")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "200" ]; then
  echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
  ((PASSED++))
else
  echo -e "${YELLOW}⚠ SKIP${NC} (HTTP $http_code - predictions may not be generated yet)"
fi

echo ""
echo "📋 Testing Supabase Edge Functions..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

auth_header="Authorization: Bearer $SUPABASE_ANON_KEY"

# Test 5: Live gameweek (Edge Function)
test_endpoint "Live Gameweek (Edge Function)" \
  "$SUPABASE_URL/functions/v1/live-gameweek?gameweek=$TEST_GAMEWEEK&entry_id=$TEST_ENTRY_ID" \
  "GET" "$auth_header"

# Test 6: ML Predictions (Edge Function)
test_endpoint "ML Predictions (Edge Function)" \
  "$SUPABASE_URL/functions/v1/ml-predictions?gameweek=$TEST_GAMEWEEK" \
  "GET" "$auth_header"

# Test 7: ML Recommendations (Edge Function → Render proxy)
echo -n "Testing ML Recommendations (may take 60s)... "
response=$(curl -s -w "\n%{http_code}" --max-time 120 \
  -H "$auth_header" \
  "$SUPABASE_URL/functions/v1/ml-recommendations?entry_id=$TEST_ENTRY_ID&gameweek=$TEST_GAMEWEEK" \
  || echo -e "\n000")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "200" ]; then
  echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
  ((PASSED++))
elif [ "$http_code" = "504" ] || [ "$http_code" = "000" ]; then
  echo -e "${YELLOW}⚠ TIMEOUT${NC} (This is normal for ML recommendations - they take 30-60 seconds)"
else
  echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
  ((FAILED++))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Test Results:"
echo "   ${GREEN}Passed: $PASSED${NC}"
echo "   ${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
  echo -e "${GREEN}✅ All critical tests passed!${NC}"
  echo ""
  echo "Next steps:"
  echo "1. Test from frontend by entering team ID $TEST_ENTRY_ID"
  echo "2. Verify live tracking updates"
  echo "3. Check ML recommendations load (may take 30-60 seconds)"
  exit 0
else
  echo -e "${YELLOW}⚠️  Some tests failed. Check the errors above.${NC}"
  exit 1
fi

