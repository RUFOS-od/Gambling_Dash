#!/bin/bash
# Betclic Brand Pulse — BI Dashboard 2026
# OpinionWay Africa

set -e

echo "=== Betclic Brand Pulse — Business Intelligence Dashboard 2026 ==="
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -q

echo ""
echo "Starting dashboard..."
echo "Open http://localhost:8501 in your browser"
echo ""

python -m streamlit run app.py --server.port 8501
