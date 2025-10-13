#!/bin/bash

# Comprehensive cleanup and organization script
# Organizes all files into proper directories

set -e

echo "🧹 Starting repository cleanup and organization..."
echo ""

# Create necessary directories
echo "📁 Creating directory structure..."
mkdir -p docs/deployment
mkdir -p docs/guides
mkdir -p docs/archive
mkdir -p scripts/deployment
mkdir -p scripts/testing

# Move documentation files to docs/
echo "📄 Moving documentation files..."

# Keep these important docs
mv -f CHEAPER_ALTERNATIVES.md docs/deployment/ 2>/dev/null || true
mv -f CONTAINERIZATION_COMPLETE.md docs/deployment/ 2>/dev/null || true
mv -f GCP_DEPLOYMENT_GUIDE.md docs/deployment/ 2>/dev/null || true
mv -f GCP_QUICK_START.md docs/deployment/ 2>/dev/null || true
mv -f HOSTING_OPTIONS_COMPARISON.md docs/deployment/ 2>/dev/null || true
mv -f WATCHLIST_AND_SCAN_FIXES.md docs/guides/ 2>/dev/null || true
mv -f ARCHITECTURE.md docs/guides/ 2>/dev/null || true

# Archive old/redundant docs
mv -f CLEANUP_PLAN.md docs/archive/ 2>/dev/null || true
mv -f DEPLOYMENT_SUCCESS.md docs/archive/ 2>/dev/null || true
mv -f READY_TO_TEST.md docs/archive/ 2>/dev/null || true
mv -f SESSION_COMPLETE_SUMMARY.md docs/archive/ 2>/dev/null || true
mv -f QUICK_START.md docs/archive/ 2>/dev/null || true
mv -f SETUP_GUIDE.md docs/archive/ 2>/dev/null || true
mv -f CONTRIBUTING.md docs/archive/ 2>/dev/null || true
mv -f IMPLEMENTATION_COMPLETE.md docs/archive/ 2>/dev/null || true
mv -f SESSION_SUMMARY.md docs/archive/ 2>/dev/null || true
mv -f TEST_REPORT.md docs/archive/ 2>/dev/null || true
mv -f HOW_TRADING_WORKS.md docs/archive/ 2>/dev/null || true

# Move scripts to scripts/
echo "🔧 Moving scripts..."
mv -f deploy-digitalocean.sh scripts/deployment/ 2>/dev/null || true
mv -f deploy-gcp.sh scripts/deployment/ 2>/dev/null || true
mv -f quickstart.sh scripts/ 2>/dev/null || true
mv -f cleanup_docs.sh scripts/ 2>/dev/null || true

# Move test files to scripts/testing/
echo "🧪 Moving test files..."
mv -f check_prices.py scripts/testing/ 2>/dev/null || true
mv -f test_all_enhancements.py scripts/testing/ 2>/dev/null || true
mv -f test_all_fixes.py scripts/testing/ 2>/dev/null || true
mv -f test_claude_api.py scripts/testing/ 2>/dev/null || true
mv -f test_discord_commands.py scripts/testing/ 2>/dev/null || true
mv -f test_pltr_data.py scripts/testing/ 2>/dev/null || true
mv -f test_real_options_data.py scripts/testing/ 2>/dev/null || true
mv -f test_sentiment_enhanced.py scripts/testing/ 2>/dev/null || true
mv -f validate_everything.py scripts/testing/ 2>/dev/null || true

# Remove duplicate/temporary files
echo "🗑️  Removing temporary files..."
rm -f nohup.out 2>/dev/null || true
rm -f *.tmp 2>/dev/null || true
rm -f *.temp 2>/dev/null || true

# Clean up logs (keep directory)
echo "📋 Cleaning logs..."
rm -f logs/*.log 2>/dev/null || true
touch logs/.gitkeep

# Clean up data (keep directory)
echo "💾 Cleaning data..."
# Keep the database but remove temporary files
rm -f data/*.tmp 2>/dev/null || true
touch data/.gitkeep

# Make scripts executable
echo "⚙️  Setting permissions..."
chmod +x scripts/*.sh 2>/dev/null || true
chmod +x scripts/deployment/*.sh 2>/dev/null || true

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "📁 Directory structure:"
echo "  docs/"
echo "    ├── deployment/     (Deployment guides)"
echo "    ├── guides/         (Usage guides)"
echo "    └── archive/        (Old documentation)"
echo "  scripts/"
echo "    ├── deployment/     (Deployment scripts)"
echo "    └── testing/        (Test scripts)"
echo ""
echo "🎯 Ready for commit!"
