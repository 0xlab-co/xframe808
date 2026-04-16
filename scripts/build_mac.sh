#!/bin/bash
# macOS 本機打包腳本
# 使用前請先建立虛擬環境：
#   python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt pyinstaller

set -e

cd "$(dirname "$0")/.."

pyinstaller --noconfirm --onedir --windowed \
  --name "xFRAME808" \
  --osx-bundle-identifier "com.0xlab.xframe808" \
  main.py

cd dist
ditto -c -k --sequesterRsrc --keepParent "xFRAME808.app" "xFRAME808-macOS.zip"

echo ""
echo "Build complete:"
echo "  App:  dist/xFRAME808.app"
echo "  ZIP:  dist/xFRAME808-macOS.zip"
