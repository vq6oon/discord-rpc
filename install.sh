#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_DIR="$HOME/.config/systemd/user"

echo "[1/4] Installing dependencies..."

python -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install -r "$DIR/requirements.txt"

echo "[2/4] Creating systemd service..."

mkdir -p "$SERVICE_DIR"

cat > "$SERVICE_DIR/mcpe-discord-rpc.service" <<EOF
[Unit]
Description=Minecraft Bedrock Discord Rich Presence
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$DIR
ExecStart=$DIR/.venv/bin/python $DIR/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

echo "[3/4] Enabling service..."

systemctl --user daemon-reload
systemctl --user enable --now mcpe-discord-rpc.service

echo "[4/4] Installation complete!"
