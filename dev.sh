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
    FRONTEND_CHAT_URL_PROD=$(grep "^# REACT_APP_CHAT_URL_PROD_VALUE=" "$JH_ROOT/frontend/.env.local" | cut -d= -f2- | tr -d '\n' | tr -d '\r')
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
    ["REACT_APP_CHAT_URL"]="$FRONTEND_CHAT_URL_PROD"
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

# Chat (Node.js) shortcuts - Phase 6
# Pass -d / --debug to enable verbose [agent] loop tracing (AGENT_DEBUG=1).
# Off by default so prod-shaped runs stay quiet; opt in for local debugging.
# Agent debug levels: -d/--debug = compact trace (1); -dd = ALSO dump the full
# message list sent to the model (2). Off by default (prod stays quiet).
_jbenode_debug_level() {
    case "$1" in
        -dd|--debug-messages) echo 2 ;;
        -d|--debug) echo 1 ;;
        *) echo 0 ;;
    esac
}

jbenode() {
    local agent_debug; agent_debug=$(_jbenode_debug_level "$1")
    cd "$JH_ROOT" || return 1
    echo -e "${BLUE}Starting chat (Node) server on port 8100$([ "$agent_debug" != 0 ] && echo " [agent debug=$agent_debug]")...${NC}"
    cd "$JH_ROOT/chat" || return 1
    AGENT_DEBUG="$agent_debug" node local.js
}

jbenode-bg() {
    local agent_debug; agent_debug=$(_jbenode_debug_level "$1")
    cd "$JH_ROOT" || return 1
    echo -e "${BLUE}Starting chat (Node) server in background$([ "$agent_debug" != 0 ] && echo " [agent debug=$agent_debug]")...${NC}"
    cd "$JH_ROOT/chat" || return 1
    AGENT_DEBUG="$agent_debug" nohup node local.js > "$JH_ROOT/chat/server.log" 2>&1 &
    echo -e "${GREEN}✓ Chat server started in background (PID: $!)${NC}"
    echo -e "${BLUE}Logs: tail -f $JH_ROOT/chat/server.log${NC}"
}

jkill-benode() {
    echo -e "${YELLOW}Killing chat Node server (port 8100)...${NC}"
    lsof -ti:8100 | xargs kill -9 2>/dev/null && echo -e "${GREEN}✓ Chat server stopped${NC}" || echo -e "${RED}No chat process found on port 8100${NC}"
}

# MCP server (Python, FastMCP) shortcuts - Phase 7B (HTTP transport, port 8001)
jbemcp() {
    cd "$JH_ROOT" || return 1
    echo -e "${BLUE}Starting MCP server (HTTP) on port 8001...${NC}"
    cd "$JH_ROOT/backend" || return 1
    source venv/bin/activate
    MCP_TRANSPORT=http MCP_PORT=8001 python -m mcp_server.server
}

jbemcp-bg() {
    cd "$JH_ROOT" || return 1
    echo -e "${BLUE}Starting MCP server (HTTP) in background on port 8001...${NC}"
    cd "$JH_ROOT/backend" || return 1
    source venv/bin/activate
    MCP_TRANSPORT=http MCP_PORT=8001 nohup python -m mcp_server.server > "$JH_ROOT/backend/mcp_server.log" 2>&1 &
    echo -e "${GREEN}✓ MCP server started in background (PID: $!)${NC}"
    echo -e "${BLUE}Logs: tail -f $JH_ROOT/backend/mcp_server.log${NC}"
}

jkill-bemcp() {
    echo -e "${YELLOW}Killing MCP server (port 8001)...${NC}"
    lsof -ti:8001 | xargs kill -9 2>/dev/null && echo -e "${GREEN}✓ MCP server stopped${NC}" || echo -e "${RED}No MCP process found on port 8001${NC}"
}

# MCP automated tests: tool logic + in-memory protocol + service-auth (Phase 7B).
# Needs TEST_DATABASE_URL in .env.local (same test DB as the db suite). No live
# Voyage call (embeddings are faked). Pass extra args, e.g. jbemcp-test -k auth.
jbemcp-test() {
    cd "$JH_ROOT/backend" || return 1
    source venv/bin/activate
    python -m pytest mcp_server/__tests__/ -v "$@"
}

