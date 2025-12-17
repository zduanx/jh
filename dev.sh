#!/bin/zsh
# Development shortcuts for Job Hunter (jh) project
# Usage: source dev.sh (or add to your shell profile)

# Color codes for pretty output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
JH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ==============================================================================
# GLOBAL ENVIRONMENT VARIABLE CONFIGURATION
# ==============================================================================
# Parse production values from .env.local files once at script load time
# Format: # <VAR_NAME>_PROD_VALUE=value

# Backend production values
if [ -f "$JH_ROOT/backend/.env.local" ]; then
    BACKEND_GOOGLE_CLIENT_ID_PROD=$(grep "^# GOOGLE_CLIENT_ID_PROD_VALUE=" "$JH_ROOT/backend/.env.local" | cut -d= -f2- | tr -d '\n' | tr -d '\r')
    BACKEND_SECRET_KEY_PROD=$(grep "^# SECRET_KEY_PROD_VALUE=" "$JH_ROOT/backend/.env.local" | cut -d= -f2- | tr -d '\n' | tr -d '\r')
    BACKEND_ALLOWED_EMAILS_PROD=$(grep "^# ALLOWED_EMAILS_PROD_VALUE=" "$JH_ROOT/backend/.env.local" | cut -d= -f2- | tr -d '\n' | tr -d '\r')
    BACKEND_ALLOWED_ORIGINS_PROD=$(grep "^# ALLOWED_ORIGINS_PROD_VALUE=" "$JH_ROOT/backend/.env.local" | cut -d= -f2- | tr -d '\n' | tr -d '\r')
    BACKEND_DATABASE_URL_PROD=$(grep "^# DATABASE_URL_PROD_VALUE=" "$JH_ROOT/backend/.env.local" | cut -d= -f2- | tr -d '\n' | tr -d '\r')
fi

# Frontend production values
if [ -f "$JH_ROOT/frontend/.env.local" ]; then
    FRONTEND_GOOGLE_CLIENT_ID_PROD=$(grep "^# REACT_APP_GOOGLE_CLIENT_ID_PROD_VALUE=" "$JH_ROOT/frontend/.env.local" | cut -d= -f2- | tr -d '\n' | tr -d '\r')
    FRONTEND_API_URL_PROD=$(grep "^# REACT_APP_API_URL_PROD_VALUE=" "$JH_ROOT/frontend/.env.local" | cut -d= -f2- | tr -d '\n' | tr -d '\r')
fi

# Global associative arrays for deployment checks (zsh syntax)
typeset -A BACKEND_CHECK=(
    ["GOOGLE_CLIENT_ID"]="$BACKEND_GOOGLE_CLIENT_ID_PROD"
    ["SECRET_KEY"]="$BACKEND_SECRET_KEY_PROD"
    ["ALLOWED_EMAILS"]="$BACKEND_ALLOWED_EMAILS_PROD"
    ["ALLOWED_ORIGINS"]="$BACKEND_ALLOWED_ORIGINS_PROD"
    ["DATABASE_URL"]="$BACKEND_DATABASE_URL_PROD"
)

typeset -A FRONTEND_CHECK=(
    ["REACT_APP_GOOGLE_CLIENT_ID"]="$FRONTEND_GOOGLE_CLIENT_ID_PROD"
    ["REACT_APP_API_URL"]="$FRONTEND_API_URL_PROD"
)

# Backend shortcuts
jbe() {
    echo -e "${BLUE}Starting backend server...${NC}"
    cd "$JH_ROOT/backend" || return 1
    source venv/bin/activate
    uvicorn main:app --reload --port 8000
}

# Frontend shortcuts
jfe() {
    echo -e "${BLUE}Starting frontend server...${NC}"
    cd "$JH_ROOT/frontend" || return 1
    npm start
}

# Kill processes
jkill-be() {
    echo -e "${YELLOW}Killing backend (port 8000)...${NC}"
    lsof -ti:8000 | xargs kill -9 2>/dev/null && echo -e "${GREEN}✓ Backend stopped${NC}" || echo -e "${RED}No backend process found on port 8000${NC}"
}

