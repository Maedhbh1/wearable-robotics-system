#!/bin/bash

# Give the main kiosk script time to find the IP and launch first
sleep 60

while true; do
  # Check if reach wifi
  if ! ping -c 8.8.8.8 > /dev/null; then
    echo "Wi-Fi appears to be down. Attempting reconnect..."
    sudo nmcli radio wifi off
    sleep 2
    sudo nmcli radio wifi on
    sleep 10
  fi
 
  # Check if chromium is running
  if ! pgrep -x "chromium" > /dev/null
  then
    echo "Chromium is not running. Relaunching..."
    # Run your start script again to find the IP and open the browser
    /home/kiosk_start.sh &
  fi
  # Wait 10 seconds before checking again
  sleep 10
done