# MCP Inspector: official interactive client to click through the tools by hand
# (https://github.com/modelcontextprotocol/inspector). Spawns the server over
# stdio — no port, no separate jbemcp needed. Requires npx (Node).
jbemcp-inspect() {
    cd "$JH_ROOT/backend" || return 1
    source venv/bin/activate
    echo -e "${BLUE}Launching MCP Inspector against the stdio server...${NC}"
    npx @modelcontextprotocol/inspector python -m mcp_server.server
}

# Chat health check
jchat-health() {
    echo -e "${BLUE}Chat health:${NC}"
    curl -s http://localhost:8100/health && echo ""
}

# Generate a JWT signed with the backend's SECRET_KEY (the real create_access_token).
# Used by jchat-test so chat auth can be tested without hand-copying a token.
jchat-token() {
    # Mint a JWT for chat testing. Defaults to user 18 — the test-DB user with
    # embedded jobs + resume (Phase 7A/7C grounding), so the agent's MCP tools
    # return real data. Override: jchat-token <user_id>
    local user_id="${1:-18}"
    cd "$JH_ROOT/backend" || return 1
    source venv/bin/activate 2>/dev/null
    JH_TOKEN_USER_ID="$user_id" python3 -c "
import os, sys; sys.path.insert(0, '.')
from auth.utils import create_access_token
uid = int(os.environ['JH_TOKEN_USER_ID'])
print(create_access_token({'user_id': uid, 'email': 'zduanx@gmail.com'}))
"
    deactivate 2>/dev/null || true
    cd "$JH_ROOT" >/dev/null || return 1
}

# Chat streaming test (timestamped) - proves events arrive incrementally.
# Targets local by default; use --aws (or CHAT_AWS_URL env) for the deployed Function URL.
# --debug snapshots the Redis session (via GET /session, same prod path) before+after.
# Auto-generates a JWT (via jchat-token) and sends it as a Bearer header.
# Message and session_id are REQUIRED.
# Usage: jchat-test [--aws] [--debug] "your message" <session_id>
jchat-test() {
    local base="http://localhost:8100"
    local label="LOCAL"
    local debug=0
    # Parse flags in any order.
    while [ "$1" = "--aws" ] || [ "$1" = "--debug" ]; do
        if [ "$1" = "--aws" ]; then
            base="$CHAT_AWS_URL"
            if [ -z "$base" ]; then
                base=$(aws cloudformation describe-stacks --stack-name jh-chat-stack --region us-east-1 \
                    --query "Stacks[0].Outputs[?OutputKey=='ChatFunctionUrl'].OutputValue" \
                    --output text 2>/dev/null)
            fi
            if [ -z "$base" ] || [ "$base" = "None" ]; then
                echo -e "${RED}Could not find chat Function URL. Deploy first (jpushchat) or set CHAT_AWS_URL.${NC}"
                return 1
            fi
            base="${base%/}"
            label="AWS"
        elif [ "$1" = "--debug" ]; then
            debug=1
        fi
        shift
    done
    local msg="$1"
    local sid="$2"
    if [ -z "$msg" ] || [ -z "$sid" ]; then
        echo -e "${RED}Usage: jchat-test [--aws] [--debug] \"your message\" <session_id>${NC}"
        echo -e "${YELLOW}  Both message and session_id are required.${NC}"
        return 1
    fi
    local token
    token=$(jchat-token)
    if [ -z "$token" ]; then
        echo -e "${RED}Failed to generate token (jchat-token). Is backend venv set up?${NC}"
        return 1
    fi

    if [ "$debug" = "1" ]; then
        echo -e "${YELLOW}── Redis session BEFORE turn ──${NC}"
        curl -s "${base}/session?session_id=${sid}" -H "Authorization: Bearer $token" | python3 -m json.tool 2>/dev/null || echo "(no session / parse error)"
    fi

    echo -e "${BLUE}Streaming /chat against ${label} (${base}) [session=$sid]... timestamps show incremental arrival${NC}"
    curl -sN -X POST "${base}/chat" \
        -H "Authorization: Bearer $token" \
        -d "{\"session_id\":\"$sid\",\"message\":\"$msg\"}" \
        | while IFS= read -r line; do echo "$(date +%H:%M:%S) | $line"; done

    if [ "$debug" = "1" ]; then
        echo -e "${YELLOW}── Redis session AFTER turn ──${NC}"
        curl -s "${base}/session?session_id=${sid}" -H "Authorization: Bearer $token" | python3 -m json.tool 2>/dev/null || echo "(no session / parse error)"
    fi
}

