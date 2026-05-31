#!/bin/bash
# SignBoard Pi first-boot provisioner.
# Modeled on Raspberry Pi Imager's generated firstrun.sh, extended to install
# a stage-2 systemd service that runs Comitup + kiosk install with network up.
#
# Invoked by cmdline.txt:
#   systemd.run=/boot/firmware/firstrun.sh
#   systemd.run_success_action=reboot
#   systemd.unit=kernel-command-line.target
#
# Expects these files in /boot/firmware/:
#   signboard.conf             — HOSTNAME, KIOSK_URL, HOME_WIFI_SSID, HOME_WIFI_PSK, etc.
#   signboard-stage2.sh        — stage 2 installer (copied to /usr/local/sbin/)
#   setup-kiosk.sh             — existing SignBoard kiosk installer
#
# Log: /boot/firmware/firstrun.log

set +e
exec > >(tee /boot/firmware/firstrun.log) 2>&1
echo "=== firstrun.sh started at $(date -u +%FT%TZ) ==="

# ---- Load config -------------------------------------------------------------
CONF=/boot/firmware/signboard.conf
# shellcheck source=/dev/null
[ -f "$CONF" ] && . "$CONF"
: "${HOSTNAME:=signboard-kiosk}"
: "${TIMEZONE:=America/New_York}"
: "${KEYMAP:=us}"
: "${WIFI_COUNTRY:=US}"

USER_NAME=admin
USER_HASH='$6$n3riBQr8gNbDvzcg$OXm/w2wowbJXxwHuW0pYHVqfAhfo.XJH93PL3HTMo8bpIVt0Qa2M3HG3D7g8M885k0wEMsYmRmCLK/TFD8UiV/'
SSH_PUBKEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIM2kHGj1KpdYP0dn8JRJ7Buchk8nvVwtkR4IsPCy13CO nickd@MacBook-Air.local'

# ---- 1. Hostname -------------------------------------------------------------
echo "[1] Setting hostname to $HOSTNAME..."
CURRENT_HOSTNAME=$(tr -d " \t\n\r" </etc/hostname)
if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
    /usr/lib/raspberrypi-sys-mods/imager_custom set_hostname "$HOSTNAME"
else
    echo "$HOSTNAME" >/etc/hostname
    sed -i "s/127.0.1.1.*$CURRENT_HOSTNAME/127.0.1.1\t$HOSTNAME/g" /etc/hosts
fi

# ---- 2. Create/rename user $USER_NAME (UID 1000) -----------------------------
echo "[2] Configuring user $USER_NAME..."
FIRSTUSER=$(getent passwd 1000 | cut -d: -f1)
FIRSTUSERHOME=$(getent passwd 1000 | cut -d: -f6)

# Set password via Pi OS's userconf-pi helper (also renames user to $USER_NAME)
if [ -f /usr/lib/userconf-pi/userconf ]; then
    /usr/lib/userconf-pi/userconf "$USER_NAME" "$USER_HASH"
else
    # Fallback: rename + chpasswd
    if [ -n "$FIRSTUSER" ] && [ "$FIRSTUSER" != "$USER_NAME" ]; then
        usermod -l "$USER_NAME" "$FIRSTUSER"
        usermod -m -d "/home/$USER_NAME" "$USER_NAME"
        groupmod -n "$USER_NAME" "$FIRSTUSER"
    fi
    [ -z "$FIRSTUSER" ] && useradd -m -u 1000 -s /bin/bash "$USER_NAME"
    echo "$USER_NAME:$USER_HASH" | chpasswd -e
    usermod -aG sudo,video,audio,plugdev,netdev,gpio,i2c,spi "$USER_NAME" 2>/dev/null || true
fi

# ---- 3. SSH ------------------------------------------------------------------
echo "[3] Enabling SSH + authorized key..."
FIRSTUSERHOME=$(getent passwd 1000 | cut -d: -f6)
if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
    /usr/lib/raspberrypi-sys-mods/imager_custom enable_ssh -k "$SSH_PUBKEY"
else
    install -o "$USER_NAME" -m 700 -d "$FIRSTUSERHOME/.ssh"
    install -o "$USER_NAME" -m 600 /dev/stdin "$FIRSTUSERHOME/.ssh/authorized_keys" <<<"$SSH_PUBKEY"
    systemctl enable ssh
fi

