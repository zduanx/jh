# Development Shortcuts

Quick reference for `dev.sh` shortcuts - ultra-short commands!

## Setup

Load shortcuts in your terminal (required once per session):
```bash
source dev.sh
```

**Optional: Auto-load on terminal startup**
Add to your `~/.zshrc` or `~/.bashrc`:
```bash
# Auto-load jh dev shortcuts when in project directory
if [ -f ~/coding/jh/dev.sh ]; then
    source ~/coding/jh/dev.sh
fi
```

---

## Available Commands

### Start Services
```bash
jbe                # Start backend (foreground)
jfe                # Start frontend (foreground)
jbe-bg             # Start backend (background, survives terminal close)
jfe-bg             # Start frontend (background, survives terminal close)
```

### Stop Services
```bash
jkill-be           # Kill backend
jkill-fe           # Kill frontend
jkillall           # Kill both
```

### Utilities
```bash
jready             # Check all prerequisites (venv, deps, .env files, ports)
jstatus            # Check what's running
jhelp              # Show all commands
```

---

## Common Workflows

### First Time Setup Check
```bash
source dev.sh
jready             # Verify all prerequisites
# Fix any issues reported
jready             # Run again until all checks pass
```

### Quick Start (background processes)
```bash
source dev.sh
jready             # Optional: verify everything is ready
jbe-bg && jfe-bg   # Start both
jstatus            # Check status
```

### Quick Start (foreground - split terminals)
```bash
# Terminal 1
source dev.sh
jbe

# Terminal 2
source dev.sh
jfe
```

### Stop Everything
```bash
jkillall
```

### View Logs (background processes)
```bash
tail -f backend/server.log
tail -f frontend/server.log
```

---

## Benefits

✅ **No more `source venv/bin/activate` every time**
✅ **Background processes survive terminal close**
✅ **Easy process management** (`jh-kill-all` to clean up)
✅ **Status checking** (`jh-status` to see what's running)
✅ **Color-coded output** for better visibility

---

## Troubleshooting

**Commands not found?**
```bash
# Make sure you sourced the script
source dev.sh

# Verify shortcuts are loaded
jh-help
```

**Process won't start?**
```bash
# Check if port is already in use
jh-status

# Kill existing processes
jh-kill-all

# Try again
jh-start-be
```

**Background logs not showing?**
```bash
# Backend logs
tail -f backend/server.log

# Frontend logs
tail -f frontend/server.log
```