# Commit the WHOLE repo (all changes, tracked + untracked) and push.
# Usage: jgit --m "message" [--c]
#   --m "msg"  commit message (required; prompted if omitted and not --c)
#   --c        auto-confirm (no y/n prompt). With --m, runs non-interactively.
# Convenience for committing cross-cutting work (docs, dev.sh, configs) that the
# per-stack jpush* commands don't cover. Commits to the CURRENT branch.
jgit() {
    local AUTO_CONFIRM=false
    local FLAG_COMMIT_MSG=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --c) AUTO_CONFIRM=true; shift ;;
            --m) FLAG_COMMIT_MSG="$2"; shift 2 ;;
            *) echo -e "${YELLOW}  (ignoring unknown arg: $1)${NC}"; shift ;;
        esac
    done

    cd "$JH_ROOT" || return 1
    echo -e "${BLUE}=== jgit: commit + push whole repo ===${NC}"
    echo -e "${BLUE}  Branch: ${YELLOW}$(git branch --show-current)${NC}"

    # Nothing to do?
    if [ -z "$(git status --porcelain 2>/dev/null)" ]; then
        echo -e "${GREEN}  ✓ Working tree clean — nothing to commit${NC}"
        return 0
    fi

    echo -e "${BLUE}  Changes to be committed:${NC}"
    git status --short | sed 's/^/    /'

    # Require a commit message.
    local COMMIT_MSG="$FLAG_COMMIT_MSG"
    if [ -z "$COMMIT_MSG" ]; then
        if [ "$AUTO_CONFIRM" = true ]; then
            echo -e "${RED}  ✗ --c requires --m \"message\"${NC}"; return 1
        fi
        echo -n -e "${YELLOW}  Commit message: ${NC}"
        read COMMIT_MSG
        [ -z "$COMMIT_MSG" ] && { echo -e "${RED}  ✗ Commit message required${NC}"; return 1; }
    fi

    # Confirm.
    if [ "$AUTO_CONFIRM" = true ]; then
        echo -e "${GREEN}  --c: auto-confirming${NC}"
    else
        echo -n -e "${YELLOW}  Commit ALL of the above and push? [y/n]: ${NC}"
        read CONFIRM
        [[ ! "$CONFIRM" =~ ^[Yy]$ ]] && { echo -e "${RED}  Cancelled${NC}"; return 1; }
    fi

    git add -A || { echo -e "${RED}  ✗ git add failed${NC}"; return 1; }
    git commit -m "$COMMIT_MSG" || { echo -e "${RED}  ✗ commit failed${NC}"; return 1; }
    echo -e "${BLUE}  Pushing to origin $(git branch --show-current)...${NC}"
    git push origin "$(git branch --show-current)" || { echo -e "${RED}  ✗ push failed${NC}"; return 1; }
    echo -e "${GREEN}=== jgit complete ===${NC}"
}

