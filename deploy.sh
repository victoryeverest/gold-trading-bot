#!/bin/bash

# Deploy to GitHub Script
# Run this script after setting up your GitHub repository

echo "🚀 Gold Trading Bot - GitHub Deployment"
echo "========================================"
echo ""
echo "Instructions:"
echo "1. Create a new repository on GitHub named 'gold-trading-bot'"
echo "2. Copy your repository URL (e.g., https://github.com/YOUR_USERNAME/gold-trading-bot.git)"
echo "3. Run the following commands:"
echo ""
echo "   cd /home/z/my-project/gold-trading-bot"
echo "   git remote add origin https://github.com/YOUR_USERNAME/gold-trading-bot.git"
echo "   git push -u origin main"
echo ""
echo "Or use SSH:"
echo "   git remote add origin git@github.com:YOUR_USERNAME/gold-trading-bot.git"
echo "   git push -u origin main"
echo ""
echo "========================================"

# If you want to deploy directly, provide your GitHub username:
# USERNAME="your_username"
# git remote add origin https://github.com/$USERNAME/gold-trading-bot.git
# git push -u origin main