jkill-fe() {
    echo -e "${YELLOW}Killing frontend (port 3000)...${NC}"
    lsof -ti:3000 | xargs kill -9 2>/dev/null && echo -e "${GREEN}✓ Frontend stopped${NC}" || echo -e "${RED}No frontend process found on port 3000${NC}"
}

jkillall() {
    echo -e "${YELLOW}Killing all processes...${NC}"
    jkill-be
    jkill-fe
}

# Background process starters (process stays alive after terminal close)
jbe-bg() {
    echo -e "${BLUE}Starting backend in background...${NC}"
    cd "$JH_ROOT/backend" || return 1
    source venv/bin/activate
    nohup uvicorn main:app --reload --port 8000 > "$JH_ROOT/backend/server.log" 2>&1 &
    echo -e "${GREEN}✓ Backend started in background (PID: $!)${NC}"
    echo -e "${BLUE}Logs: tail -f $JH_ROOT/backend/server.log${NC}"
}

jfe-bg() {
    echo -e "${BLUE}Starting frontend in background...${NC}"
    cd "$JH_ROOT/frontend" || return 1
    nohup npm start > "$JH_ROOT/frontend/server.log" 2>&1 &
    echo -e "${GREEN}✓ Frontend started in background (PID: $!)${NC}"
    echo -e "${BLUE}Logs: tail -f $JH_ROOT/frontend/server.log${NC}"
}

# Status check
jstatus() {
    echo -e "${BLUE}=== Job Hunter Status ===${NC}"
    echo ""

    # Check backend
    if lsof -ti:8000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend running${NC} on http://localhost:8000"
    else
        echo -e "${RED}✗ Backend not running${NC}"
    fi

    # Check frontend
    if lsof -ti:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Frontend running${NC} on http://localhost:3000"
    else
        echo -e "${RED}✗ Frontend not running${NC}"
    fi

    echo ""
    echo -e "${BLUE}Quick test:${NC} curl http://localhost:8000/health"
}