# Deploy the chat Node Lambda (+ Function URL) via SAM.
# Chat has its OWN stack (jh-chat-stack) and template in chat/ — independent of
# the Python backend (jh-backend-stack). Deploying chat never touches the backend.
# Mirrors jpushapi's discipline (git clean-state check, confirm, build, deploy,
# verify), minus backend-only steps (Python codegen, template/env generation).
# Requires chat/samconfig.toml (cp from chat/samconfig.toml.example first).
jpushchat() {
    echo -e "${BLUE}=== Deploying Chat (Node) Lambda → jh-chat-stack ===${NC}"
    echo ""

    # Flags: --c (auto-confirm y/n prompts), --m "msg" (commit message).
    local AUTO_CONFIRM=false
    local FLAG_COMMIT_MSG=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --c) AUTO_CONFIRM=true; shift ;;
            --m) FLAG_COMMIT_MSG="$2"; shift 2 ;;
            *) echo -e "${YELLOW}  (ignoring unknown arg: $1)${NC}"; shift ;;
        esac
    done

    # Step 1: git clean-state check for chat/
    echo -e "${BLUE}[1/5] Checking git status (chat/ must be clean)...${NC}"
    cd "$JH_ROOT" || return 1
    echo -e "${BLUE}  Current branch: ${YELLOW}$(git branch --show-current)${NC}"
    CHAT_CHANGES=$(git status --porcelain chat/ 2>/dev/null)
    if [ -z "$CHAT_CHANGES" ]; then
        echo -e "${GREEN}  ✓ No uncommitted chat/ changes${NC}"
    else
        echo -e "${RED}  ✗ You have uncommitted chat/ changes${NC}"
        git status --short chat/ | sed 's/^/    /'
        echo ""
        if [ "$AUTO_CONFIRM" = true ]; then
            echo -e "${GREEN}  --c: auto-confirming commit${NC}"; COMMIT_CHOICE="y"
        else
            echo -n -e "${YELLOW}Commit chat/ changes now? [y/n]: ${NC}"
            read COMMIT_CHOICE
        fi
        if [[ ! "$COMMIT_CHOICE" =~ ^[Yy]$ ]]; then
            echo -e "${RED}Deployment cancelled - commit changes first${NC}"
            cd "$JH_ROOT" || return 1; return 1
        fi
        git add chat/
        if git diff --cached --quiet; then
            echo -e "${YELLOW}  ⚠ No chat changes to commit${NC}"
        else
            git status --short | grep "^[AM]" | sed 's/^/  /'
            if [ -n "$FLAG_COMMIT_MSG" ]; then
                COMMIT_MSG="$FLAG_COMMIT_MSG"
                echo -e "${GREEN}  --m: using commit message: ${COMMIT_MSG}${NC}"
            else
                echo -n -e "${YELLOW}Commit message: ${NC}"
                read COMMIT_MSG
            fi
            if [ -z "$COMMIT_MSG" ]; then
                echo -e "${RED}✗ Commit message required${NC}"; git reset >/dev/null 2>&1
                cd "$JH_ROOT" || return 1; return 1
            fi
            git commit -m "$COMMIT_MSG" || { echo -e "${RED}✗ Commit failed${NC}"; cd "$JH_ROOT"; return 1; }
            echo -e "${GREEN}✓ Changes committed${NC}"
        fi
    fi

    # Step 2: generate template.yaml + samconfig.toml from .sam-config / .env.local
    echo ""
    echo -e "${BLUE}[2/6] Generating deployment config (template.yaml + samconfig.toml)...${NC}"
    cd "$JH_ROOT/chat" || return 1
    python3 scripts/generate_template.py
    TEMPLATE_EXIT=$?
    if [ $TEMPLATE_EXIT -gt 2 ]; then
        echo -e "${RED}  ✗ Failed to generate template.yaml${NC}"; cd "$JH_ROOT"; return 1
    fi
    python3 scripts/generate_samconfig.py
    SAMCONFIG_EXIT=$?
    if [ $SAMCONFIG_EXIT -gt 2 ]; then
        echo -e "${RED}  ✗ Failed to generate samconfig.toml${NC}"; cd "$JH_ROOT"; return 1
    fi
    # If template.yaml changed/created, commit it (it's tracked; samconfig is gitignored).
    if [ $TEMPLATE_EXIT -ne 0 ]; then
        echo -e "${YELLOW}  template.yaml was updated — committing${NC}"
        cd "$JH_ROOT" || return 1
        git add chat/template.yaml
        git diff --cached --quiet || git commit -m "Auto-generated: update chat/template.yaml" >/dev/null 2>&1
        cd "$JH_ROOT/chat" || return 1
    fi

    # Step 3: confirm
    echo ""
    if [ "$AUTO_CONFIRM" = true ]; then
        echo -e "${GREEN}[3/6] --c: auto-confirming deploy${NC}"; DEPLOY_CHOICE="y"
    else
        echo -n -e "${YELLOW}[3/6] Deploy chat to AWS (jh-chat-stack)? [y/n]: ${NC}"
        read DEPLOY_CHOICE
    fi
    if [[ ! "$DEPLOY_CHOICE" =~ ^[Yy]$ ]]; then
        echo -e "${RED}Deployment cancelled by user${NC}"; cd "$JH_ROOT"; return 1
    fi

    # Step 4: build
    echo ""
    echo -e "${BLUE}[4/6] sam build...${NC}"
    [ -f server.log ] && rm -f server.log
    sam build || { echo -e "${RED}✗ sam build failed${NC}"; cd "$JH_ROOT"; return 1; }

    # Step 5: deploy
    echo ""
    echo -e "${BLUE}[5/6] sam deploy...${NC}"
    sam deploy || { echo -e "${RED}✗ sam deploy failed${NC}"; cd "$JH_ROOT"; return 1; }

    # Step 6: verify - print Function URL
    echo ""
    echo -e "${BLUE}[6/6] Verifying...${NC}"
    CHAT_URL=$(aws cloudformation describe-stacks --stack-name jh-chat-stack --region us-east-1 \
        --query "Stacks[0].Outputs[?OutputKey=='ChatFunctionUrl'].OutputValue" --output text 2>/dev/null)
    echo -e "${GREEN}  ✓ Chat Function URL: ${BLUE}$CHAT_URL${NC}"
    echo -e "${YELLOW}  Set CHAT_AWS_URL to the URL above (strip trailing slash), then: jchat-test --aws${NC}"
    cd "$JH_ROOT" || return 1
    echo ""
    echo -e "${GREEN}=== Chat deployment complete ===${NC}"
}

