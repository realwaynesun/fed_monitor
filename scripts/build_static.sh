#!/bin/bash
# Build static dashboard
# Run this daily to keep data fresh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== Building Static Dashboard ==="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Fetch latest data from FRED (incremental)
echo "1. Fetching latest data from FRED..."
python scripts/fetch_data.py

# Export to JSON
echo ""
echo "2. Exporting data to JSON..."
python scripts/export_json.py

echo ""
echo "=== Build Complete ==="
echo ""
echo "Static files are in: $PROJECT_DIR/static/"
echo "  - index.html (dashboard)"
echo "  - data.json (data)"
echo ""
echo "To view locally:"
echo "  cd static && python3 -m http.server 8080"
echo "  Open http://localhost:8080"
echo ""
echo "To deploy: copy the 'static' folder to any web server"