# ---- 4. WiFi (NetworkManager keyfile) ----------------------------------------
echo "[4] WiFi preseed..."
if [ -n "${HOME_WIFI_SSID:-}" ] && [ -n "${HOME_WIFI_PSK:-}" ]; then
    if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
        /usr/lib/raspberrypi-sys-mods/imager_custom set_wlan -c "$WIFI_COUNTRY" "$HOME_WIFI_SSID" "$HOME_WIFI_PSK" 2>/dev/null || true
    fi
    # Also drop an NM keyfile in case the helper above didn't handle NetworkManager
    NMDIR=/etc/NetworkManager/system-connections
    mkdir -p "$NMDIR"
    NMFILE="$NMDIR/signboard-preseed.nmconnection"
    cat >"$NMFILE" <<EOF
[connection]
id=signboard-preseed
type=wifi
autoconnect=true

[wifi]
mode=infrastructure
ssid=$HOME_WIFI_SSID

[wifi-security]
key-mgmt=wpa-psk
psk=$HOME_WIFI_PSK

[ipv4]
method=auto

[ipv6]
method=auto
EOF
    chmod 600 "$NMFILE"
    chown root:root "$NMFILE"
    # Unblock WiFi country
    if command -v raspi-config >/dev/null 2>&1; then
        raspi-config nonint do_wifi_country "$WIFI_COUNTRY" 2>/dev/null || true
    fi
    echo "  Preseeded SSID: $HOME_WIFI_SSID"
else
    echo "  No WiFi in signboard.conf — skipping preseed."
fi

# ---- 5. Locale / timezone / keymap -------------------------------------------
echo "[5] Locale/timezone/keymap..."
if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
    /usr/lib/raspberrypi-sys-mods/imager_custom set_keymap "$KEYMAP" 2>/dev/null || true
    /usr/lib/raspberrypi-sys-mods/imager_custom set_timezone "$TIMEZONE" 2>/dev/null || true
else
    ln -sf "/usr/share/zoneinfo/$TIMEZONE" /etc/localtime
    echo "$TIMEZONE" >/etc/timezone
    [ -f /etc/default/keyboard ] && sed -i "s/^XKBLAYOUT=.*/XKBLAYOUT=\"$KEYMAP\"/" /etc/default/keyboard
fi

# ---- 6. Install stage-2 systemd service --------------------------------------
echo "[6] Installing stage-2 service..."
if [ -f /boot/firmware/signboard-stage2.sh ]; then
    cp /boot/firmware/signboard-stage2.sh /usr/local/sbin/signboard-stage2.sh
    chmod +x /usr/local/sbin/signboard-stage2.sh
    cp /boot/firmware/setup-kiosk.sh /usr/local/sbin/setup-kiosk.sh 2>/dev/null || true
    chmod +x /usr/local/sbin/setup-kiosk.sh 2>/dev/null || true
    cp /boot/firmware/signboard.conf /etc/signboard.conf 2>/dev/null || true

    cat >/etc/systemd/system/signboard-stage2.service <<'EOF'
[Unit]
Description=SignBoard stage-2 installer (apt + kiosk setup)
After=network-online.target
Wants=network-online.target
ConditionPathExists=!/var/lib/signboard/stage2-done

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/signboard-stage2.sh
StandardOutput=append:/var/log/signboard-stage2.log
StandardError=append:/var/log/signboard-stage2.log
TimeoutStartSec=30min
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

    mkdir -p /etc/systemd/system/multi-user.target.wants
    ln -sf /etc/systemd/system/signboard-stage2.service \
        /etc/systemd/system/multi-user.target.wants/signboard-stage2.service
else
    echo "  WARN: /boot/firmware/signboard-stage2.sh missing — skipping stage-2 install"
fi

# ---- 7. Self-clean cmdline + firstrun.sh -------------------------------------
echo "[7] Cleaning up cmdline.txt..."
CMDLINE=/boot/firmware/cmdline.txt
[ -f "$CMDLINE" ] || CMDLINE=/boot/cmdline.txt
sed -i 's| systemd.run=[^ ]*||g; s| systemd.run_success_action=[^ ]*||g; s| systemd.unit=[^ ]*||g; s|init=/usr/lib/raspberrypi-sys-mods/firstboot ||g' "$CMDLINE"
rm -f /boot/firmware/firstrun.sh

echo "=== firstrun.sh finished at $(date -u +%FT%TZ) ==="
sync
exit 0