jkillall() {
    echo -e "${YELLOW}Killing all processes...${NC}"
    jkill-be
    jkill-fe
    jkill-benode
    jkill-bemcp
    # Extractor sandbox (Phase 8): force-remove any leftover trial containers AND
    # the sandbox image (next `jcompany` run rebuilds it fresh, ~30s).
    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        echo -e "${YELLOW}Killing extractor sandbox containers + image...${NC}"
        docker ps -aq --filter "ancestor=jh-extractor-sandbox" | xargs -r docker rm -f >/dev/null 2>&1
        docker rmi -f jh-extractor-sandbox >/dev/null 2>&1 \
            && echo -e "${GREEN}  ✓ sandbox image removed (rebuilds on next jcompany)${NC}" \
            || echo -e "${BLUE}  (no sandbox image to remove)${NC}"
    fi
}

# Ensure the extractor sandbox is READY: (1) Docker daemon running, (2) sandbox
# image built (Docker's build cache makes this instant if nothing changed, and
# rebuilds changed layers automatically). Run before jcompany; daemon stops on reboot.
# Usage: jdocker [--rebuild]   (--rebuild = from-scratch build, ignores the cache)
jdocker() {
    if ! command -v docker >/dev/null 2>&1; then
        echo -e "${RED}  ✗ Docker not installed${NC}"
        echo -e "${YELLOW}    Install: brew install --cask docker${NC}"
        return 1
    fi

    # 1) Daemon up?
    if docker info >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Docker daemon running${NC}"
    else
        echo -e "${BLUE}Starting Docker Desktop...${NC}"
        open -a Docker
        echo -ne "${BLUE}  waiting for daemon"
        local up=0
        for _ in $(seq 1 30); do
            if docker info >/dev/null 2>&1; then up=1; break; fi
            echo -ne "."; sleep 2
        done
        if [ "$up" = 1 ]; then
            echo -e "${NC}\n${GREEN}✓ Docker daemon ready${NC}"
        else
            echo -e "${NC}\n${YELLOW}⚠ daemon not ready after 60s — check Docker Desktop (may need a license click)${NC}"
            return 1
        fi
    fi

    # 2) Build the image. Docker's build CACHE handles staleness for us: if nothing
    # changed, this is ~instant (all layers cached); if the source changed, it rebuilds
    # the changed layers. So we just always build — no timestamp/hash bookkeeping needed.
    # `jdocker --rebuild` forces a from-scratch build (ignores the cache).
    local img="jh-extractor-sandbox"
    local backend="$JH_ROOT/backend"
    local nocache=""
    [ "${1:-}" = "--rebuild" ] && { nocache="--no-cache"; echo -e "${YELLOW}  --rebuild: building from scratch${NC}"; }

    echo -e "${BLUE}  building sandbox image ($img)...${NC}"
    ( cd "$backend" && docker build -q $nocache -f extractor_agent/sandbox/Dockerfile -t "$img" . ) \
        && echo -e "${GREEN}✓ sandbox image ready${NC}" \
        || { echo -e "${RED}  ✗ image build failed${NC}"; return 1; }
}

