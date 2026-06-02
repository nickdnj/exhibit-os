# ExhibitOS Pi Kiosk Provisioning

Flash an SD card for a headless Raspberry Pi ExhibitOS kiosk. No monitor or
keyboard required — the Pi comes up, installs Comitup (WiFi AP fallback), runs
Chromium in kiosk mode against a configured URL, and is reachable over SSH.

## Files

| File | Role |
|---|---|
| `exhibitos.conf.example` | Per-device config template (hostname, URL, timezone) |
| `firstrun.sh` | Runs once on first Pi boot. Creates admin user, authorizes SSH key, sets hostname/locale, installs Comitup + kiosk packages, invokes `../setup-kiosk.sh`, cleans up, reboots. |
| `build-sd.sh` | macOS-side flasher. Writes the Pi OS image, mounts boot partition, injects config + scripts. |
| `configs/*.conf` | One config per deployment (lobby, gallery, infoage, …). Edit hostname + URL per site. |

## Usage (macOS)

### 1. Download Pi OS Lite 64-bit

```bash
mkdir -p ~/Downloads/exhibitos-kiosk
cd ~/Downloads/exhibitos-kiosk
curl -L -o raspios-lite.img.xz \
    https://downloads.raspberrypi.com/raspios_lite_arm64_latest
```

### 2. Pick the target disk

```bash
diskutil list external
```

Confirm the correct `/dev/diskN` — `build-sd.sh` will refuse to touch anything
that isn't flagged external/removable, but double-check.

### 3. Create a per-device config

```bash
cp exhibitos.conf.example configs/lobby.conf
# edit HOSTNAME + KIOSK_URL for this deployment
```

### 4. Flash

```bash
ADMIN_PASSWORD='SilverLemon72!' \
sudo bash build-sd.sh /dev/disk4 \
    ~/Downloads/exhibitos-kiosk/raspios-lite.img.xz \
    configs/lobby.conf
```

You'll be prompted to type `WIPE` as a safety confirmation. The script:

1. Flashes the image with `dd`
2. Mounts the boot partition
3. Writes `/boot/firmware/exhibitos.conf` (the per-device config)
4. Writes `/boot/firmware/exhibitos-authorized_keys` (your `~/.ssh/id_ed25519.pub`)
5. Writes `/boot/firmware/exhibitos-user-password` (hashed via `openssl passwd -6`)
6. Copies `firstrun.sh` + `setup-kiosk.sh` into `/boot/firmware/`
7. Appends `systemd.run=/boot/firmware/firstrun.sh …` to `cmdline.txt`
8. Ejects the card

### 5. Boot the Pi

1. Insert SD card, plug in power. First boot takes ~5 minutes.
2. **If WiFi is already reachable** (e.g. ethernet dongle, or if you pre-seeded
   WiFi via `custom.toml`), the Pi boots → installs packages → reboots → kiosk.
3. **If no WiFi is configured**, Comitup starts broadcasting a hotspot named
   `exhibitos-setup-XXXX`. Connect from your phone; a captive portal at
   `http://10.41.0.1` lets you pick a WiFi network and enter the password.
   Pi reconnects on the main network, continues install, reboots into kiosk.

### 6. Verify

```bash
ssh admin@exhibitos-lobby.local
systemctl status exhibitos-kiosk
journalctl -u exhibitos-kiosk -n 50
```

## Re-provisioning later

Comitup stays installed. If WiFi credentials change (or you move the Pi to a
new network, e.g. InfoAge), SSH in and:

```bash
sudo comitup-cli     # interactive: pick new SSID, enter password
# or
sudo nmcli device wifi connect <SSID> password <password>
```

If SSH is unreachable because WiFi is broken, Comitup automatically falls back
to the AP hotspot — reconnect from your phone and re-provision.

## Per-device config files

Commit one file per deployment to `configs/`:

```
configs/
├── lobby.conf       # HOSTNAME=exhibitos-lobby, KIOSK_URL=.../display/lobby
├── gallery.conf     # HOSTNAME=exhibitos-gallery, KIOSK_URL=.../display/gallery
└── infoage.conf     # future: museum kiosk
```

This keeps deployments reproducible: `git pull && sudo bash build-sd.sh …
configs/gallery.conf` reflashes an identical card.
