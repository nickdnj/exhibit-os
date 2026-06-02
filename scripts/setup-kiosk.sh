#!/bin/bash
# ExhibitOS Pi Kiosk Setup Script
# Run on a fresh Raspberry Pi OS Lite installation
#
# Usage: sudo bash setup-kiosk.sh <exhibitos-url> <channel-slug>
# Example: sudo bash setup-kiosk.sh http://192.168.12.136:8100 office

set -e

EXHIBITOS_URL="${1:-http://192.168.12.136:8100}"
CHANNEL_SLUG="${2:-office}"
DISPLAY_URL="${EXHIBITOS_URL}/display/${CHANNEL_SLUG}"
PI_USER="${SUDO_USER:-pi}"

echo "============================================"
echo "  ExhibitOS Pi Kiosk Setup"
echo "  URL: ${DISPLAY_URL}"
echo "  User: ${PI_USER}"
echo "============================================"

# Step 1: Install minimal X11 + Chromium
echo "[1/7] Installing packages..."
apt-get update -qq
apt-get install -y -qq \
    xserver-xorg x11-xserver-utils xinit \
    chromium \
    unclutter \
    fonts-noto-color-emoji fonts-noto \
    curl \
    > /dev/null 2>&1
echo "  Done."

# Step 2: Create the kiosk startup script
echo "[2/7] Creating kiosk script..."
cat > /home/${PI_USER}/kiosk.sh << 'KIOSK_EOF'
#!/bin/bash
# ExhibitOS Kiosk - launched by systemd

EXHIBITOS_URL="__EXHIBITOS_URL__"
DISPLAY_URL="__DISPLAY_URL__"

# Wait for server to be reachable
until curl -s -o /dev/null -w '%{http_code}' "${EXHIBITOS_URL}/api/health" 2>/dev/null | grep -q "200"; do
    sleep 5
done

# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Hide cursor after 3 seconds idle
unclutter -idle 3 -root &

# Match window to actual screen size — kiosk alone doesn't fill without a WM
RES=$(xrandr --current 2>/dev/null | awk '/\*/ {print $1; exit}')
[ -z "$RES" ] && RES="1600x900"
W=${RES%x*}
H=${RES#*x}

# Pi Zero 2 W has 512MB RAM — these flags minimize Chromium's footprint
exec chromium \
    --no-memcheck \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-component-update \
    --disable-translate \
    --disable-features=TranslateUI,Translate \
    --check-for-update-interval=31536000 \
    --autoplay-policy=no-user-gesture-required \
    --window-position=0,0 \
    --window-size=${W},${H} \
    --disable-gpu-compositing \
    --disable-smooth-scrolling \
    --disable-background-networking \
    --disable-sync \
    --disk-cache-size=16777216 \
    --media-cache-size=16777216 \
    --renderer-process-limit=1 \
    "${DISPLAY_URL}"
KIOSK_EOF

# Replace placeholders
sed -i "s|__EXHIBITOS_URL__|${EXHIBITOS_URL}|g" /home/${PI_USER}/kiosk.sh
sed -i "s|__DISPLAY_URL__|${DISPLAY_URL}|g" /home/${PI_USER}/kiosk.sh
chmod +x /home/${PI_USER}/kiosk.sh
chown ${PI_USER}:${PI_USER} /home/${PI_USER}/kiosk.sh
echo "  Done."

# Step 3: Create systemd service
echo "[3/7] Creating systemd service..."
cat > /etc/systemd/system/exhibitos-kiosk.service << EOF
[Unit]
Description=ExhibitOS Kiosk Display
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${PI_USER}
Environment=DISPLAY=:0
ExecStart=/bin/bash /home/${PI_USER}/kiosk.sh
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
EOF
echo "  Done."

# Step 4: Configure auto-login to console + start X
echo "[4/7] Configuring auto-login..."
# .xinitrc launches the kiosk directly — no window manager needed for single-app display
cat > /home/${PI_USER}/.xinitrc << EOF
#!/bin/sh
exec /home/${PI_USER}/kiosk.sh
EOF
chmod +x /home/${PI_USER}/.xinitrc
chown ${PI_USER}:${PI_USER} /home/${PI_USER}/.xinitrc

# Auto-login via getty
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin ${PI_USER} --noclear %I \$TERM
EOF

# Start X on login
grep -q "startx" /home/${PI_USER}/.bash_profile 2>/dev/null || \
    echo '[[ -z $DISPLAY && $XDG_VTNR -eq 1 ]] && exec startx -- -nocursor' >> /home/${PI_USER}/.bash_profile
chown ${PI_USER}:${PI_USER} /home/${PI_USER}/.bash_profile 2>/dev/null || true
echo "  Done."

# Step 5: Disable screen blanking globally
echo "[5/7] Disabling screen blanking..."
# Console blanking
grep -q "consoleblank=0" /boot/cmdline.txt 2>/dev/null || \
    sed -i 's/$/ consoleblank=0/' /boot/cmdline.txt 2>/dev/null || \
    sed -i 's/$/ consoleblank=0/' /boot/firmware/cmdline.txt 2>/dev/null || true
echo "  Done."

# Step 6: Enable overlayfs (read-only root) for SD card protection
echo "[6/7] SD card protection..."
echo "  NOTE: Run 'sudo raspi-config' -> Performance -> Overlay File System -> Enable"
echo "  This makes the root filesystem read-only, preventing SD card corruption."
echo "  All writes go to a tmpfs overlay that's lost on reboot."
echo "  The ExhibitOS server stores all data, so the Pi needs no persistent storage."
echo ""

# Step 7: Configure watchdog
echo "[7/7] Configuring watchdog..."
# Enable hardware watchdog to reboot Pi if it hangs
if [ -f /boot/config.txt ]; then
    grep -q "dtparam=watchdog=on" /boot/config.txt || \
        echo "dtparam=watchdog=on" >> /boot/config.txt
elif [ -f /boot/firmware/config.txt ]; then
    grep -q "dtparam=watchdog=on" /boot/firmware/config.txt || \
        echo "dtparam=watchdog=on" >> /boot/firmware/config.txt
fi
echo "  Done."

# Enable the service
systemctl daemon-reload
systemctl enable exhibitos-kiosk.service

echo ""
echo "============================================"
echo "  Setup complete!"
echo ""
echo "  Display URL: ${DISPLAY_URL}"
echo "  Service: exhibitos-kiosk.service"
echo ""
echo "  Next steps:"
echo "  1. Reboot: sudo reboot"
echo "  2. The Pi will auto-login, start X, and"
echo "     launch Chromium pointed at ExhibitOS."
echo "  3. Enable overlayfs via raspi-config for"
echo "     SD card protection."
echo "============================================"
