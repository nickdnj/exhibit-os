#!/usr/bin/env bash
# Flash a Raspberry Pi OS Lite image to an SD card and inject ExhibitOS
# kiosk provisioning files so the Pi comes up headless with:
#   - admin user (password + SSH key)
#   - hostname from exhibitos.conf
#   - Comitup WiFi-AP-fallback provisioning
#   - Chromium kiosk autostart pointing at KIOSK_URL
#
# Works on macOS. Requires: xz, diskutil, sudo.
#
# Usage:
#   sudo bash build-sd.sh /dev/diskN path/to/raspios-lite.img.xz path/to/exhibitos.conf
#
# Example:
#   sudo bash build-sd.sh /dev/disk4 \
#       ~/Downloads/exhibitos-kiosk/raspios-lite.img.xz \
#       ~/Workspaces/exhibit-os/scripts/kiosk/configs/example.conf

set -euo pipefail

DISK="${1:-}"
IMAGE="${2:-}"
CONF="${3:-}"

die() { echo "ERROR: $*" >&2; exit 1; }

[ -n "$DISK" ]  || die "Missing target disk (e.g. /dev/disk4)"
[ -n "$IMAGE" ] || die "Missing image path (.img or .img.xz)"
[ -n "$CONF" ]  || die "Missing exhibitos.conf path"
[ -b "$DISK" ] || [ -c "$DISK" ] || die "$DISK is not a block device"
[ -f "$IMAGE" ] || die "$IMAGE not found"
[ -f "$CONF" ]  || die "$CONF not found"

# Safety: confirm target is external and not the system disk.
if [[ "$OSTYPE" == "darwin"* ]]; then
    INFO=$(diskutil info "$DISK" 2>/dev/null || true)
    echo "$INFO" | grep -qE "Removable Media:\s+Removable|Device Location:\s+External" \
        || die "$DISK is not flagged as external/removable. Aborting for safety."
    SIZE=$(echo "$INFO" | awk -F: '/Disk Size/ {print $2; exit}' | xargs)
    echo "Target: $DISK  ($SIZE)"
fi

SSH_PUB="${SSH_PUB:-$HOME/.ssh/id_ed25519.pub}"
[ -f "$SSH_PUB" ] || die "SSH public key $SSH_PUB not found"

ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
[ -n "$ADMIN_PASSWORD" ] || die "Set ADMIN_PASSWORD env var (will be hashed, not stored)"

echo
echo "=== About to ERASE $DISK and flash $IMAGE ==="
read -r -p "Type 'WIPE' to continue: " CONFIRM
[ "$CONFIRM" = "WIPE" ] || die "Aborted."

# Unmount
echo "Unmounting $DISK..."
diskutil unmountDisk "$DISK" || true

# Flash
RAW_DISK="${DISK/\/dev\/disk//dev/rdisk}"
echo "Flashing image (this takes a few minutes)..."
case "$IMAGE" in
    *.xz) xzcat "$IMAGE" | sudo dd of="$RAW_DISK" bs=4m status=progress ;;
    *)    sudo dd if="$IMAGE" of="$RAW_DISK" bs=4m status=progress ;;
esac
sync

# Re-mount to get boot partition
echo "Re-mounting to access boot partition..."
diskutil unmountDisk "$DISK" || true
diskutil mountDisk "$DISK"
BOOT_MNT=$(diskutil info "${DISK}s1" | awk -F: '/Mount Point/ {print $2; exit}' | xargs)
[ -n "$BOOT_MNT" ] && [ -d "$BOOT_MNT" ] || die "Could not locate boot mount for ${DISK}s1"
echo "Boot partition mounted at: $BOOT_MNT"

# Inject provisioning files
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Writing exhibitos.conf..."
cp "$CONF" "$BOOT_MNT/exhibitos.conf"

echo "Writing authorized SSH key..."
cp "$SSH_PUB" "$BOOT_MNT/exhibitos-authorized_keys"

echo "Hashing admin password..."
HASH=$(openssl passwd -6 "$ADMIN_PASSWORD")
printf '%s' "$HASH" >"$BOOT_MNT/exhibitos-user-password"

echo "Copying firstrun.sh..."
cp "$SCRIPT_DIR/firstrun.sh" "$BOOT_MNT/firstrun.sh"
chmod +x "$BOOT_MNT/firstrun.sh"

echo "Copying setup-kiosk.sh (existing Pi-side installer)..."
cp "$SCRIPT_DIR/../setup-kiosk.sh" "$BOOT_MNT/setup-kiosk.sh"
chmod +x "$BOOT_MNT/setup-kiosk.sh"

echo "Enabling SSH on first boot..."
touch "$BOOT_MNT/ssh"

echo "Hooking firstrun.sh into cmdline.txt..."
CMDLINE="$BOOT_MNT/cmdline.txt"
if ! grep -q "systemd.run=" "$CMDLINE"; then
    # Strip trailing newline, append run params, preserve single-line format
    CURRENT=$(tr -d '\n' <"$CMDLINE")
    printf '%s systemd.run=/boot/firmware/firstrun.sh systemd.run_success_action=reboot systemd.unit=kernel-command-line.target\n' \
        "$CURRENT" >"$CMDLINE"
fi

sync
echo
echo "Ejecting $DISK..."
diskutil eject "$DISK"

echo
echo "=== DONE ==="
echo "  1. Insert SD card into Pi Zero 2 W."
echo "  2. Power on. First boot installs Comitup + kiosk (takes ~5 min)."
echo "  3. If no WiFi detected, Pi will broadcast an "exhibitos-setup-XXXX" hotspot."
echo "     Connect from your phone, open http://10.41.0.1 or follow captive portal,"
echo "     enter WiFi credentials, Pi reboots into kiosk mode."
echo "  4. SSH access: ssh admin@<hostname>.local"
