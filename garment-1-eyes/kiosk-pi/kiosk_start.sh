#!/bin/bash

# 1. Wait for the Desktop and Network to settle
sleep 10

# 2. Set Environment for Bookworm (Wayland)
export WAYLAND_DISPLAY=wayland-0
export DISPLAY=:0

# 3. Prevent Chromium from showing "Crashed" or "Restore Pages" bars
sed -i 's/"exited_cleanly":false/"exited_cleanly":true/' ~/.config/chromium/Default/Preferences 2>/dev/null
sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/' ~/.config/chromium/Default/Preferences 2>/dev/null

# 4. Scan the network for the Camera Pi (Port 8000)
echo "Searching for Camera Pi..."
TARGET=""
while [ -z "$TARGET" ]; do
  SUBNET=$(hostname -I | awk '{print $1}' | cut -d. -f1-3)
  
  # Scan the network range for Port 8000
  TARGET=$(sudo nmap -T3 --max-retries 1 -p 8000 "$SUBNET.0/24" --open -oG - | grep "Host:" | awk '{print $2}' | head -n 1)
  
  if [ -z "$TARGET" ]; then
    echo "Camera Pi not found yet. Retrying in 5 seconds..."
    sleep 5
  fi
done

echo "Found Camera Pi at $TARGET! Launching Gallery..."

# 5. Launch Chromium in Kiosk Mode and restart if it crashes

# Kill any old instances once before starting
pkill -9 chromium 2>/dev/null

while true; do
  echo "Starting Chromium..."
  chromium --kiosk --noerrdialogs --disable-infobars --password-store=basic "http://$TARGET:8000"

  echo "Chromium exited or crashed. Restarting in 3 seconds..."
  sleep 3
done
