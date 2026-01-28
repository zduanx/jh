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
    BACKEND_TEST_DATABASE_URL_PROD=$(grep "^# TEST_DATABASE_URL_PROD_VALUE=" "$JH_ROOT/backend/.env.local" | cut -d= -f2- | tr -d '\n' | tr -d '\r')
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
    ["TEST_DATABASE_URL"]="$BACKEND_TEST_DATABASE_URL_PROD"
)

typeset -A FRONTEND_CHECK=(
    ["REACT_APP_GOOGLE_CLIENT_ID"]="$FRONTEND_GOOGLE_CLIENT_ID_PROD"
    ["REACT_APP_API_URL"]="$FRONTEND_API_URL_PROD"
)

# Database URLs to check in jready
typeset -a DB_CHECK_VARS=(
    "DATABASE_URL"
    "TEST_DATABASE_URL"
)

# ==============================================================================
# HELPER FUNCTION: Normalize environment variable values
# ==============================================================================
# Strips literal \n, \r, \t escape sequences and quotes from env var values
# This prevents issues where values like "url\n" differ from clean "url"
_normalize_env_value() {
    local value="$1"
    # Remove quotes, then remove literal \n, \r, \t escape sequences
    echo "$value" | tr -d '"' | sed 's/\\n//g' | sed 's/\\r//g' | sed 's/\\t//g'
}

# Get test database URL from backend/.env.local
_get_test_db_url() {
    grep "^DATABASE_URL=" "$JH_ROOT/backend/.env.local" 2>/dev/null | cut -d= -f2-
}

# Get prod database URL from backend/.env.local (from PROD_VALUE comment)
_get_prod_db_url() {
    grep "^# DATABASE_URL_PROD_VALUE=" "$JH_ROOT/backend/.env.local" 2>/dev/null | cut -d= -f2-
}

# Mask password in database URL for display
_mask_db_url() {
    echo "$1" | sed 's/:[^:@]*@/:***@/'
}

# Backend shortcuts
jbe() {
    cd "$JH_ROOT" || return 1
    echo -e "${BLUE}Starting backend server...${NC}"
    cd "$JH_ROOT/backend" || return 1
    source venv/bin/activate
    uvicorn main:app --reload --port 8000
}

# Frontend shortcuts
jfe() {
    cd "$JH_ROOT" || return 1
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
    cd "$JH_ROOT" || return 1
    echo -e "${BLUE}Starting backend in background...${NC}"
    cd "$JH_ROOT/backend" || return 1
    source venv/bin/activate
    nohup uvicorn main:app --reload --port 8000 > "$JH_ROOT/backend/server.log" 2>&1 &
    echo -e "${GREEN}✓ Backend started in background (PID: $!)${NC}"
    echo -e "${BLUE}Logs: tail -f $JH_ROOT/backend/server.log${NC}"
}