# Start ALL 3 backends in the background: FastAPI (8000), chat Node (8100), MCP (8001).
jbeall() {
    echo -e "${BLUE}Starting all backends in background (FastAPI 8000, chat 8100, MCP 8001)...${NC}"
    jbe-bg
    jbenode-bg
    jbemcp-bg
    echo -e "${GREEN}✓ All backends started. Stop with: jkillall${NC}"
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

    # Check chat (Node) server
    if lsof -ti:8100 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Chat server running${NC} on http://localhost:8100"
    else
        echo -e "${RED}✗ Chat server not running${NC}"
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

    if lsof -ti:8100 > /dev/null 2>&1; then
        echo -e "${YELLOW}  ⚠ Port 8100 (chat) already in use${NC}"
        echo -e "${YELLOW}    Run 'jkill-benode' to free it${NC}"
        PORT_ISSUES=$((PORT_ISSUES + 1))
    else
        echo -e "${GREEN}  ✓ Port 8100 (chat) available${NC}"
    fi

    # Node.js (chat service)
    if command -v node > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Node.js installed ($(node --version))${NC}"
    else
        echo -e "${RED}  ✗ Node.js not found (required for chat service)${NC}"
        ISSUES=$((ISSUES + 1))
    fi

    # Chat Redis (Upstash) connectivity
    if [ -f "$JH_ROOT/chat/.env.local" ] && [ -d "$JH_ROOT/chat/node_modules" ]; then
        REDIS_PING=$(cd "$JH_ROOT/chat" && node -e "
process.loadEnvFile('.env.local');
const { ping } = await import('./redis.js');
try { console.log(await ping()); } catch (e) { console.log('ERR:' + e.message); }
" 2>/dev/null)
        if [ "$REDIS_PING" = "PONG" ]; then
            echo -e "${GREEN}  ✓ Chat Redis (Upstash) reachable${NC}"
        else
            echo -e "${RED}  ✗ Chat Redis unreachable (${REDIS_PING:-no response})${NC}"
            ISSUES=$((ISSUES + 1))
        fi
    else
        echo -e "${YELLOW}  ⊘ Chat Redis check skipped (no chat/.env.local or node_modules)${NC}"
    fi

    # Docker (Phase 8 extractor-agent sandbox). OPTIONAL — only needed for the
    # extractor discovery agent, not the core app. So warn, don't fail.
    echo -e "${BLUE}[+] Docker sandbox (Phase 8 extractor agent — optional)...${NC}"
    if ! command -v docker > /dev/null 2>&1; then
        echo -e "${YELLOW}  ⊘ Docker not installed (only needed for the extractor agent)${NC}"
        echo -e "${YELLOW}    Install: brew install --cask docker${NC}"
    elif docker info > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Docker daemon running${NC}"
        if docker image inspect jh-extractor-sandbox > /dev/null 2>&1; then
            echo -e "${GREEN}  ✓ Sandbox image built (jh-extractor-sandbox)${NC}"
        else
            echo -e "${YELLOW}  ⊘ Sandbox image not built yet (auto-builds on first agent run)${NC}"
        fi
    else
        echo -e "${YELLOW}  ⚠ Docker installed but daemon not running${NC}"
        echo -e "${YELLOW}    Start: open -a Docker  (or: extractors_v2/cli.sh edocker)${NC}"
    fi

    # Summary
    echo ""
    echo -e "${BLUE}=== Summary ===${NC}"
    if [ $ISSUES -eq 0 ] && [ $PORT_ISSUES -eq 0 ]; then
        echo -e "${GREEN}✓ All checks passed! Ready to start development.${NC}"
        echo ""
        echo -e "${BLUE}Quick start:${NC}"
        echo -e "  ${YELLOW}jbe-bg && jfe-bg${NC}        # Start backend + frontend (background)"
        echo -e "  ${YELLOW}jbenode-bg${NC}             # Start chat Node server (background, port 8100)"
        echo -e "  ${YELLOW}jstatus${NC}                # Check what's running"
        echo -e "  ${YELLOW}jchat-test --debug \"q\" sid${NC}  # Test chat (streams + Redis before/after)"
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

    # Flags: --c (auto-confirm y/n prompts), --m "msg" (commit message).
    local AUTO_CONFIRM=false
    local FLAG_COMMIT_MSG=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --c) AUTO_CONFIRM=true; shift ;;
            --m) FLAG_COMMIT_MSG="$2"; shift 2 ;;
            *) echo -e "${YELLOW}  (ignoring unknown arg: $1)${NC}"; shift ;;
        esac
    done

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
        if [ "$AUTO_CONFIRM" = true ]; then
            echo -e "${GREEN}  --c: auto-confirming Vercel env update${NC}"; UPDATE_CHOICE="y"
        else
            echo -n -e "${YELLOW}Update Vercel with these values? [y/n]: ${NC}"
            read UPDATE_CHOICE
        fi

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
    if [ "$AUTO_CONFIRM" = true ]; then
        echo -e "${GREEN}  --c: auto-confirming git push${NC}"; DEPLOY_CHOICE="y"
    else
        echo -n -e "${YELLOW}Push frontend/ to git for Vercel CI/CD? [y/n]: ${NC}"
        read DEPLOY_CHOICE
    fi

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

            if [ -n "$FLAG_COMMIT_MSG" ]; then
                COMMIT_MSG="$FLAG_COMMIT_MSG"
                echo -e "${GREEN}  --m: using commit message: ${COMMIT_MSG}${NC}"
            else
                echo -n -e "${YELLOW}Commit message: ${NC}"
                read COMMIT_MSG
            fi

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
    echo "  jbenode            - Start chat Node server (foreground, port 8100)"
    echo "  jbe-bg             - Start backend (background, survives terminal close)"
    echo "  jfe-bg             - Start frontend (background, survives terminal close)"
    echo "  jbenode-bg         - Start chat Node server (background)"
    echo ""
    echo -e "${GREEN}Stop Services:${NC}"
    echo "  jkill-be           - Kill backend"
    echo "  jkill-fe           - Kill frontend"
    echo "  jkill-benode       - Kill chat Node server (port 8100)"
    echo "  jkillall           - Kill all (backend, frontend, chat)"
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
    echo "  jpushchat          - Deploy chat Node Lambda + Function URL (SAM)"
    echo "  jpushvercel        - Deploy frontend to Vercel (git CI/CD)"
    echo "  jenvcheck          - Verify environment variables (local vs deployed)"
    echo ""
    echo -e "${GREEN}Debugging:${NC}"
    echo "  js3get <s3_url>    - Download S3 object to stdout (raw/google/...)"
    echo "  js3url <s3_url>    - Generate presigned URL for S3 object"
    echo "  jchat-health       - Curl chat /health"
    echo "  jchat-token        - Generate a JWT (backend SECRET_KEY) for manual testing"
    echo "  jchat-test [--aws] [--debug] \"msg\" <session> - Stream chat (--debug snapshots Redis before/after)"
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

    # Also check PROD's version — test and prod normally move in lockstep, but if
    # they've diverged (e.g. a migration applied to one DB independently), checking
    # only test could silently skip prod. Only short-circuit if BOTH are at head.
    local PROD_CURRENT=""
    if [ -n "$PROD_DB_URL" ]; then
        DATABASE_URL="$PROD_DB_URL"
        PROD_CURRENT=$(alembic current 2>&1 | grep -oE '[a-f0-9]{12}' | head -1)
        export DATABASE_URL="$TEST_DB_URL"
    fi

    if [ "$CURRENT" = "$HEAD" ] && { [ -z "$PROD_DB_URL" ] || [ "$PROD_CURRENT" = "$HEAD" ]; }; then
        echo -e "${GREEN}  ✓ Already at latest migration (test + prod): $HEAD${NC}"
        echo -e "${YELLOW}  No migrations to apply${NC}"
        deactivate 2>/dev/null || true
        cd "$JH_ROOT" || return 1
        return 0
    fi

    echo -e "${YELLOW}  Head:         $HEAD${NC}"
    echo -e "${YELLOW}  Test current: ${CURRENT:-none}${NC}"
    [ -n "$PROD_DB_URL" ] && echo -e "${YELLOW}  Prod current: ${PROD_CURRENT:-none}${NC}"
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

    # Flags: --c (auto-confirm all y/n prompts), --m "msg" (commit message).
    # With both set, jpushapi runs fully non-interactively.
    local AUTO_CONFIRM=false
    local FLAG_COMMIT_MSG=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --c) AUTO_CONFIRM=true; shift ;;
            --m) FLAG_COMMIT_MSG="$2"; shift 2 ;;
            *) echo -e "${YELLOW}  (ignoring unknown arg: $1)${NC}"; shift ;;
        esac
    done

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
        if [ "$AUTO_CONFIRM" = true ]; then
            echo -e "${GREEN}  --c: auto-confirming commit${NC}"
            COMMIT_CHOICE="y"
        else
            echo -n -e "${YELLOW}Commit backend/ changes now? [y/n]: ${NC}"
            read COMMIT_CHOICE
        fi

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

            if [ -n "$FLAG_COMMIT_MSG" ]; then
                COMMIT_MSG="$FLAG_COMMIT_MSG"
                echo -e "${GREEN}  --m: using commit message: ${COMMIT_MSG}${NC}"
            else
                echo -n -e "${YELLOW}Commit message: ${NC}"
                read COMMIT_MSG
            fi

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
        if [ "$AUTO_CONFIRM" = true ]; then
            echo -e "${GREEN}  --c: auto-confirming config${NC}"
            CONFIG_OK="y"
        else
            echo -n -e "${YELLOW}Do these changes look good? [y/n]: ${NC}"
            read CONFIG_OK
        fi

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
    if [ "$AUTO_CONFIRM" = true ]; then
        echo -e "${GREEN}  --c: auto-confirming deploy${NC}"; DEPLOY_CHOICE="y"
    else
        echo -n -e "${YELLOW}Deploy backend to AWS Lambda? [y/n]: ${NC}"
        read DEPLOY_CHOICE
    fi

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