# Readiness check - verify all prerequisites are set up
jready() {
    echo -e "${BLUE}=== Job Hunter Readiness Check ===${NC}"
    echo ""

    ISSUES=0

    # 1. Check Python venv
    echo -e "${BLUE}[1/7] Backend virtual environment...${NC}"
    if [ -d "$JH_ROOT/backend/venv" ]; then
        echo -e "${GREEN}  ✓ Virtual environment exists${NC}"
    else
        echo -e "${RED}  ✗ Virtual environment not found${NC}"
        echo -e "${YELLOW}    Fix: cd backend && python3 -m venv venv${NC}"
        ISSUES=$((ISSUES + 1))
    fi

    # 2. Check Python dependencies
    echo -e "${BLUE}[2/7] Backend dependencies...${NC}"
    if [ -d "$JH_ROOT/backend/venv" ]; then
        cd "$JH_ROOT/backend" || return 1
        source venv/bin/activate
        if python -c "import fastapi, sqlalchemy, uvicorn" 2>/dev/null; then
            echo -e "${GREEN}  ✓ Key dependencies installed${NC}"
        else
            echo -e "${RED}  ✗ Missing dependencies${NC}"
            echo -e "${YELLOW}    Auto-fix: Installing dependencies...${NC}"

            # Auto-install dependencies
            pip install -r requirements.txt > /dev/null 2>&1

            # Verify installation
            if python -c "import fastapi, sqlalchemy, uvicorn" 2>/dev/null; then
                echo -e "${GREEN}  ✓ Dependencies installed successfully${NC}"
            else
                echo -e "${RED}  ✗ Auto-fix failed${NC}"
                echo -e "${YELLOW}    Manual fix: cd backend && source venv/bin/activate && pip install -r requirements.txt${NC}"
                ISSUES=$((ISSUES + 1))
            fi
        fi
        deactivate 2>/dev/null || true
        cd "$JH_ROOT" || return 1
    else
        echo -e "${YELLOW}  ⊘ Skipped (venv not found)${NC}"
        ISSUES=$((ISSUES + 1))
    fi

    # 3. Check backend .env.local
    echo -e "${BLUE}[3/7] Backend environment config...${NC}"
    if [ -f "$JH_ROOT/backend/.env.local" ]; then
        echo -e "${GREEN}  ✓ backend/.env.local exists${NC}"
        # Check for required variables
        if grep -q "DATABASE_URL=" "$JH_ROOT/backend/.env.local" && \
           grep -q "GOOGLE_CLIENT_ID=" "$JH_ROOT/backend/.env.local" && \
           grep -q "SECRET_KEY=" "$JH_ROOT/backend/.env.local"; then
            echo -e "${GREEN}  ✓ Required environment variables present${NC}"
        else
            echo -e "${YELLOW}  ⚠ Some required variables may be missing${NC}"
            echo -e "${YELLOW}    Check: DATABASE_URL, GOOGLE_CLIENT_ID, SECRET_KEY${NC}"
        fi
    else
        echo -e "${RED}  ✗ backend/.env.local not found${NC}"
        echo -e "${YELLOW}    Fix: Create backend/.env.local with required variables${NC}"
        ISSUES=$((ISSUES + 1))
    fi

    # 4. Check frontend node_modules
    echo -e "${BLUE}[4/7] Frontend dependencies...${NC}"
    if [ -d "$JH_ROOT/frontend/node_modules" ]; then
        echo -e "${GREEN}  ✓ node_modules exists${NC}"
    else
        echo -e "${RED}  ✗ node_modules not found${NC}"
        echo -e "${YELLOW}    Fix: cd frontend && npm install${NC}"
        ISSUES=$((ISSUES + 1))
    fi

    # 5. Check frontend .env.local
    echo -e "${BLUE}[5/7] Frontend environment config...${NC}"
    if [ -f "$JH_ROOT/frontend/.env.local" ]; then
        echo -e "${GREEN}  ✓ frontend/.env.local exists${NC}"
        # Check for required variables
        if grep -q "REACT_APP_API_URL=" "$JH_ROOT/frontend/.env.local" && \
           grep -q "REACT_APP_GOOGLE_CLIENT_ID=" "$JH_ROOT/frontend/.env.local"; then
            echo -e "${GREEN}  ✓ Required environment variables present${NC}"
        else
            echo -e "${YELLOW}  ⚠ Some required variables may be missing${NC}"
            echo -e "${YELLOW}    Check: REACT_APP_API_URL, REACT_APP_GOOGLE_CLIENT_ID${NC}"
        fi
    else
        echo -e "${RED}  ✗ frontend/.env.local not found${NC}"
        echo -e "${YELLOW}    Fix: Create frontend/.env.local with required variables${NC}"
        ISSUES=$((ISSUES + 1))
    fi

    # 6. Check database connectivity
    echo -e "${BLUE}[6/7] Database connectivity...${NC}"
    if [ -f "$JH_ROOT/backend/.env.local" ] && [ -d "$JH_ROOT/backend/venv" ]; then
        cd "$JH_ROOT/backend" || return 1
        source venv/bin/activate
        DB_CHECK=$(python -c "
import os
from pathlib import Path
from dotenv import load_dotenv
env_local = Path('.env.local')
if env_local.exists():
    load_dotenv(env_local)
db_url = os.getenv('DATABASE_URL')
if db_url:
    if 'ep-aged-darkness-ahpqrn39-pooler' in db_url:
        print('test')
    elif 'ep-quiet-hat-ahe8vhso-pooler' in db_url:
        print('production')
    else:
        print('unknown')
else:
    print('missing')
" 2>/dev/null)
        deactivate 2>/dev/null || true
        cd "$JH_ROOT" || return 1

        if [ "$DB_CHECK" = "test" ]; then
            echo -e "${GREEN}  ✓ DATABASE_URL points to test/dev branch${NC}"
        elif [ "$DB_CHECK" = "production" ]; then
            echo -e "${YELLOW}  ⚠ DATABASE_URL points to PRODUCTION branch${NC}"
            echo -e "${YELLOW}    For local development, use test branch (ep-aged-darkness-ahpqrn39-pooler)${NC}"
        elif [ "$DB_CHECK" = "missing" ]; then
            echo -e "${RED}  ✗ DATABASE_URL not found in .env.local${NC}"
            ISSUES=$((ISSUES + 1))
        else
            echo -e "${YELLOW}  ⚠ DATABASE_URL format not recognized${NC}"
        fi
    else
        echo -e "${YELLOW}  ⊘ Skipped (dependencies not ready)${NC}"
    fi

    # 7. Check port availability
    echo -e "${BLUE}[7/7] Port availability...${NC}"
    PORT_ISSUES=0
    if lsof -ti:8000 > /dev/null 2>&1; then
        echo -e "${YELLOW}  ⚠ Port 8000 (backend) already in use${NC}"
        echo -e "${YELLOW}    Run 'jkill-be' to free it${NC}"
        PORT_ISSUES=$((PORT_ISSUES + 1))
    else
        echo -e "${GREEN}  ✓ Port 8000 (backend) available${NC}"
    fi

    if lsof -ti:3000 > /dev/null 2>&1; then
        echo -e "${YELLOW}  ⚠ Port 3000 (frontend) already in use${NC}"
        echo -e "${YELLOW}    Run 'jkill-fe' to free it${NC}"
        PORT_ISSUES=$((PORT_ISSUES + 1))
    else
        echo -e "${GREEN}  ✓ Port 3000 (frontend) available${NC}"
    fi

    # Summary
    echo ""
    echo -e "${BLUE}=== Summary ===${NC}"
    if [ $ISSUES -eq 0 ] && [ $PORT_ISSUES -eq 0 ]; then
        echo -e "${GREEN}✓ All checks passed! Ready to start development.${NC}"
        echo ""
        echo -e "${BLUE}Quick start:${NC}"
        echo -e "  ${YELLOW}jbe-bg && jfe-bg${NC}   # Start both in background"
        echo -e "  ${YELLOW}jstatus${NC}            # Check status"
        return 0
    else
        if [ $ISSUES -gt 0 ]; then
            echo -e "${RED}✗ Found $ISSUES issue(s) that need fixing${NC}"
        fi
        if [ $PORT_ISSUES -gt 0 ]; then
            echo -e "${YELLOW}⚠ Found $PORT_ISSUES port conflict(s) (run jkillall to clear)${NC}"
        fi
        echo -e "${YELLOW}Fix the issues above and run 'jready' again${NC}"
        return 1
    fi
}

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

# Compare environment variable values and display results
# Args: $1=VAR_NAME, $2=ACTUAL_VAL, $3=EXPECTED_VAL, $4=SOURCE_NAME (e.g., "Lambda" or "Vercel")
_compare_and_display_env() {
    local VAR_NAME="$1"
    local ACTUAL_VAL="$2"
    local EXPECTED_VAL="$3"
    local SOURCE_NAME="$4"

    if [ -z "$ACTUAL_VAL" ]; then
        echo -e "${RED}  ✗ $VAR_NAME NOT SET in $SOURCE_NAME${NC}"
        if [ -n "$EXPECTED_VAL" ]; then
            echo -e "${YELLOW}    Expected: $EXPECTED_VAL${NC}"
        fi
    elif [ -z "$EXPECTED_VAL" ]; then
        echo -e "${YELLOW}  ⚠ $VAR_NAME: No ${VAR_NAME}_PROD_VALUE comment in .env.local${NC}"
        echo -e "${BLUE}    $SOURCE_NAME: $ACTUAL_VAL${NC}"
    elif [ "$ACTUAL_VAL" = "$EXPECTED_VAL" ]; then
        echo -e "${GREEN}  ✓ $VAR_NAME matches${NC}"
        echo -e "${BLUE}    Value: $ACTUAL_VAL${NC}"
    else
        echo -e "${RED}  ✗ $VAR_NAME differs${NC}"
        echo -e "${YELLOW}    $SOURCE_NAME:   $ACTUAL_VAL${NC}"
        echo -e "${YELLOW}    Expected: $EXPECTED_VAL${NC}"
    fi
}

# ==============================================================================
# DEPLOYMENT COMMANDS
# ==============================================================================

# Deploy backend to AWS Lambda via SAM
jpushapi() {
    echo -e "${BLUE}=== Deploying Backend to AWS ===${NC}"
    echo ""

    cd "$JH_ROOT/backend" || return 1

    # Check if DATABASE_URL is set in Lambda (production)
    echo -e "${BLUE}[1/5] Checking current Lambda environment...${NC}"
    LAMBDA_DB=$(aws lambda get-function --function-name JobHuntTrackerAPI --query 'Configuration.Environment.Variables.DATABASE_URL' --output text 2>/dev/null)

    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}  ⚠ Lambda function not found or not accessible${NC}"
        echo -e "${YELLOW}    This might be the first deployment${NC}"
    else
        if [ -n "$LAMBDA_DB" ] && [ "$LAMBDA_DB" != "None" ]; then
            echo -e "${GREEN}  ✓ DATABASE_URL is configured in Lambda${NC}"
            if [[ "$LAMBDA_DB" == *"ep-quiet-hat-ahe8vhso-pooler"* ]]; then
                echo -e "${GREEN}  ✓ Points to PRODUCTION database${NC}"
            else
                echo -e "${YELLOW}  ⚠ DATABASE_URL may not be production branch${NC}"
            fi
        else
            echo -e "${RED}  ✗ DATABASE_URL not set in Lambda!${NC}"
            echo -e "${YELLOW}    You need to set it after deployment via:${NC}"
            echo -e "${YELLOW}    aws lambda update-function-configuration --function-name JobHuntTrackerAPI --environment Variables={...}${NC}"
        fi
    fi

    # Build with SAM
    echo ""
    echo -e "${BLUE}[2/5] Building with SAM...${NC}"
    sam build
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ SAM build failed${NC}"
        cd "$JH_ROOT" || return 1
        return 1
    fi
    echo -e "${GREEN}  ✓ Build successful${NC}"

    # Deploy with SAM (uses samconfig.toml)
    echo ""
    echo -e "${BLUE}[3/5] Deploying to AWS...${NC}"
    sam deploy
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ SAM deploy failed${NC}"
        cd "$JH_ROOT" || return 1
        return 1
    fi
    echo -e "${GREEN}  ✓ Deploy successful${NC}"

    # Get API Gateway URL
    echo ""
    echo -e "${BLUE}[4/5] Retrieving API Gateway URL...${NC}"
    API_URL=$(aws cloudformation describe-stacks --stack-name jh-backend-stack --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text 2>/dev/null)
    if [ -n "$API_URL" ]; then
        echo -e "${GREEN}  ✓ API URL: ${BLUE}$API_URL${NC}"
    else
        echo -e "${YELLOW}  ⚠ Could not retrieve API URL${NC}"
    fi

    # Verify environment variables
    echo ""
    echo -e "${BLUE}[5/5] Verifying Lambda environment variables...${NC}"
    LAMBDA_VARS=$(aws lambda get-function --function-name JobHuntTrackerAPI --query 'Configuration.Environment.Variables' --output json 2>/dev/null)

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ Environment variables:${NC}"
        echo "$LAMBDA_VARS" | python3 -m json.tool | grep -E "(GOOGLE_CLIENT_ID|ALLOWED_ORIGINS|ALLOWED_EMAILS|DATABASE_URL)" | sed 's/^/    /'

        # Check if DATABASE_URL exists
        if echo "$LAMBDA_VARS" | grep -q "DATABASE_URL"; then
            echo ""
            echo -e "${GREEN}  ✓ DATABASE_URL is set${NC}"
        else
            echo ""
            echo -e "${RED}  ✗ DATABASE_URL is NOT set!${NC}"
            echo -e "${YELLOW}    Add it manually:${NC}"
            echo -e "${YELLOW}    1. Go to AWS Lambda Console → JobHuntTrackerAPI → Configuration → Environment variables${NC}"
            echo -e "${YELLOW}    2. Add DATABASE_URL with production value from backend/.env.local comments${NC}"
        fi
    fi

    cd "$JH_ROOT" || return 1
    echo ""
    echo -e "${GREEN}=== Backend deployment complete ===${NC}"
}

