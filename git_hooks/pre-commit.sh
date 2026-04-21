#!/bin/sh
# Git Pre-commit Hook: Secret Detection Guard
# Prevents accidental commit of .env files and common API key patterns.

# Define sensitive patterns (regex)
SENSITIVE_PATTERNS="\.env$|\.key$|\.pem$|\.secret|api_key|secret_key|password_hash"

# List staged files that match the patterns
FILES=$(git diff --cached --name-only | grep -iE "$SENSITIVE_PATTERNS")

if [ -n "$FILES" ]; then
    echo " "
    echo "❌ [SECURITY BLOCKED]"
    echo "Attempting to commit potentially sensitive files/patterns:"
    echo "--------------------------------------------------------"
    echo "$FILES"
    echo "--------------------------------------------------------"
    echo "Aksi ini diblokir untuk mencegah kebocoran kredensial."
    echo "Jika ini adalah kesalahan, hapus file dari staging dengan:"
    echo "git reset HEAD <file>"
    echo " "
    exit 1
fi

echo "✅ Security check passed. Proceeding with commit..."
exit 0
