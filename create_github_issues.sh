#!/bin/bash
# ============================================================
# Script untuk membuat GitHub Issues dari file markdown
# 
# CARA PAKAI:
# 1. Install gh CLI: brew install gh
# 2. Login: gh auth login
# 3. Jalankan script: chmod +x create_github_issues.sh && ./create_github_issues.sh
# ============================================================

set -e

REPO="kipotz1986/apex-trading-bot"
ISSUES_DIR="$(dirname "$0")/github-issues"
CREATED_COUNT=0
FAILED_COUNT=0

echo "🚀 APEX Trading Bot — GitHub Issue Creator"
echo "============================================"
echo "Repository: $REPO"
echo ""

# Check gh CLI
if ! command -v gh &> /dev/null; then
    echo "❌ gh CLI belum terinstall."
    echo "   Install: brew install gh"
    echo "   Login:   gh auth login"
    exit 1
fi

# Check auth
if ! gh auth status &> /dev/null 2>&1; then
    echo "❌ gh CLI belum login."
    echo "   Jalankan: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI authenticated"
echo ""

# Mapping epic files to their label, milestone, and issues
get_epic_meta() {
    local key="$1"
    case "$key" in
        "epic-01") echo "epic-1-foundation|Fase 1 — Foundation" ;;
        "epic-02") echo "epic-2-ai-provider|Fase 1 — Foundation" ;;
        "epic-03") echo "epic-3-market-data|Fase 1 — Foundation" ;;
        "epic-04") echo "epic-4-agents|Fase 2 — Brain" ;;
        "epic-05") echo "epic-5-orchestrator|Fase 2 — Brain" ;;
        "epic-06") echo "epic-6-copy-trading|Fase 2 — Brain" ;;
        "epic-07") echo "epic-7-execution|Fase 3 — Execution" ;;
        "epic-08") echo "epic-8-risk-management|Fase 3 — Execution" ;;
        "epic-09") echo "epic-9-self-learning|Fase 4 — Intelligence" ;;
        "epic-10") echo "epic-10-paper-trading|Fase 3 — Execution" ;;
        "epic-11") echo "epic-11-telegram|Fase 5 — Interface" ;;
        "epic-12") echo "epic-12-dashboard|Fase 5 — Interface" ;;
        "epic-13") echo "epic-13-backend-api|Fase 5 — Interface" ;;
        "epic-14") echo "epic-14-security|Fase 6 — Hardening" ;;
        "epic-15") echo "epic-15-deployment|Fase 6 — Hardening" ;;
    esac
}

# Create labels first
echo "📌 Creating labels..."
LABELS=(
    "epic-1-foundation:0e8a16:Epic 1 - Project Foundation"
    "epic-2-ai-provider:1d76db:Epic 2 - AI Provider"
    "epic-3-market-data:5319e7:Epic 3 - Market Data"
    "epic-4-agents:d93f0b:Epic 4 - Analyst Agents"
    "epic-5-orchestrator:c2e0c6:Epic 5 - Orchestrator"
    "epic-6-copy-trading:bfdadc:Epic 6 - Copy Trading"
    "epic-7-execution:d4c5f9:Epic 7 - Auto Execution"
    "epic-8-risk-management:f9d0c4:Epic 8 - Risk Management"
    "epic-9-self-learning:fef2c0:Epic 9 - Self Learning"
    "epic-10-paper-trading:c5def5:Epic 10 - Paper Trading"
    "epic-11-telegram:bfd4f2:Epic 11 - Telegram"
    "epic-12-dashboard:d4c5f9:Epic 12 - Dashboard"
    "epic-13-backend-api:e99695:Epic 13 - Backend API"
    "epic-14-security:f9d0c4:Epic 14 - Security"
    "epic-15-deployment:c2e0c6:Epic 15 - Deployment"
    "priority-critical:b60205:Priority Critical"
    "priority-high:d93f0b:Priority High"
    "priority-medium:fbca04:Priority Medium"
    "priority-low:0e8a16:Priority Low"
)

for label_info in "${LABELS[@]}"; do
    IFS=':' read -r name color desc <<< "$label_info"
    gh label create "$name" --color "$color" --description "$desc" --repo "$REPO" 2>/dev/null || true
done
echo "✅ Labels created"
echo ""

# Create milestones
echo "📌 Creating milestones..."
MILESTONES=(
    "Fase 1 — Foundation:Foundation setup and data services"
    "Fase 2 — Brain:Multi-agent AI core"
    "Fase 3 — Execution:Trading execution and risk management"
    "Fase 4 — Intelligence:Self-learning and RL"
    "Fase 5 — Interface:Dashboard and API"
    "Fase 6 — Hardening:Security and deployment"
)

for ms_info in "${MILESTONES[@]}"; do
    IFS=':' read -r title desc <<< "$ms_info"
    gh api repos/$REPO/milestones -f title="$title" -f description="$desc" -f state="open" 2>/dev/null || true
done
echo "✅ Milestones created"
echo ""

# Parse and create issues from each markdown file
echo "📝 Creating issues..."
echo ""

for md_file in "$ISSUES_DIR"/epic-*.md; do
    filename=$(basename "$md_file" .md)
    
    # Extract epic number (e.g., "01" from "epic-01-project-foundation")
    epic_num=$(echo "$filename" | grep -o 'epic-[0-9]*' | grep -o '[0-9]*' | sed 's/^0*//')
    epic_key="epic-$(printf '%02d' $epic_num)"
    
    meta=$(get_epic_meta "$epic_key")
    IFS='|' read -r epic_label milestone <<< "$meta"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📂 Processing: $filename"
    echo "   Label: $epic_label | Milestone: $milestone"
    
    # Create issues using python
    
    # Simpler approach: extract issues using python
    python3 -c "
import re
import subprocess
import sys
import time

with open('$md_file', 'r') as f:
    content = f.read()

# Split by task headers
tasks = re.split(r'(?=^## T-\d+\.\d+:)', content, flags=re.MULTILINE)

for task in tasks:
    if not task.strip() or not task.strip().startswith('## T-'):
        continue
    
    # Extract title
    lines = task.strip().split('\n')
    title_line = lines[0].replace('## ', '').strip()
    body = '\n'.join(lines[1:]).strip()
    
    # Remove the --- separator if present at the start
    body = re.sub(r'^---\s*', '', body).strip()
    
    print(f'  📋 Creating: {title_line}')
    
    try:
        result = subprocess.run(
            ['gh', 'issue', 'create',
             '--repo', '$REPO',
             '--title', title_line,
             '--body', body,
             '--label', '$epic_label',
             '--milestone', '$milestone'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            print(f'     ✅ Created: {url}')
        else:
            print(f'     ❌ Failed: {result.stderr.strip()}')
    except Exception as e:
        print(f'     ❌ Error: {e}')
    
    time.sleep(1)  # Rate limiting
" 2>&1
    
    echo ""
done

echo ""
echo "============================================"
echo "🎉 Done! All issues have been processed."
echo "   View at: https://github.com/$REPO/issues"
echo "============================================"
