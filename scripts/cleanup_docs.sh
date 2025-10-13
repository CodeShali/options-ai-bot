#!/bin/bash

echo "🧹 Starting documentation cleanup..."
echo ""

# Create directories
echo "📁 Creating organized directories..."
mkdir -p docs/guides
mkdir -p docs/reference
mkdir -p docs/deployment
mkdir -p docs/features
mkdir -p docs/archive

# Move files to organize
echo "📦 Moving files to organized structure..."

# Guides
mv HOW_TRADING_WORKS.md docs/guides/ 2>/dev/null && echo "  ✅ Moved HOW_TRADING_WORKS.md"
mv GREEKS_EXPLAINED.md docs/guides/ 2>/dev/null && echo "  ✅ Moved GREEKS_EXPLAINED.md"
mv STOCK_PRICE_CALCULATION_EXPLAINED.md docs/guides/ 2>/dev/null && echo "  ✅ Moved STOCK_PRICE_CALCULATION_EXPLAINED.md"
mv ANTHROPIC_SETUP_GUIDE.md docs/guides/ 2>/dev/null && echo "  ✅ Moved ANTHROPIC_SETUP_GUIDE.md"

# Reference
mv COMPLETE_DISCORD_COMMANDS_TEST.md docs/reference/ 2>/dev/null && echo "  ✅ Moved COMPLETE_DISCORD_COMMANDS_TEST.md"
mv QUICK_REFERENCE.md docs/reference/ 2>/dev/null && echo "  ✅ Moved QUICK_REFERENCE.md"
mv PRICE_FIX_CRITICAL.md docs/reference/ 2>/dev/null && echo "  ✅ Moved PRICE_FIX_CRITICAL.md"

# Deployment
mv CLOUD_DEPLOYMENT_GUIDE.md docs/deployment/ 2>/dev/null && echo "  ✅ Moved CLOUD_DEPLOYMENT_GUIDE.md"
mv DEPLOY_CHECKLIST.md docs/deployment/ 2>/dev/null && echo "  ✅ Moved DEPLOY_CHECKLIST.md"

# Features
mv WATCHLIST_IMPROVEMENTS.md docs/features/ 2>/dev/null && echo "  ✅ Moved WATCHLIST_IMPROVEMENTS.md"
mv FINAL_SUMMARY.md docs/features/ 2>/dev/null && echo "  ✅ Moved FINAL_SUMMARY.md"

# Archive historical
echo "📚 Archiving historical documents..."
mv PHASE2_COMPLETE.md docs/archive/ 2>/dev/null && echo "  ✅ Archived PHASE2_COMPLETE.md"
mv PHASE2_PLAN.md docs/archive/ 2>/dev/null && echo "  ✅ Archived PHASE2_PLAN.md"
mv PENDING_ITEMS_CHECKLIST.md docs/archive/ 2>/dev/null && echo "  ✅ Archived PENDING_ITEMS_CHECKLIST.md"

