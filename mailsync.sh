#!/bin/bash
#
# Manual Mail Sync Trigger Script (Bash)
# Usage: ./mailsync.sh <syncName>
# Example: ./mailsync.sh MyMailSync
#

# Configuration
API_URL="${MAILSYNC_API_URL:-http://localhost:5000}"
API_KEY="${MAILSYNC_API_KEY:-change-me-please}"

# Check arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 <syncName>"
    echo "Example: $0 MyMailSync"
    exit 1
fi

SYNC_NAME="$1"

echo "Triggering mail sync: $SYNC_NAME"
echo "API URL: $API_URL"
echo ""

# Make API request
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d "{\"syncName\": \"$SYNC_NAME\"}" \
    "$API_URL/sync")

# Extract HTTP status code and body
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

# Check response
if [ "$HTTP_CODE" -eq 200 ]; then
    echo "✓ Sync triggered successfully!"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    exit 0
else
    echo "✗ Sync failed (HTTP $HTTP_CODE)"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    exit 1
fi