# Check and deploy frontend to Vercel
jpushvercel() {
    echo -e "${BLUE}=== Deploying Frontend to Vercel ===${NC}"
    echo ""

    cd "$JH_ROOT/frontend" || return 1

    # Check Vercel project status
    echo -e "${BLUE}[1/5] Checking Vercel project status...${NC}"
    VERCEL_PROJECT=$(vercel project ls 2>&1 | grep "zduan-job")
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ Vercel project found: zduan-job${NC}"
        PROD_URL=$(echo "$VERCEL_PROJECT" | awk '{print $3}')
        echo -e "${GREEN}  ✓ Production URL: ${BLUE}$PROD_URL${NC}"
    else
        echo -e "${RED}  ✗ Vercel project not found${NC}"
        cd "$JH_ROOT" || return 1
        return 1
    fi

    # Check environment variables
    echo ""
    echo -e "${BLUE}[2/5] Checking Vercel environment variables...${NC}"

    # Check which variables exist (encrypted ones won't show values)
    VERCEL_ENV_LIST=$(vercel env ls production 2>&1)

    echo -e "${BLUE}  Required variables for production:${NC}"
    echo ""

    # Pull env vars from Vercel once
    vercel env pull .env.vercel.check --environment=production > /dev/null 2>&1

    # Track variables that need updating
    typeset -a VARS_TO_UPDATE=()

    # Loop through each variable (using global FRONTEND_CHECK)
    for VAR_NAME in "${(@k)FRONTEND_CHECK}"; do
        EXPECTED_VAL="${FRONTEND_CHECK[$VAR_NAME]}"

        if echo "$VERCEL_ENV_LIST" | grep -q "$VAR_NAME"; then
            if echo "$VERCEL_ENV_LIST" | grep "$VAR_NAME" | grep -q "Encrypted"; then
                echo -e "${GREEN}  ✓ $VAR_NAME: Set (Encrypted/Sensitive)${NC}"
                echo -e "${BLUE}    Expected: $EXPECTED_VAL${NC}"
                echo -e "${YELLOW}    To verify value: Check Vercel Dashboard${NC}"
            else
                # Get value from pulled env file
                if [ -f ".env.vercel.check" ]; then
                    VERCEL_VAL=$(grep "^${VAR_NAME}=" .env.vercel.check | cut -d= -f2- | tr -d '"' | tr -d '\n' | tr -d '\r' | sed 's/\\n$//')
                    if [ "$VERCEL_VAL" = "$EXPECTED_VAL" ]; then
                        echo -e "${GREEN}  ✓ $VAR_NAME matches${NC}"
                        echo -e "${BLUE}    Value: $VERCEL_VAL${NC}"
                    else
                        echo -e "${YELLOW}  ⚠ $VAR_NAME differs${NC}"
                        echo -e "${YELLOW}    Current:  $VERCEL_VAL${NC}"
                        echo -e "${YELLOW}    Expected: $EXPECTED_VAL${NC}"
                        VARS_TO_UPDATE+=("$VAR_NAME")
                    fi
                fi
            fi
        else
            echo -e "${RED}  ✗ $VAR_NAME: NOT SET${NC}"
            echo -e "${YELLOW}    Expected: $EXPECTED_VAL${NC}"
            VARS_TO_UPDATE+=("$VAR_NAME")
        fi
    done

    # Cleanup
    rm -f .env.vercel.check

    echo ""
    echo -e "${BLUE}  Dashboard: https://vercel.com/zduanxs-projects/zduan-job/settings/environment-variables${NC}"

    # Offer to update differing variables
    if [ ${#VARS_TO_UPDATE[@]} -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}The following variable(s) will be updated to match .env.local:${NC}"
        for VAR_NAME in "${VARS_TO_UPDATE[@]}"; do
            EXPECTED_VAL="${FRONTEND_CHECK[$VAR_NAME]}"
            echo -e "${YELLOW}  • $VAR_NAME → $EXPECTED_VAL${NC}"
        done
        echo ""
        echo -n -e "${YELLOW}Update Vercel with these values? [y/n]: ${NC}"
        read UPDATE_CHOICE

        if [[ "$UPDATE_CHOICE" =~ ^[Yy]$ ]]; then
            echo -e "${BLUE}Updating Vercel environment variables...${NC}"
            for VAR_NAME in "${VARS_TO_UPDATE[@]}"; do
                EXPECTED_VAL="${FRONTEND_CHECK[$VAR_NAME]}"
                echo -e "${BLUE}  Setting $VAR_NAME...${NC}"
                echo "$EXPECTED_VAL" | vercel env add "$VAR_NAME" production > /dev/null 2>&1
                if [ $? -eq 0 ]; then
                    echo -e "${GREEN}    ✓ $VAR_NAME updated${NC}"
                else
                    echo -e "${RED}    ✗ Failed to update $VAR_NAME${NC}"
                fi
            done
            echo -e "${GREEN}Environment variable update complete${NC}"
        else
            echo -e "${RED}Aborting deployment - environment variables not synced${NC}"
            cd "$JH_ROOT" || return 1
            return 1
        fi
    fi

    # Check git status
    echo ""
    echo -e "${BLUE}[3/5] Checking git status...${NC}"
    cd "$JH_ROOT" || return 1

    if git diff --quiet frontend/ && git diff --cached --quiet frontend/; then
        echo -e "${GREEN}  ✓ No uncommitted frontend/ changes${NC}"
    else
        echo -e "${YELLOW}  ⚠ You have uncommitted frontend/ changes${NC}"
        echo -e "${YELLOW}    Vercel deploys from git, so commit your changes first${NC}"
        git status --short frontend/ | sed 's/^/    /'
    fi

    # Check current branch
    CURRENT_BRANCH=$(git branch --show-current)
    echo -e "${BLUE}  Current branch: ${YELLOW}$CURRENT_BRANCH${NC}"

    # Check latest deployment status
    echo ""
    echo -e "${BLUE}[4/5] Checking latest Vercel deployments...${NC}"
    cd "$JH_ROOT/frontend" || return 1
    vercel ls --limit 3 2>&1 | tail -n +6 | head -5

    # Trigger git deployment
    echo ""
    echo -e "${BLUE}[5/5] Git push and deployment:${NC}"
    echo -n -e "${YELLOW}Push frontend/ to git for Vercel CI/CD? [y/n]: ${NC}"
    read DEPLOY_CHOICE

    if [[ "$DEPLOY_CHOICE" =~ ^[Yy]$ ]]; then
        cd "$JH_ROOT" || return 1

        # Only add frontend changes
        echo -e "${BLUE}Adding frontend/ changes...${NC}"
        git add frontend/

        # Check if there are staged changes
        if git diff --cached --quiet; then
            echo -e "${YELLOW}  ⚠ No frontend changes to commit${NC}"
        else
            # Show what will be committed
            echo -e "${BLUE}Staged changes:${NC}"
            git status --short | grep "^[AM]" | sed 's/^/  /'

            echo -n -e "${YELLOW}Commit message: ${NC}"
            read COMMIT_MSG

            if [ -z "$COMMIT_MSG" ]; then
                echo -e "${RED}✗ Commit message required${NC}"
                git reset > /dev/null 2>&1
                cd "$JH_ROOT" || return 1
                return 1
            fi

            # Commit
            git commit -m "$COMMIT_MSG"
            if [ $? -ne 0 ]; then
                echo -e "${RED}✗ Commit failed${NC}"
                cd "$JH_ROOT" || return 1
                return 1
            fi

            # Push
            echo -e "${BLUE}Pushing to git...${NC}"
            git push origin "$CURRENT_BRANCH"
            if [ $? -ne 0 ]; then
                echo -e "${RED}✗ Git push failed${NC}"
                cd "$JH_ROOT" || return 1
                return 1
            fi

            echo -e "${GREEN}✓ Pushed to git. Vercel CI/CD will auto-deploy.${NC}"
            echo ""

            # Wait a moment for Vercel to pick up the deployment
            echo -e "${BLUE}Waiting for Vercel to pick up deployment...${NC}"
            sleep 3

            # Check latest deployment status
            cd "$JH_ROOT/frontend" || return 1
            echo -e "${BLUE}Latest Vercel deployments:${NC}"
            vercel ls --limit 5 2>&1 | tail -n +6 | head -7

            echo ""
            echo -e "${BLUE}Monitor deployment:${NC}"
            echo -e "  Dashboard: ${BLUE}https://vercel.com/zduanxs-projects/zduan-job${NC}"
            echo -e "  Live site:  ${BLUE}https://zduan-job.vercel.app${NC}"
        fi
    else
        echo -e "${RED}Deployment cancelled by user${NC}"
        cd "$JH_ROOT" || return 1
        return 1
    fi

    cd "$JH_ROOT" || return 1
    echo ""
    echo -e "${GREEN}=== Frontend deployment complete ===${NC}"
}

# Verify environment variables are synced between local and deployed
jenvcheck() {
    echo -e "${BLUE}=== Environment Variables Check ===${NC}"
    echo ""

    # Backend (Lambda vs .env.local)
    echo -e "${BLUE}Backend (AWS Lambda):${NC}"
    echo -e "${BLUE}  Comparing .env.local PROD_VALUE → Lambda:${NC}"

    if [ -f "$JH_ROOT/backend/.env.local" ]; then
        # Get Lambda env vars
        LAMBDA_VARS=$(aws lambda get-function --function-name JobHuntTrackerAPI --query 'Configuration.Environment.Variables' 2>/dev/null)

        if [ $? -eq 0 ]; then
            # Loop through each variable (using global BACKEND_CHECK)
            for VAR_NAME in "${(@k)BACKEND_CHECK}"; do
                EXPECTED_VAL="${BACKEND_CHECK[$VAR_NAME]}"
                LAMBDA_VAL=$(echo "$LAMBDA_VARS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('$VAR_NAME', ''))")
                _compare_and_display_env "$VAR_NAME" "$LAMBDA_VAL" "$EXPECTED_VAL" "Lambda"
            done
        else
            echo -e "${RED}  ✗ Cannot access Lambda function${NC}"
        fi
    else
        echo -e "${RED}  ✗ backend/.env.local not found${NC}"
    fi

    echo ""
    echo -e "${BLUE}Frontend (Vercel):${NC}"
    echo -e "${BLUE}  Comparing .env.local PROD_VALUE → Vercel:${NC}"

    if [ -f "$JH_ROOT/frontend/.env.local" ]; then
        cd "$JH_ROOT/frontend" || return 1

        # Pull env vars from Vercel
        vercel env pull .env.vercel.check --environment=production > /dev/null 2>&1

        if [ -f ".env.vercel.check" ]; then
            # Loop through each variable (using global FRONTEND_CHECK)
            for VAR_NAME in "${(@k)FRONTEND_CHECK}"; do
                EXPECTED_VAL="${FRONTEND_CHECK[$VAR_NAME]}"
                VERCEL_VAL=$(grep "^${VAR_NAME}=" .env.vercel.check | cut -d= -f2- | tr -d '"' | tr -d '\n' | tr -d '\r' | sed 's/\\n$//')
                _compare_and_display_env "$VAR_NAME" "$VERCEL_VAL" "$EXPECTED_VAL" "Vercel"
            done

            # Cleanup
            rm -f .env.vercel.check
        else
            echo -e "${RED}  ✗ Cannot retrieve Vercel environment variables${NC}"
            echo -e "${YELLOW}    Run 'jpushvercel' to check connection and fix${NC}"
        fi

        cd "$JH_ROOT" || return 1
    else
        echo -e "${RED}  ✗ frontend/.env.local not found${NC}"
    fi

    echo ""
}

# Help
jhelp() {
    echo -e "${BLUE}=== Job Hunter Development Shortcuts ===${NC}"
    echo ""
    echo -e "${GREEN}Start Services:${NC}"
    echo "  jbe                - Start backend (foreground)"
    echo "  jfe                - Start frontend (foreground)"
    echo "  jbe-bg             - Start backend (background, survives terminal close)"
    echo "  jfe-bg             - Start frontend (background, survives terminal close)"
    echo ""
    echo -e "${GREEN}Stop Services:${NC}"
    echo "  jkill-be           - Kill backend"
    echo "  jkill-fe           - Kill frontend"
    echo "  jkillall           - Kill both"
    echo ""
    echo -e "${GREEN}Deployment:${NC}"
    echo "  jpushapi           - Deploy backend to AWS Lambda (SAM)"
    echo "  jpushvercel        - Deploy frontend to Vercel (git CI/CD)"
    echo "  jenvcheck          - Verify environment variables (local vs deployed)"
    echo ""
    echo -e "${GREEN}Utilities:${NC}"
    echo "  jready             - Check all prerequisites"
    echo "  jstatus            - Check what's running"
    echo "  jhelp              - Show this help"
    echo ""
    echo -e "${YELLOW}Quick start:${NC}"
    echo "  jbe-bg && jfe-bg   # Start both in background"
    echo "  jstatus            # Check status"
    echo "  jkillall           # Stop everything"
}

# Show help on load
echo -e "${GREEN}Job Hunter dev shortcuts loaded!${NC} Type ${BLUE}jhelp${NC} for commands."
