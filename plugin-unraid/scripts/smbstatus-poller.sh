#!/bin/bash
# StreamFuse — Samba status poller for Unraid
#
# Runs continuously on the Unraid host, calling smbstatus --json every
# INTERVAL seconds and writing the result to a file that the StreamFuse
# backend container reads via a bind mount.
#
# AUTO-START ON BOOT
# ------------------
# Add ONE line to /boot/config/go (the Unraid startup script):
#
#   nohup /boot/config/custom/streamfuse-smbstatus-poller.sh >>/var/log/streamfuse-smbstatus.log 2>&1 &
#
# INSTALL
# -------
#   cp plugin-unraid/scripts/smbstatus-poller.sh /boot/config/custom/
#   chmod +x /boot/config/custom/streamfuse-smbstatus-poller.sh
#
# Then add the nohup line above to /boot/config/go and either reboot or
# run it manually once.

set -uo pipefail

PIDFILE="/var/run/streamfuse-smbstatus.pid"
OUT_DIR="/mnt/user/appdata/streamfuse/host-shared"
OUT="${OUT_DIR}/samba-status.json"
TMP="${OUT}.tmp"
INTERVAL=10   # seconds between polls — StreamFuse polls every ~30 s, 10 s is plenty

# ── Guard: prevent duplicate instances ───────────────────────────────────────
if [ -f "$PIDFILE" ]; then
  OLD_PID=$(cat "$PIDFILE" 2>/dev/null || true)
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "[StreamFuse] smbstatus poller already running (PID $OLD_PID). Exiting."
    exit 0
  fi
fi

echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE" "$TMP"' EXIT INT TERM

# ── Create output directory if missing ───────────────────────────────────────
mkdir -p "$OUT_DIR"

# Seed an empty-but-valid JSON so the container doesn't error on startup
# before the first successful smbstatus call.
if [ ! -f "$OUT" ]; then
  printf '{"sessions":{},"tcons":{},"open_files":{}}\n' > "$OUT"
fi

echo "[StreamFuse] smbstatus poller started (PID $$), writing to $OUT every ${INTERVAL}s"

# ── Main loop ─────────────────────────────────────────────────────────────────
while true; do
  # smbstatus exits 0 even when no sessions; it can fail if smbd is not running.
  # We intentionally do NOT use set -e here — a transient smbstatus failure
  # must not kill the loop.
  if smbstatus --json > "$TMP" 2>/dev/null; then
    # Atomic replace: readers never see a half-written file
    mv "$TMP" "$OUT"
  else
    # smbd may be temporarily unavailable; keep the last good snapshot
    rm -f "$TMP"
  fi
  sleep "$INTERVAL"
done