# ---------------------------------------------------------------------------
# Extractor-agent CLI (Phase 8) — expose the `e*` verbs from
# backend/extractors_v2/cli.sh as shell commands, so `source dev.sh` makes
# them available everywhere (edocker, eclean, elogo, elist, ejd).
# Each is a thin wrapper that runs the cli.sh dispatcher.
# ---------------------------------------------------------------------------
_JH_EXTRACTOR_CLI="$JH_ROOT/backend/extractors_v2/cli.sh"
for _verb in edocker eclean elogo elist ejd; do
    eval "${_verb}() { \"$_JH_EXTRACTOR_CLI\" ${_verb} \"\$@\"; }"
done
unset _verb

# Run the extractor-DISCOVERY agent for a company (Phase 8C/8D).
# Usage: jcompany <company> <careers_url>
#   The agent (host brain + Docker-sandboxed trials) discovers, prints step-by-step.
# Needs: ANTHROPIC_API_KEY (from backend/.env.local) + Docker running (edocker).
jcompany() {
    if [ $# -lt 2 ]; then
        echo -e "${YELLOW}Usage: jcompany [--d] <company> <careers_url>${NC}"
        echo -e "${YELLOW}  --d  also print the full thought + the trial code each step${NC}"
        return 1
    fi
    cd "$JH_ROOT/backend" || return 1
    source venv/bin/activate 2>/dev/null
    # The agent brain (host) needs ANTHROPIC_API_KEY. It lives in chat/.env.local
    # (the chat agent's key) — reuse it. Fall back to backend/.env.local if present.
    export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-$(grep '^ANTHROPIC_API_KEY=' "$JH_ROOT/chat/.env.local" 2>/dev/null | cut -d= -f2-)}"
    export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-$(grep '^ANTHROPIC_API_KEY=' .env.local 2>/dev/null | cut -d= -f2-)}"
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        echo -e "${YELLOW}  ANTHROPIC_API_KEY not found (checked chat/.env.local, backend/.env.local)${NC}"
    fi

    # Record the run to a gitignored log (the audit of what the agent did). The agent
    # already prints everything; we tee it to a file (ANSI colors stripped) for review.
    local company_label
    company_label=$(for a in "$@"; do case "$a" in --*) ;; *) echo "$a"; break;; esac; done)
    local runs_dir="$JH_ROOT/backend/extractor_agent/runs"
    mkdir -p "$runs_dir"
    local logfile="$runs_dir/${company_label:-run}-$(date +%Y%m%d-%H%M%S).log"

    # tee to console (colored) + logfile (ANSI stripped: color codes AND cursor/clear
    # sequences like \x1b[2K and \r). PIPESTATUS keeps python's rc.
    python -u -m extractor_agent.cli "$@" 2>&1 \
        | tee >(sed -E $'s/\x1b\\[[0-9;]*[a-zA-Z]//g; s/\r//g' > "$logfile")
    local rc=${pipestatus[1]:-${PIPESTATUS[0]:-0}}
    echo -e "${BLUE}  run log: ${logfile#$JH_ROOT/}${NC}"
    deactivate 2>/dev/null || true
    cd "$JH_ROOT" || return 1
    return $rc
}
