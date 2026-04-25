#!/bin/bash
# Deploy SMHI ODP Ulanzi features to Home Assistant Green
# Usage: ./deploy-to-ha.sh
# You'll be prompted for SSH password once

set -e  # Exit on error

HA_HOST="192.168.68.136"
HA_USER="root"
HA_PATH="/config/custom_components/smhi_odp"

echo "🚀 Deploying SMHI ODP to Home Assistant Green..."
echo "   Host: $HA_HOST"
echo ""
echo "📦 Copying all files in one operation (enter password once)..."
echo ""

# Use rsync to copy all files with one password prompt
rsync -avz --progress \
  --include='weather_icons.py' \
  --include='display_service.py' \
  --include='services.yaml' \
  --include='__init__.py' \
  --include='manifest.json' \
  --exclude='*' \
  custom_components/smhi_odp/ $HA_USER@$HA_HOST:$HA_PATH/

echo ""
echo "✅ Files deployed successfully!"
echo ""
echo "🔄 Restarting Home Assistant..."
echo ""

# Restart Home Assistant
ssh -o StrictHostKeyChecking=no $HA_USER@$HA_HOST "ha core restart"

echo ""
echo "✨ Deployment complete!"
echo ""
echo "⏳ Wait ~30 seconds for Home Assistant to restart, then check:"
echo "   • Developer Tools → Services"
echo "   • Look for: smhi_odp.generate_today_gif"
echo "   •           smhi_odp.generate_tomorrow_gif"
echo "   •           smhi_odp.generate_week_gif"
echo ""