# Delete duplicates
echo "🗑️  Deleting duplicate/outdated files..."
rm -f CURRENT_STATUS.md && echo "  ✅ Deleted CURRENT_STATUS.md"
rm -f FINAL_STATUS.md && echo "  ✅ Deleted FINAL_STATUS.md"
rm -f FINAL_STATUS_READY_FOR_GIT.md && echo "  ✅ Deleted FINAL_STATUS_READY_FOR_GIT.md"
rm -f IMPLEMENTATION_STATUS.md && echo "  ✅ Deleted IMPLEMENTATION_STATUS.md"
rm -f SYSTEM_READY.md && echo "  ✅ Deleted SYSTEM_READY.md"
rm -f SESSION_SUMMARY.md && echo "  ✅ Deleted SESSION_SUMMARY.md"
rm -f FINAL_SUMMARY_AND_NEXT_STEPS.md && echo "  ✅ Deleted FINAL_SUMMARY_AND_NEXT_STEPS.md"
rm -f FINAL_VALIDATION_SUMMARY.md && echo "  ✅ Deleted FINAL_VALIDATION_SUMMARY.md"
rm -f TEST_REPORT.md && echo "  ✅ Deleted TEST_REPORT.md"
rm -f COMPLETE_TEST_REPORT.md && echo "  ✅ Deleted COMPLETE_TEST_REPORT.md"
rm -f VALIDATION_REPORT.md && echo "  ✅ Deleted VALIDATION_REPORT.md"
rm -f FINAL_VALIDATION_COMPLETE.md && echo "  ✅ Deleted FINAL_VALIDATION_COMPLETE.md"
rm -f TESTING_GUIDE.md && echo "  ✅ Deleted TESTING_GUIDE.md"
rm -f IMPLEMENTATION_COMPLETE.md && echo "  ✅ Deleted IMPLEMENTATION_COMPLETE.md"
rm -f DEPLOYMENT_COMPLETE.md && echo "  ✅ Deleted DEPLOYMENT_COMPLETE.md"
rm -f SENTIMENT_EXPLAINED.md && echo "  ✅ Deleted SENTIMENT_EXPLAINED.md"
rm -f SENTIMENT_ISSUES_AND_FIXES.md && echo "  ✅ Deleted SENTIMENT_ISSUES_AND_FIXES.md"
rm -f SENTIMENT_IMPROVEMENTS_COMPLETE.md && echo "  ✅ Deleted SENTIMENT_IMPROVEMENTS_COMPLETE.md"
rm -f NEW_SENTIMENT_IMPLEMENTATION.md && echo "  ✅ Deleted NEW_SENTIMENT_IMPLEMENTATION.md"
rm -f SENTIMENT_DATA_FLOW_ANALYSIS.md && echo "  ✅ Deleted SENTIMENT_DATA_FLOW_ANALYSIS.md"
rm -f ERRORS_FOUND.md && echo "  ✅ Deleted ERRORS_FOUND.md"
rm -f FIXES_APPLIED.md && echo "  ✅ Deleted FIXES_APPLIED.md"
rm -f ISSUES_FOUND_AND_FIXES.md && echo "  ✅ Deleted ISSUES_FOUND_AND_FIXES.md"
rm -f CLAUDE_INTEGRATION_COMPLETE.md && echo "  ✅ Deleted CLAUDE_INTEGRATION_COMPLETE.md"
rm -f REAL_OPTIONS_IMPLEMENTATION_COMPLETE.md && echo "  ✅ Deleted REAL_OPTIONS_IMPLEMENTATION_COMPLETE.md"
rm -f ALPACA_OPTIONS_REAL_DATA.md && echo "  ✅ Deleted ALPACA_OPTIONS_REAL_DATA.md"
rm -f AGGRESSIVE_TRADING_ANALYSIS.md && echo "  ✅ Deleted AGGRESSIVE_TRADING_ANALYSIS.md"
rm -f COMMANDS_DETAILED_ANALYSIS.md && echo "  ✅ Deleted COMMANDS_DETAILED_ANALYSIS.md"
rm -f DISCORD_COMMANDS_EXPLAINED.md && echo "  ✅ Deleted DISCORD_COMMANDS_EXPLAINED.md"
rm -f DISCORD_ENHANCEMENTS.md && echo "  ✅ Deleted DISCORD_ENHANCEMENTS.md"
rm -f SYSTEM_FLOW_AND_COSTS.md && echo "  ✅ Deleted SYSTEM_FLOW_AND_COSTS.md"
rm -f REAL_VS_MOCK_DATA.md && echo "  ✅ Deleted REAL_VS_MOCK_DATA.md"
rm -f PROJECT_OVERVIEW.md && echo "  ✅ Deleted PROJECT_OVERVIEW.md"

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "📊 Summary:"
echo "  Root .md files: $(ls -1 *.md 2>/dev/null | wc -l | tr -d ' ')"
echo "  Organized in /docs/: $(find docs -name "*.md" 2>/dev/null | wc -l | tr -d ' ')"
echo ""
echo "📁 Directory structure:"
tree docs -L 2 2>/dev/null || find docs -type d 2>/dev/null
