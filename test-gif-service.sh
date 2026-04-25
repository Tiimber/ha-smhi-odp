#!/bin/bash
# Test the GIF generation services and save output
# Usage: ./test-gif-service.sh [today|tomorrow|week]

SERVICE="${1:-tomorrow}"
HA_HOST="192.168.68.136"
HA_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIyNDRhODNhNzI5ZTI0ODI2YmQ2YjQ2NjEzNmE1YWQzYiIsImlhdCI6MTc3NzE1MzYxMCwiZXhwIjoyMDkyNTEzNjEwfQ.XNli503-H34afDMiRUzb8f_TtLGIvGJJakIbmKcRzDI"  # Add your long-lived access token here

if [ -z "$HA_TOKEN" ]; then
    echo "❌ Error: Please add your HA long-lived access token to this script"
    echo ""
    echo "To get a token:"
    echo "1. Go to HA → Your Profile (bottom left)"
    echo "2. Scroll to 'Long-Lived Access Tokens'"
    echo "3. Click 'Create Token'"
    echo "4. Copy the token and paste it in this script at line 6"
    exit 1
fi

echo "🧪 Testing smhi_odp.generate_${SERVICE}_gif..."
echo ""

# Call the service via REST API - use URL parameter for return_response
RESPONSE=$(curl -s -X POST \
  "http://${HA_HOST}:8123/api/services/smhi_odp/generate_${SERVICE}_gif?return_response=true" \
  -H "Authorization: Bearer ${HA_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{}')

# Check if response is valid JSON
if ! echo "$RESPONSE" | python3 -c "import sys, json; json.load(sys.stdin)" 2>/dev/null; then
    echo "❌ Invalid JSON response"
    echo "Response: $RESPONSE"
    exit 1
fi

# Extract gif_bytes from service_response wrapper
GIF_HEX=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); sr=data.get('service_response', {}); print(sr.get('gif_bytes', '') if isinstance(sr, dict) else '')")

if [ -z "$GIF_HEX" ]; then
    echo "❌ Failed to get GIF data"
    echo "Response: $RESPONSE"
    exit 1
fi

# Convert hex to binary and save
echo "$GIF_HEX" | xxd -r -p > "weather_${SERVICE}.gif"

echo "✅ GIF saved to: weather_${SERVICE}.gif"
echo "📊 Size: $(ls -lh weather_${SERVICE}.gif | awk '{print $5}')"
echo ""
echo "🖼️  Open with: open weather_${SERVICE}.gif"
echo ""
