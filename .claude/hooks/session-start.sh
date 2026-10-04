#!/usr/bin/env bash
# SessionStart: stdout, oturum bağlamına eklenir.
# Yeni oturumda ve /compact sonrası devir notunu yeniden enjekte eder.
cd "$CLAUDE_PROJECT_DIR" || exit 0
F="docs/handoff/CURRENT.md"
if [ -f "$F" ]; then
  echo "=== DEVİR NOTU ($F) ==="
  cat "$F"
fi
echo ""
echo "=== GIT DURUMU ==="
git branch --show-current 2>/dev/null
git status --short 2>/dev/null | head -20
git log --oneline -5 2>/dev/null
exit 0