jfe-bg() {
    cd "$JH_ROOT" || return 1
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
    echo -e "${BLUE}[1/8] Backend virtual environment...${NC}"
    if [ -d "$JH_ROOT/backend/venv" ]; then
        echo -e "${GREEN}  ✓ Virtual environment exists${NC}"
    else
        echo -e "${RED}  ✗ Virtual environment not found${NC}"
        echo -e "${YELLOW}    Fix: cd backend && python3 -m venv venv${NC}"
        ISSUES=$((ISSUES + 1))
    fi

    # 2. Check Python dependencies
    echo -e "${BLUE}[2/8] Backend dependencies...${NC}"
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
    echo -e "${BLUE}[3/8] Backend environment config...${NC}"
    if [ -f "$JH_ROOT/backend/.env.local" ]; then
        echo -e "${GREEN}  ✓ backend/.env.local exists${NC}"
        # Check for required variables using BACKEND_CHECK keys
        MISSING_BACKEND_VARS=()
        for VAR_NAME in "${(@k)BACKEND_CHECK}"; do
            if ! grep -q "^${VAR_NAME}=" "$JH_ROOT/backend/.env.local"; then
                MISSING_BACKEND_VARS+=("$VAR_NAME")
            fi
        done
        if [ ${#MISSING_BACKEND_VARS[@]} -eq 0 ]; then
            echo -e "${GREEN}  ✓ Required environment variables present${NC}"
        else
            echo -e "${YELLOW}  ⚠ Some required variables may be missing${NC}"
            echo -e "${YELLOW}    Check: ${MISSING_BACKEND_VARS[*]}${NC}"
        fi
    else
        echo -e "${RED}  ✗ backend/.env.local not found${NC}"
        echo -e "${YELLOW}    Fix: Create backend/.env.local with required variables${NC}"
        ISSUES=$((ISSUES + 1))
    fi

    # 4. Check frontend node_modules
    echo -e "${BLUE}[4/8] Frontend dependencies...${NC}"
    if [ -d "$JH_ROOT/frontend/node_modules" ]; then
        echo -e "${GREEN}  ✓ node_modules exists${NC}"
    else
        echo -e "${RED}  ✗ node_modules not found${NC}"
        echo -e "${YELLOW}    Fix: cd frontend && npm install${NC}"
        ISSUES=$((ISSUES + 1))
    fi

    # 5. Check frontend .env.local
    echo -e "${BLUE}[5/8] Frontend environment config...${NC}"
    if [ -f "$JH_ROOT/frontend/.env.local" ]; then
        echo -e "${GREEN}  ✓ frontend/.env.local exists${NC}"
        # Check for required variables using FRONTEND_CHECK keys
        MISSING_FRONTEND_VARS=()
        for VAR_NAME in "${(@k)FRONTEND_CHECK}"; do
            if ! grep -q "^${VAR_NAME}=" "$JH_ROOT/frontend/.env.local"; then
                MISSING_FRONTEND_VARS+=("$VAR_NAME")
            fi
        done
        if [ ${#MISSING_FRONTEND_VARS[@]} -eq 0 ]; then
            echo -e "${GREEN}  ✓ Required environment variables present${NC}"
        else
            echo -e "${YELLOW}  ⚠ Some required variables may be missing${NC}"
            echo -e "${YELLOW}    Check: ${MISSING_FRONTEND_VARS[*]}${NC}"
        fi
    else
        echo -e "${RED}  ✗ frontend/.env.local not found${NC}"
        echo -e "${YELLOW}    Fix: Create frontend/.env.local with required variables${NC}"
        ISSUES=$((ISSUES + 1))
    fi

    # 6. Check database connectivity (test both local/test and prod databases)
    echo -e "${BLUE}[6/8] Database connectivity...${NC}"
    if [ -f "$JH_ROOT/backend/.env.local" ] && [ -d "$JH_ROOT/backend/venv" ]; then
        cd "$JH_ROOT/backend" || return 1
        source venv/bin/activate

        for DB_VAR in "${DB_CHECK_VARS[@]}"; do
            # Get prod URL from BACKEND_CHECK
            PROD_URL="${BACKEND_CHECK[$DB_VAR]}"

            # Test both local (test) and prod connections
            DB_RESULT=$(python -c "
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

env_local = Path('.env.local')
if env_local.exists():
    load_dotenv(env_local)

local_url = os.getenv('$DB_VAR')
prod_url = '$PROD_URL'

results = []

# Test local/test DB
if local_url:
    try:
        engine = create_engine(local_url)
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        results.append('local:ok')
    except Exception as e:
        results.append(f'local:error:{str(e)[:50]}')
else:
    results.append('local:missing')

# Test prod DB
if prod_url:
    try:
        engine = create_engine(prod_url)
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        results.append('prod:ok')
    except Exception as e:
        results.append(f'prod:error:{str(e)[:50]}')
else:
    results.append('prod:missing')

print('|'.join(results))
" 2>/dev/null)

            # Parse results (format: "local:status|prod:status")
            LOCAL_RESULT=$(echo "$DB_RESULT" | cut -d'|' -f1)
            PROD_RESULT=$(echo "$DB_RESULT" | cut -d'|' -f2)

            # Display local/test result
            if [[ "$LOCAL_RESULT" == "local:ok" ]]; then
                echo -e "${GREEN}  ✓ $DB_VAR (test) connected${NC}"
            elif [[ "$LOCAL_RESULT" == "local:missing" ]]; then
                echo -e "${RED}  ✗ $DB_VAR (test) not configured${NC}"
                ISSUES=$((ISSUES + 1))
            elif [[ "$LOCAL_RESULT" == local:error:* ]]; then
                echo -e "${RED}  ✗ $DB_VAR (test) connection failed${NC}"
                echo -e "${YELLOW}    ${LOCAL_RESULT#local:error:}${NC}"
                ISSUES=$((ISSUES + 1))
            fi

            # Display prod result
            if [[ "$PROD_RESULT" == "prod:ok" ]]; then
                echo -e "${GREEN}  ✓ $DB_VAR (prod) connected${NC}"
            elif [[ "$PROD_RESULT" == "prod:missing" ]]; then
                echo -e "${YELLOW}  ⊘ $DB_VAR (prod) not configured${NC}"
            elif [[ "$PROD_RESULT" == prod:error:* ]]; then
                echo -e "${RED}  ✗ $DB_VAR (prod) connection failed${NC}"
                echo -e "${YELLOW}    ${PROD_RESULT#prod:error:}${NC}"
                ISSUES=$((ISSUES + 1))
            fi
        done

        deactivate 2>/dev/null || true
        cd "$JH_ROOT" || return 1
    else
        echo -e "${YELLOW}  ⊘ Skipped (dependencies not ready)${NC}"
    fi

    # 7. Run codegen to ensure frontend schemas are up to date
    echo -e "${BLUE}[7/8] Frontend schema codegen...${NC}"
    if [ -d "$JH_ROOT/backend/venv" ]; then
        cd "$JH_ROOT/backend" || return 1
        source venv/bin/activate

        CODEGEN_OUTPUT=$(python3 scripts/generate_tracking_schema.py 2>&1)
        CODEGEN_EXIT=$?

        deactivate 2>/dev/null || true
        cd "$JH_ROOT" || return 1

        if [ $CODEGEN_EXIT -eq 0 ]; then
            echo -e "${GREEN}  ✓ Frontend schemas up to date${NC}"
        elif [ $CODEGEN_EXIT -eq 1 ]; then
            echo -e "${YELLOW}  ⚠ Frontend schemas updated (commit the changes)${NC}"
            echo "$CODEGEN_OUTPUT" | grep -E "^\s+" | sed 's/^/  /'
        else
            echo -e "${RED}  ✗ Codegen failed${NC}"
            echo "$CODEGEN_OUTPUT" | sed 's/^/    /'
            ISSUES=$((ISSUES + 1))
        fi
    else
        echo -e "${YELLOW}  ⊘ Skipped (venv not found)${NC}"
    fi

    # 8. Check port availability
    echo -e "${BLUE}[8/8] Port availability...${NC}"
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

# Check and deploy frontend to Vercel
jpushvercel() {
    echo -e "${BLUE}=== Deploying Frontend to Vercel ===${NC}"
    echo ""

    cd "$JH_ROOT" || return 1
    cd frontend || return 1

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

    echo -e "${BLUE}  Required variables for production:${NC}"
    echo ""

    # Pull env vars from Vercel to get actual decrypted values
    vercel env pull .env.vercel.check --environment=production > /dev/null 2>&1

    # Track variables that need updating
    typeset -a VARS_TO_UPDATE=()

    if [ -f ".env.vercel.check" ]; then
        # Loop through each variable (using global FRONTEND_CHECK)
        for VAR_NAME in "${(@k)FRONTEND_CHECK}"; do
            EXPECTED_VAL="${FRONTEND_CHECK[$VAR_NAME]}"

            # Get value from pulled env file (preserve literal \n for detection)
            VERCEL_VAL_RAW=$(grep "^${VAR_NAME}=" .env.vercel.check | cut -d= -f2-)
            VERCEL_VAL=$(printf "%s" "$VERCEL_VAL_RAW" | tr -d '"')

            # Also get normalized version to check if it matches when cleaned
            VERCEL_VAL_CLEAN=$(_normalize_env_value "$VERCEL_VAL_RAW")

            if [ -n "$VERCEL_VAL" ]; then
                # Variable exists in Vercel
                # Check if raw value matches (ideal case)
                if [ "$VERCEL_VAL" = "$EXPECTED_VAL" ]; then
                    echo -e "${GREEN}  ✓ $VAR_NAME matches${NC}"
                    echo -e "${BLUE}    Value: $VERCEL_VAL${NC}"
                # Check if it matches after cleaning (needs fixing)
                elif [ "$VERCEL_VAL_CLEAN" = "$EXPECTED_VAL" ]; then
                    echo -e "${YELLOW}  ⚠ $VAR_NAME has corrupted escape sequences (will fix)${NC}"
                    echo -e "${YELLOW}    Current:  $VERCEL_VAL${NC}"
                    echo -e "${YELLOW}    Expected: $EXPECTED_VAL${NC}"
                    VARS_TO_UPDATE+=("$VAR_NAME")
                # Completely different value
                else
                    echo -e "${RED}  ✗ $VAR_NAME differs${NC}"
                    echo -e "${YELLOW}    Vercel:   $VERCEL_VAL${NC}"
                    echo -e "${YELLOW}    Expected: $EXPECTED_VAL${NC}"
                    VARS_TO_UPDATE+=("$VAR_NAME")
                fi
            else
                # Variable not found in Vercel
                echo -e "${RED}  ✗ $VAR_NAME: NOT SET${NC}"
                echo -e "${YELLOW}    Expected: $EXPECTED_VAL${NC}"
                VARS_TO_UPDATE+=("$VAR_NAME")
            fi
        done

        # Cleanup
        rm -f .env.vercel.check
    else
        echo -e "${RED}  ✗ Cannot retrieve Vercel environment variables${NC}"
        cd "$JH_ROOT" || return 1
        return 1
    fi

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

                # Remove existing variable if it exists (suppress errors if not found)
                echo "y" | vercel env rm "$VAR_NAME" production > /dev/null 2>&1

                # Add the new value (use printf to avoid adding newline that becomes literal \n)
                printf "%s" "$EXPECTED_VAL" | vercel env add "$VAR_NAME" production > /dev/null 2>&1
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

    # Check for uncommitted changes (including untracked files)
    FRONTEND_CHANGES=$(git status --porcelain frontend/ 2>/dev/null)
    if [ -z "$FRONTEND_CHANGES" ]; then
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

    if [ -f "$JH_ROOT/backend/.env.local" ]; then
        # Check API Lambda
        echo -e "${BLUE}  API Lambda (JobHuntTrackerAPI):${NC}"
        LAMBDA_VARS=$(aws lambda get-function --function-name JobHuntTrackerAPI --query 'Configuration.Environment.Variables' 2>/dev/null)

        if [ $? -eq 0 ]; then
            # Loop through each variable (using global BACKEND_CHECK)
            for VAR_NAME in "${(@k)BACKEND_CHECK}"; do
                EXPECTED_VAL="${BACKEND_CHECK[$VAR_NAME]}"
                LAMBDA_VAL_RAW=$(echo "$LAMBDA_VARS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('$VAR_NAME', ''))")
                LAMBDA_VAL=$(_normalize_env_value "$LAMBDA_VAL_RAW")
                _compare_and_display_env "$VAR_NAME" "$LAMBDA_VAL" "$EXPECTED_VAL" "Lambda"
            done

            # Check WORKER_FUNCTION_NAME
            WORKER_FN=$(echo "$LAMBDA_VARS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('WORKER_FUNCTION_NAME', ''))")
            if [ -n "$WORKER_FN" ]; then
                echo -e "${GREEN}  ✓ WORKER_FUNCTION_NAME=${WORKER_FN}${NC}"
            else
                echo -e "${RED}  ✗ WORKER_FUNCTION_NAME (missing - async invoke won't work)${NC}"
            fi
        else
            echo -e "${RED}  ✗ Cannot access API Lambda${NC}"
        fi

        # Check Worker Lambda
        echo ""
        echo -e "${BLUE}  Worker Lambda (IngestionWorker):${NC}"
        WORKER_VARS=$(aws lambda get-function --function-name IngestionWorker --query 'Configuration.Environment.Variables' 2>/dev/null)

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}  ✓ Worker Lambda exists${NC}"
            # Check DATABASE_URL is set (worker needs DB access)
            WORKER_DB=$(echo "$WORKER_VARS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('DATABASE_URL', ''))" 2>/dev/null)
            if [ -n "$WORKER_DB" ]; then
                echo -e "${GREEN}    ✓ DATABASE_URL configured${NC}"
            else
                echo -e "${RED}    ✗ DATABASE_URL missing${NC}"
            fi
        else
            echo -e "${YELLOW}  ⚠ Worker Lambda not deployed yet${NC}"
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
                # Get raw value without normalization to detect corruption (preserve literal \n)
                VERCEL_VAL_RAW=$(grep "^${VAR_NAME}=" .env.vercel.check | cut -d= -f2-)
                VERCEL_VAL=$(printf "%s" "$VERCEL_VAL_RAW" | tr -d '"')
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

# ==============================================================================
# CODEGEN COMMANDS
# ==============================================================================

# Generate frontend schema from backend Pydantic models
jcodegen() {
    echo -e "${BLUE}=== Generating Frontend Schemas ===${NC}"
    echo ""

    cd "$JH_ROOT/backend" || return 1
    source venv/bin/activate

    # Run tracking schema generator
    echo -e "${BLUE}[1/1] Tracking schema (backend -> frontend)...${NC}"
    python3 scripts/generate_tracking_schema.py
    CODEGEN_EXIT=$?

    deactivate 2>/dev/null || true
    cd "$JH_ROOT" || return 1

    if [ $CODEGEN_EXIT -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✓ Schema generation complete (no changes)${NC}"
        return 0
    elif [ $CODEGEN_EXIT -eq 1 ]; then
        echo ""
        echo -e "${GREEN}✓ Schema generation complete (files updated)${NC}"
        return 0
    else
        echo ""
        echo -e "${RED}✗ Schema generation failed${NC}"
        return 1
    fi
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
    echo -e "${GREEN}Database:${NC}"
    echo "  jdbcreate <name>   - Create new Alembic migration"
    echo "  jdbpush            - Apply migrations to test + prod databases"
    echo "  jdbstatus          - Show current migration status"
    echo ""
    echo -e "${GREEN}Codegen:${NC}"
    echo "  jcodegen           - Generate frontend schemas from backend models"
    echo ""
    echo -e "${GREEN}Deployment:${NC}"
    echo "  jpushapi           - Deploy backend to AWS Lambda (SAM)"
    echo "  jpushvercel        - Deploy frontend to Vercel (git CI/CD)"
    echo "  jenvcheck          - Verify environment variables (local vs deployed)"
    echo ""
    echo -e "${GREEN}Debugging:${NC}"
    echo "  js3get <s3_url>    - Download S3 object to stdout (raw/google/...)"
    echo "  js3url <s3_url>    - Generate presigned URL for S3 object"
    echo ""
    echo -e "${GREEN}Utilities:${NC}"
    echo "  jready             - Check all prerequisites + run codegen"
    echo "  jstatus            - Check what's running"
    echo "  jhelp              - Show this help"
    echo ""
    echo -e "${YELLOW}Quick start:${NC}"
    echo "  jbe-bg && jfe-bg   # Start both in background"
    echo "  jstatus            # Check status"
    echo "  jkillall           # Stop everything"
}

# ==============================================================================
# S3 DEBUGGING COMMANDS
# ==============================================================================

# Download S3 object to stdout
# Usage: js3get s3://bucket/key or js3get raw/google/jobs_123.html
js3get() {
    if [ -z "$1" ]; then
        echo -e "${RED}Usage: js3get <s3_url_or_key>${NC}"
        echo -e "${YELLOW}Examples:${NC}"
        echo -e "  js3get s3://jh-raw-content-123456789/raw/google/jobs_123.html"
        echo -e "  js3get raw/google/jobs_123.html  # Uses default bucket"
        return 1
    fi

    local S3_PATH="$1"

    # If not a full s3:// URL, prepend the default bucket
    if [[ ! "$S3_PATH" =~ ^s3:// ]]; then
        # Get bucket name from AWS (assumes single jh-raw-content bucket)
        local BUCKET=$(aws s3 ls | grep "jh-raw-content" | awk '{print $3}')
        if [ -z "$BUCKET" ]; then
            echo -e "${RED}✗ Could not find jh-raw-content bucket${NC}"
            return 1
        fi
        S3_PATH="s3://$BUCKET/$S3_PATH"
    fi

    echo -e "${BLUE}Fetching: $S3_PATH${NC}" >&2
    aws s3 cp "$S3_PATH" -
}

# Generate presigned URL for S3 object (valid 1 hour)
# Usage: js3url s3://bucket/key or js3url raw/google/jobs_123.html
js3url() {
    if [ -z "$1" ]; then
        echo -e "${RED}Usage: js3url <s3_url_or_key>${NC}"
        echo -e "${YELLOW}Examples:${NC}"
        echo -e "  js3url s3://jh-raw-content-123456789/raw/google/jobs_123.html"
        echo -e "  js3url raw/google/jobs_123.html  # Uses default bucket"
        return 1
    fi

    local S3_PATH="$1"

    # If not a full s3:// URL, prepend the default bucket
    if [[ ! "$S3_PATH" =~ ^s3:// ]]; then
        # Get bucket name from AWS (assumes single jh-raw-content bucket)
        local BUCKET=$(aws s3 ls | grep "jh-raw-content" | awk '{print $3}')
        if [ -z "$BUCKET" ]; then
            echo -e "${RED}✗ Could not find jh-raw-content bucket${NC}"
            return 1
        fi
        S3_PATH="s3://$BUCKET/$S3_PATH"
    fi

    # Parse bucket and key from s3:// URL
    local BUCKET_KEY="${S3_PATH#s3://}"
    local BUCKET="${BUCKET_KEY%%/*}"
    local KEY="${BUCKET_KEY#*/}"

    echo -e "${BLUE}Generating presigned URL for: $S3_PATH${NC}" >&2
    aws s3 presign "s3://$BUCKET/$KEY" --expires-in 3600
}

# ==============================================================================
# DATABASE COMMANDS
# ==============================================================================

# Create a new Alembic migration
jdbcreate() {
    if [ -z "$1" ]; then
        echo -e "${RED}Usage: jdbcreate <migration_name>${NC}"
        echo -e "${YELLOW}Example: jdbcreate create_user_company_settings${NC}"
        return 1
    fi

    local MIGRATION_NAME="$1"
    echo -e "${BLUE}=== Creating Alembic Migration ===${NC}"
    echo ""

    cd "$JH_ROOT" || return 1
    cd backend || return 1
    source venv/bin/activate

    # Check current status first
    echo -e "${BLUE}[1/3] Checking current migration status...${NC}"
    alembic current 2>/dev/null
    echo ""

    # Generate new migration
    echo -e "${BLUE}[2/3] Generating migration: ${YELLOW}$MIGRATION_NAME${NC}"
    alembic revision --autogenerate -m "$MIGRATION_NAME"

    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Failed to create migration${NC}"
        deactivate 2>/dev/null || true
        cd "$JH_ROOT" || return 1
        return 1
    fi

    # Find the newly created migration file
    echo ""
    echo -e "${BLUE}[3/3] Migration created:${NC}"
    LATEST_MIGRATION=$(ls -t alembic/versions/*.py 2>/dev/null | head -1)
    if [ -n "$LATEST_MIGRATION" ]; then
        echo -e "${GREEN}  ✓ $LATEST_MIGRATION${NC}"
        echo ""
        echo -e "${YELLOW}Next steps:${NC}"
        echo -e "  1. Review and edit the migration file"
        echo -e "  2. Run ${BLUE}jdbpush${NC} to apply to test + prod databases"
    fi

    deactivate 2>/dev/null || true
    cd "$JH_ROOT" || return 1
}

# Show migration status for both databases
jdbstatus() {
    echo -e "${BLUE}=== Database Migration Status ===${NC}"
    echo ""

    cd "$JH_ROOT" || return 1
    cd backend || return 1
    source venv/bin/activate

    # Check test database
    echo -e "${BLUE}Test Database (DATABASE_URL):${NC}"
    local TEST_DB_URL=$(_get_test_db_url)
    if [ -n "$TEST_DB_URL" ]; then
        echo -e "${YELLOW}  URL: $(_mask_db_url "$TEST_DB_URL")${NC}"
        export DATABASE_URL="$TEST_DB_URL"
        echo -e "${BLUE}  Migration:${NC}"
        alembic current 2>&1 | sed 's/^/    /'
        echo -e "${BLUE}  Tables:${NC}"
        python3 -c "
from sqlalchemy import create_engine, inspect
import os
engine = create_engine(os.environ['DATABASE_URL'])
inspector = inspect(engine)
tables = inspector.get_table_names()
for t in sorted(tables):
    print(f'    - {t}')
" 2>/dev/null || echo -e "${RED}    ✗ Could not list tables${NC}"
    else
        echo -e "${RED}  ✗ DATABASE_URL not configured${NC}"
    fi

    echo ""

    # Check prod database
    echo -e "${BLUE}Prod Database (DATABASE_URL_PROD_VALUE):${NC}"
    local PROD_DB_URL=$(_get_prod_db_url)
    if [ -n "$PROD_DB_URL" ]; then
        echo -e "${YELLOW}  URL: $(_mask_db_url "$PROD_DB_URL")${NC}"
        export DATABASE_URL="$PROD_DB_URL"
        echo -e "${BLUE}  Migration:${NC}"
        alembic current 2>&1 | sed 's/^/    /'
        echo -e "${BLUE}  Tables:${NC}"
        python3 -c "
from sqlalchemy import create_engine, inspect
import os
engine = create_engine(os.environ['DATABASE_URL'])
inspector = inspect(engine)
tables = inspector.get_table_names()
for t in sorted(tables):
    print(f'    - {t}')
" 2>/dev/null || echo -e "${RED}    ✗ Could not list tables${NC}"
    else
        echo -e "${YELLOW}  ⊘ DATABASE_URL_PROD_VALUE not configured${NC}"
    fi

    deactivate 2>/dev/null || true
    cd "$JH_ROOT" || return 1
}

# Apply migrations to both test and prod databases
jdbpush() {
    echo -e "${BLUE}=== Applying Database Migrations ===${NC}"
    echo ""

    cd "$JH_ROOT" || return 1
    cd backend || return 1
    source venv/bin/activate

    # Get database URLs using helper functions
    local TEST_DB_URL=$(_get_test_db_url)
    local PROD_DB_URL=$(_get_prod_db_url)

    if [ -z "$TEST_DB_URL" ]; then
        echo -e "${RED}✗ DATABASE_URL not found in .env.local${NC}"
        deactivate 2>/dev/null || true
        cd "$JH_ROOT" || return 1
        return 1
    fi

    # Show pending migrations
    echo -e "${BLUE}[1/4] Checking pending migrations...${NC}"
    export DATABASE_URL="$TEST_DB_URL"

    CURRENT=$(alembic current 2>&1 | grep -oE '[a-f0-9]{12}' | head -1)
    HEAD=$(alembic heads 2>&1 | grep -oE '[a-f0-9]{12}' | head -1)

    if [ "$CURRENT" = "$HEAD" ]; then
        echo -e "${GREEN}  ✓ Already at latest migration: $HEAD${NC}"
        echo -e "${YELLOW}  No migrations to apply${NC}"
        deactivate 2>/dev/null || true
        cd "$JH_ROOT" || return 1
        return 0
    fi

    echo -e "${YELLOW}  Current: ${CURRENT:-none}${NC}"
    echo -e "${YELLOW}  Head:    $HEAD${NC}"
    echo ""

    # Show migration history
    echo -e "${BLUE}[2/4] Migration history:${NC}"
    alembic history --verbose 2>&1 | head -20 | sed 's/^/  /'
    echo ""

    # Confirm
    echo -e "${YELLOW}This will apply migrations to:${NC}"
    echo -e "${YELLOW}  1. Test database (DATABASE_URL)${NC}"
    if [ -n "$PROD_DB_URL" ]; then
        echo -e "${YELLOW}  2. Prod database (DATABASE_URL_PROD_VALUE)${NC}"
    else
        echo -e "${YELLOW}  2. Prod database: ${RED}NOT CONFIGURED${NC}"
    fi
    echo ""
    echo -n -e "${YELLOW}Proceed with migrations? [y/n]: ${NC}"
    read CONFIRM

    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo -e "${RED}Migration cancelled${NC}"
        deactivate 2>/dev/null || true
        cd "$JH_ROOT" || return 1
        return 1
    fi

    # Apply to test database
    echo ""
    echo -e "${BLUE}[3/4] Applying to TEST database...${NC}"
    export DATABASE_URL="$TEST_DB_URL"
    alembic upgrade head

    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Migration failed on test database${NC}"
        echo -e "${RED}  Prod database NOT updated${NC}"
        deactivate 2>/dev/null || true
        cd "$JH_ROOT" || return 1
        return 1
    fi
    echo -e "${GREEN}  ✓ Test database updated${NC}"

    # Apply to prod database
    echo ""
    echo -e "${BLUE}[4/4] Applying to PROD database...${NC}"
    if [ -n "$PROD_DB_URL" ]; then
        export DATABASE_URL="$PROD_DB_URL"
        alembic upgrade head

        if [ $? -ne 0 ]; then
            echo -e "${RED}✗ Migration failed on prod database${NC}"
            echo -e "${YELLOW}  Test database was updated, but prod failed${NC}"
            deactivate 2>/dev/null || true
            cd "$JH_ROOT" || return 1
            return 1
        fi
        echo -e "${GREEN}  ✓ Prod database updated${NC}"
    else
        echo -e "${YELLOW}  ⊘ Skipped (DATABASE_URL_PROD_VALUE not configured)${NC}"
    fi

    echo ""
    echo -e "${GREEN}=== Migration complete ===${NC}"

    deactivate 2>/dev/null || true
    cd "$JH_ROOT" || return 1
}

# Show help on load
echo -e "${GREEN}Job Hunter dev shortcuts loaded!${NC} Type ${BLUE}jhelp${NC} for commands."
# Deploy backend to AWS Lambda via SAM
jpushapi() {
    echo -e "${BLUE}=== Deploying Backend to AWS ===${NC}"
    echo ""

    # Step 1: Check git status - ensure clean state (MUST commit or exit)
    echo -e "${BLUE}[1/7] Checking git status (must have clean state)...${NC}"
    cd "$JH_ROOT" || return 1

    CURRENT_BRANCH=$(git branch --show-current)
    echo -e "${BLUE}  Current branch: ${YELLOW}$CURRENT_BRANCH${NC}"

    # Check for uncommitted changes in backend/ (including untracked files)
    BACKEND_CHANGES=$(git status --porcelain backend/ 2>/dev/null)
    if [ -z "$BACKEND_CHANGES" ]; then
        echo -e "${GREEN}  ✓ No uncommitted backend/ changes${NC}"
    else
        echo -e "${RED}  ✗ You have uncommitted backend/ changes${NC}"
        git status --short backend/ | sed 's/^/    /'
        echo ""
        echo -e "${YELLOW}Deployment requires a clean git state.${NC}"
        echo -n -e "${YELLOW}Commit backend/ changes now? [y/n]: ${NC}"
        read COMMIT_CHOICE

        if [[ ! "$COMMIT_CHOICE" =~ ^[Yy]$ ]]; then
            echo -e "${RED}Deployment cancelled - commit changes first${NC}"
            cd "$JH_ROOT" || return 1
            return 1
        fi

        # Add backend changes
        echo -e "${BLUE}Adding backend/ changes...${NC}"
        git add backend/

        # Check if there are staged changes
        if git diff --cached --quiet; then
            echo -e "${YELLOW}  ⚠ No backend changes to commit${NC}"
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
            echo -e "${GREEN}✓ Changes committed${NC}"
        fi
    fi

    cd "$JH_ROOT/backend" || return 1

    # Step 2: Run codegen to ensure frontend schemas are synced
    echo ""
    echo -e "${BLUE}[2/8] Running codegen (backend -> frontend schemas)...${NC}"
    source venv/bin/activate

    python3 scripts/generate_tracking_schema.py
    CODEGEN_EXIT=$?

    deactivate 2>/dev/null || true

    if [ $CODEGEN_EXIT -eq 1 ]; then
        echo -e "${YELLOW}  Frontend schemas were updated${NC}"
        echo -e "${YELLOW}  These changes will be committed with the deployment${NC}"
        # Add frontend changes to git
        cd "$JH_ROOT" || return 1
        git add frontend/src/types/
        cd "$JH_ROOT/backend" || return 1
    elif [ $CODEGEN_EXIT -gt 1 ]; then
        echo -e "${RED}  ✗ Codegen failed${NC}"
        cd "$JH_ROOT" || return 1
        return 1
    fi

    # Step 3: Check Lambda environment variables
    echo ""
    echo -e "${BLUE}[3/8] Checking Lambda environment variables...${NC}"
    LAMBDA_VARS=$(aws lambda get-function --function-name JobHuntTrackerAPI --query 'Configuration.Environment.Variables' 2>/dev/null)

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ Lambda function found${NC}"
        echo ""

        # Compare each variable (using global BACKEND_CHECK)
        typeset -a VARS_TO_UPDATE=()
        for VAR_NAME in "${(@k)BACKEND_CHECK}"; do
            EXPECTED_VAL="${BACKEND_CHECK[$VAR_NAME]}"
            LAMBDA_VAL_RAW=$(echo "$LAMBDA_VARS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('$VAR_NAME', ''))")
            LAMBDA_VAL=$(_normalize_env_value "$LAMBDA_VAL_RAW")

            if [ -z "$LAMBDA_VAL" ]; then
                echo -e "${RED}  ✗ $VAR_NAME: NOT SET in Lambda${NC}"
                if [ -n "$EXPECTED_VAL" ]; then
                    echo -e "${YELLOW}    Will set to: $EXPECTED_VAL${NC}"
                    VARS_TO_UPDATE+=("$VAR_NAME")
                fi
            elif [ -z "$EXPECTED_VAL" ]; then
                echo -e "${YELLOW}  ⚠ $VAR_NAME: No PROD_VALUE in .env.local${NC}"
                echo -e "${BLUE}    Current: $LAMBDA_VAL${NC}"
            elif [ "$LAMBDA_VAL" = "$EXPECTED_VAL" ]; then
                echo -e "${GREEN}  ✓ $VAR_NAME (up to date)${NC}"
            else
                echo -e "${YELLOW}  ⚠ $VAR_NAME will be updated${NC}"
                echo -e "${YELLOW}    Current: $LAMBDA_VAL${NC}"
                echo -e "${YELLOW}    New:     $EXPECTED_VAL${NC}"
                VARS_TO_UPDATE+=("$VAR_NAME")
            fi
        done

        if [ ${#VARS_TO_UPDATE[@]} -gt 0 ]; then
            echo ""
            echo -e "${YELLOW}${#VARS_TO_UPDATE[@]} variable(s) will be updated on deployment${NC}"
        else
            echo ""
            echo -e "${GREEN}All environment variables are up to date${NC}"
        fi
    else
        echo -e "${YELLOW}  ⚠ Lambda function not found${NC}"
        echo -e "${YELLOW}    This appears to be the first deployment${NC}"
        echo ""
        echo -e "${BLUE}Will create Lambda with values from .env.local PROD_VALUE${NC}"
    fi

    # Step 4: Generate template.yaml and samconfig.toml
    echo ""
    echo -e "${BLUE}[4/8] Generating deployment configuration...${NC}"

    # Generate template.yaml (script prints status and returns exit code)
    python3 scripts/generate_template.py
    TEMPLATE_EXIT=$?
    if [ $TEMPLATE_EXIT -gt 2 ]; then
        echo -e "${RED}  ✗ Failed to generate template.yaml${NC}"
        cd "$JH_ROOT" || return 1
        return 1
    fi

    # Generate samconfig.toml (script prints status and returns exit code)
    python3 scripts/generate_samconfig.py
    SAMCONFIG_EXIT=$?
    if [ $SAMCONFIG_EXIT -gt 2 ]; then
        echo -e "${RED}  ✗ Failed to generate samconfig.toml${NC}"
        cd "$JH_ROOT" || return 1
        return 1
    fi

    # Check if either file was modified or created
    if [ $TEMPLATE_EXIT -ne 0 ] || [ $SAMCONFIG_EXIT -ne 0 ]; then
        echo ""
        echo -e "${YELLOW}Configuration files were updated. Review the changes above.${NC}"
        echo -n -e "${YELLOW}Do these changes look good? [y/n]: ${NC}"
        read CONFIG_OK

        if [[ ! "$CONFIG_OK" =~ ^[Yy]$ ]]; then
            echo -e "${RED}Configuration rejected - exiting${NC}"
            cd "$JH_ROOT" || return 1
            return 1
        fi

        # Commit the backend changes including generated files
        echo ""
        echo -e "${BLUE}Committing backend/ changes...${NC}"
        cd "$JH_ROOT" || return 1
        git add backend/

        if git diff --cached --quiet; then
            echo -e "${YELLOW}  ⚠ No backend changes to commit${NC}"
        else
            git commit -m "Auto-generated: Update deployment configuration (template.yaml/samconfig.toml)"
            if [ $? -ne 0 ]; then
                echo -e "${RED}✗ Commit failed${NC}"
                cd "$JH_ROOT/backend" || return 1
                return 1
            fi
            echo -e "${GREEN}✓ Changes committed${NC}"
        fi

        cd "$JH_ROOT/backend" || return 1
    fi

    # Step 5: Confirm deployment
    echo ""
    echo -e "${BLUE}[5/8] Deploy confirmation:${NC}"
    echo -n -e "${YELLOW}Deploy backend to AWS Lambda? [y/n]: ${NC}"
    read DEPLOY_CHOICE

    if [[ ! "$DEPLOY_CHOICE" =~ ^[Yy]$ ]]; then
        echo -e "${RED}Deployment cancelled by user${NC}"
        cd "$JH_ROOT" || return 1
        return 1
    fi

    # Step 6: Build with SAM
    echo ""
    echo -e "${BLUE}[6/8] Building with SAM...${NC}"

    # Clean up dev files that SAM doesn't exclude (hardcoded EXCLUDED_FILES doesn't include these)
    if [ -f "server.log" ]; then
        echo -e "${YELLOW}  Removing server.log (dev artifact)...${NC}"
        rm -f server.log
    fi

    sam build
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ SAM build failed${NC}"
        cd "$JH_ROOT" || return 1
        return 1
    fi
    echo -e "${GREEN}  ✓ Build successful${NC}"

    # Step 7: Deploy with SAM (uses samconfig.toml)
    echo ""
    echo -e "${BLUE}[7/8] Deploying to AWS...${NC}"
    sam deploy
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ SAM deploy failed${NC}"
        cd "$JH_ROOT" || return 1
        return 1
    fi
    echo -e "${GREEN}  ✓ Deploy successful${NC}"

    # Step 8: Verify deployment
    echo ""
    echo -e "${BLUE}[8/8] Verifying deployment...${NC}"

    # Get API Gateway URL
    API_URL=$(aws cloudformation describe-stacks --stack-name jh-backend-stack --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text 2>/dev/null)
    if [ -n "$API_URL" ]; then
        echo -e "${GREEN}  ✓ API URL: ${BLUE}$API_URL${NC}"
    else
        echo -e "${YELLOW}  ⚠ Could not retrieve API URL${NC}"
    fi

    # Get Worker Lambda name from stack outputs
    WORKER_NAME=$(aws cloudformation describe-stacks --stack-name jh-backend-stack --query 'Stacks[0].Outputs[?OutputKey==`WorkerFunctionName`].OutputValue' --output text 2>/dev/null)
    if [ -n "$WORKER_NAME" ] && [ "$WORKER_NAME" != "None" ]; then
        echo -e "${GREEN}  ✓ Worker Lambda: ${BLUE}$WORKER_NAME${NC}"
    else
        echo -e "${YELLOW}  ⚠ Worker Lambda not found in stack outputs${NC}"
    fi

    # Verify API Lambda environment variables
    echo -e "${BLUE}  API Lambda environment:${NC}"
    LAMBDA_VARS=$(aws lambda get-function --function-name JobHuntTrackerAPI --query 'Configuration.Environment.Variables' --output json 2>/dev/null)
    if [ $? -eq 0 ]; then
        for VAR_NAME in "${(@k)BACKEND_CHECK}"; do
            LAMBDA_VAL_RAW=$(echo "$LAMBDA_VARS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('$VAR_NAME', ''))")
            LAMBDA_VAL=$(_normalize_env_value "$LAMBDA_VAL_RAW")
            if [ -n "$LAMBDA_VAL" ]; then
                echo -e "${GREEN}    ✓ $VAR_NAME${NC}"
            else
                echo -e "${RED}    ✗ $VAR_NAME (missing)${NC}"
            fi
        done

        # Check WORKER_FUNCTION_NAME is set (API Lambda needs this to invoke worker)
        WORKER_FN=$(echo "$LAMBDA_VARS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('WORKER_FUNCTION_NAME', ''))")
        if [ -n "$WORKER_FN" ]; then
            echo -e "${GREEN}    ✓ WORKER_FUNCTION_NAME=${WORKER_FN}${NC}"
        else
            echo -e "${RED}    ✗ WORKER_FUNCTION_NAME (missing - async invoke won't work)${NC}"
        fi
    fi

    cd "$JH_ROOT" || return 1
    echo ""
    echo -e "${GREEN}=== Backend deployment complete ===${NC}"
    echo -e "${BLUE}API Endpoint: ${API_URL}${NC}"
}
