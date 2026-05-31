#!/bin/bash
# SignBoard Pi first-boot provisioner — Stage 2.
#
# Runs as a oneshot systemd service on the FIRST boot where network is up.
# Installs Comitup (WiFi AP fallback) and the Chromium kiosk stack, then
# invokes the existing setup-kiosk.sh with the configured KIOSK_URL.
#
# Log: /var/log/signboard-stage2.log

set +e
echo "=== stage2 started at $(date -u +%FT%TZ) ==="

CONF=/boot/firmware/signboard.conf
KIOSK_INSTALLER=/boot/firmware/setup-kiosk.sh
DONE=/var/lib/signboard/stage2-done
mkdir -p "$(dirname "$DONE")"

# shellcheck source=/dev/null
. "$CONF"
: "${KIOSK_URL:=https://signboard.vistter.com/display/pool}"

# Wait for internet
for i in $(seq 1 30); do
    if curl -fsS --max-time 5 https://deb.debian.org/ >/dev/null 2>&1; then
        echo "Network reachable."
        NET_OK=1
        break
    fi
    echo "Waiting for network (${i}/30)..."
    sleep 5
done

if [ "${NET_OK:-0}" != "1" ]; then
    echo "ERROR: no network reachable — aborting stage 2. Will retry on next boot."
    exit 1
fi

# Wait for system clock to sync via NTP — Pi Zero has no RTC, and stale clock
# breaks APT signature verification with "Not live until ..." errors.
echo "Waiting for NTP time sync..."
for i in $(seq 1 24); do
    if timedatectl show --property=NTPSynchronized --value 2>/dev/null | grep -q yes; then
        echo "  Clock synchronized: $(date -u +%FT%TZ)"
        break
    fi
    echo "  Clock not yet synced (${i}/24)..."
    sleep 5
done

echo "Updating apt..."
apt-get update -qq

echo "Installing Comitup APT source..."
curl -fsSL -o /tmp/davesteele-comitup-apt-source.deb \
    https://davesteele.github.io/comitup/deb/davesteele-comitup-apt-source_1.3_all.deb
dpkg -i --force-all /tmp/davesteele-comitup-apt-source.deb
rm -f /tmp/davesteele-comitup-apt-source.deb
apt-get update -qq

echo "Installing Comitup + kiosk packages..."
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    comitup \
    xserver-xorg x11-xserver-utils xinit \
    chromium \
    unclutter \
    curl ca-certificates

echo "Running setup-kiosk.sh..."
if [ -x "$KIOSK_INSTALLER" ]; then
    BASE=$(echo "$KIOSK_URL" | sed -E 's|/display/[^/]+/?$||')
    SLUG=$(echo "$KIOSK_URL" | sed -E 's|.*/display/([^/?#]+).*|\1|')
    SUDO_USER=admin bash "$KIOSK_INSTALLER" "$BASE" "$SLUG" || echo "(setup-kiosk.sh non-zero)"
else
    echo "WARN: $KIOSK_INSTALLER missing."
fi

echo "=== stage2 finished at $(date -u +%FT%TZ) ==="
touch "$DONE"

# Disable ourselves
systemctl disable signboard-stage2.service 2>/dev/null || true

# Reboot into kiosk
(sleep 5 && reboot) &
exit 0
