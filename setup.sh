#!/usr/bin/env bash
# ╔══════════════════════════════════════════════╗
# ║        Yuki Bot — Quick Setup Script         ║
# ╚══════════════════════════════════════════════╝

set -e

echo "🌸 Setting up Yuki Bot..."

# Check Python 3.11
if ! python3.11 --version &>/dev/null; then
    echo "❌ Python 3.11 not found. Install it first."
    exit 1
fi

# Create venv
python3.11 -m venv venv
echo "✅ Virtual environment created"

# Activate
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip -q

# Install dependencies
pip install -r requirements.txt
echo "✅ Dependencies installed"

# Copy env file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Created .env — fill in your values!"
fi

echo ""
echo "╔═══════════════════════════════════════╗"
echo "║  ✨ Yuki Bot is ready to launch~      ║"
echo "║                                       ║"
echo "║  1. Edit .env with your credentials  ║"
echo "║  2. Run: source venv/bin/activate    ║"
echo "║  3. Run: python -m yuki              ║"
echo "╚═══════════════════════════════════════╝"
