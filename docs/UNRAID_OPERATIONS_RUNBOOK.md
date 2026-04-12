# StreamFuse Unraid Operations Runbook

This runbook documents the operational scripts and commands used in production on Unraid for:
- Samba ingestion (`smbstatus --json` -> StreamFuse)
- SFTPGo ingestion support and diagnostics
- System/Unraid metrics (`System Health`, `Total Shared`, `Total Bandwidth`)
- Persistence across reboots and troubleshooting

All paths and commands here are intended for Unraid shell (`root@NAS`).

## 1) Required data paths

Create these paths once:

```bash
mkdir -p /mnt/user/appdata/streamfuse/data
mkdir -p /mnt/user/appdata/streamfuse/scripts
```

`/mnt/user/appdata/streamfuse/data` is mounted into backend container as `/data`.

## 2) Samba collector script

Purpose: generate `samba-status.json` periodically from `smbstatus --json`.

Create script:

```bash
cat >/mnt/user/appdata/streamfuse/scripts/streamfuse-smbstatus-loop.sh <<'EOF'
#!/bin/bash
set -euo pipefail

OUT="/mnt/user/appdata/streamfuse/data/samba-status.json"
TMP="${OUT}.tmp"

while true; do
  if smbstatus --json > "$TMP" 2>/dev/null; then
    mv "$TMP" "$OUT"
  fi
  sleep 5
done
EOF

chmod +x /mnt/user/appdata/streamfuse/scripts/streamfuse-smbstatus-loop.sh
```

Run now:

```bash
pkill -f streamfuse-smbstatus-loop.sh || true
nohup /mnt/user/appdata/streamfuse/scripts/streamfuse-smbstatus-loop.sh >/var/log/streamfuse-smbstatus.log 2>&1 &
```

Verify:

```bash
ls -lh /mnt/user/appdata/streamfuse/data/samba-status.json
tail -n 20 /var/log/streamfuse-smbstatus.log
```

## 3) Unraid metrics collector script (System Health)

Purpose: generate `/data/unraid-metrics.json` for dashboard system cards and optional totals override.

Create script:

```bash
cat >/mnt/user/appdata/streamfuse/scripts/unraid-metrics-loop.sh <<'EOF'
#!/bin/bash
set -euo pipefail

OUT="/mnt/user/appdata/streamfuse/data/unraid-metrics.json"
STATE="/mnt/user/appdata/streamfuse/data/.unraid-metrics.state"
IFACE="${1:-bond0}"

if [ ! -d "/sys/class/net/$IFACE" ]; then
  IFACE="$(ip route | awk '/default/ {print $5; exit}')"
fi

cpu_model="$(awk -F: '/model name/ {gsub(/^ +/,"",$2); print $2; exit}' /proc/cpuinfo || true)"
ram_total_kb="$(awk '/MemTotal:/ {print $2}' /proc/meminfo || echo 0)"

gpu_model=""
if command -v nvidia-smi >/dev/null 2>&1; then
  gpu_model="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1 || true)"
fi

while true; do
  now_epoch="$(date +%s)"
  rx="$(cat /sys/class/net/$IFACE/statistics/rx_bytes 2>/dev/null || echo 0)"
  tx="$(cat /sys/class/net/$IFACE/statistics/tx_bytes 2>/dev/null || echo 0)"

  cpu_line="$(awk '/^cpu / {print $2,$3,$4,$5,$6,$7,$8,$9,$10,$11; exit}' /proc/stat)"
  idle_now="$(echo "$cpu_line" | awk '{print $4+$5}')"
  total_now="$(echo "$cpu_line" | awk '{s=0; for(i=1;i<=NF;i++) s+=$i; print s}')"

  ram_avail_kb="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo || echo 0)"
  ram_total_bytes=$((ram_total_kb * 1024))
  ram_free_bytes=$((ram_avail_kb * 1024))
  ram_used_bytes=$((ram_total_bytes - ram_free_bytes))

  if [ -f "$STATE" ]; then
    read -r prev_t prev_rx prev_tx prev_idle prev_total < "$STATE" || true
  else
    prev_t="$now_epoch"; prev_rx="$rx"; prev_tx="$tx"; prev_idle="$idle_now"; prev_total="$total_now"
  fi

  dt=$((now_epoch - prev_t)); [ "$dt" -le 0 ] && dt=1
  drx=$((rx - prev_rx)); [ "$drx" -lt 0 ] && drx=0
  dtx=$((tx - prev_tx)); [ "$dtx" -lt 0 ] && dtx=0

  inbound_bps=$((drx * 8 / dt))
  outbound_bps=$((dtx * 8 / dt))
  total_bandwidth_bps=$((inbound_bps + outbound_bps))

  didle=$((idle_now - prev_idle)); [ "$didle" -lt 0 ] && didle=0
  dtotal=$((total_now - prev_total)); [ "$dtotal" -le 0 ] && dtotal=1
  cpu_percent="$(awk -v di="$didle" -v dt="$dtotal" 'BEGIN { printf "%.2f", (1 - di/dt)*100 }')"

  gpu_percent="0"
  power_watts="null"
  if command -v nvidia-smi >/dev/null 2>&1; then
    gpu_percent="$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -n1 || echo 0)"
    p="$(nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits 2>/dev/null | head -n1 || true)"
    [ -n "$p" ] && power_watts="$p"
  fi

  timestamp="$(date -Iseconds)"
  tmp="${OUT}.tmp"

  cat > "$tmp" <<JSON
{
  "timestamp": "$timestamp",
  "cpu_model": "$cpu_model",
  "gpu_model": "$gpu_model",
  "ram_total_bytes": $ram_total_bytes,
  "ram_used_bytes": $ram_used_bytes,
  "ram_free_bytes": $ram_free_bytes,
  "cpu_percent": $cpu_percent,
  "gpu_percent": $gpu_percent,
  "network": {
    "inbound_bps": $inbound_bps,
    "outbound_bps": $outbound_bps
  },
  "power_watts": $power_watts,
  "total_shared_bytes": $tx,
  "total_bandwidth_bps": $total_bandwidth_bps
}
JSON

  mv "$tmp" "$OUT"
  echo "$now_epoch $rx $tx $idle_now $total_now" > "$STATE"
  sleep 2
done
EOF

chmod +x /mnt/user/appdata/streamfuse/scripts/unraid-metrics-loop.sh
```

Run now:

```bash
pkill -f unraid-metrics-loop.sh || true
nohup /mnt/user/appdata/streamfuse/scripts/unraid-metrics-loop.sh bond0 >/var/log/streamfuse-metrics.log 2>&1 &
```

Verify:

```bash
tail -n 20 /var/log/streamfuse-metrics.log
cat /mnt/user/appdata/streamfuse/data/unraid-metrics.json
```

## 4) StreamFuse Settings values (UI)

In `Settings` page:

- `SFTPGo Logs Path`: path inside backend container (example `/data/transfers-tail.jsonl` if you generate it there)
- `SFTPGo Path Mappings`:
  - `/multimedia/peliculas:/peliculas`
  - `/multimedia/series:/series`
- `Enable Samba ingestion`: `ON`
- `Samba Status JSON Path`: `/data/samba-status.json`
- `Enable Unraid metrics integration`: `ON`
- `Unraid metrics JSON path`: `/data/unraid-metrics.json`
- `Use Unraid totals for Total Shared and Total Bandwidth`: `ON` (optional)

## 5) Manual poll and verification APIs

From Windows PowerShell:

```powershell
Invoke-RestMethod -Method POST -Uri "http://192.168.0.111:8000/api/v1/internal/samba/poll"
Invoke-RestMethod -Method POST -Uri "http://192.168.0.111:8000/api/v1/internal/sftpgo/poll"
Invoke-RestMethod -Method GET  -Uri "http://192.168.0.111:8000/api/v1/system/metrics"
Invoke-RestMethod -Method GET  -Uri "http://192.168.0.111:8000/api/v1/sessions/active"
```

If auth is enabled, include Bearer token in headers.

## 6) Persist scripts after reboot

Append to `/boot/config/go`:

```bash
grep -q "streamfuse-smbstatus-loop.sh" /boot/config/go || \
  echo "nohup /mnt/user/appdata/streamfuse/scripts/streamfuse-smbstatus-loop.sh >/var/log/streamfuse-smbstatus.log 2>&1 &" >> /boot/config/go

grep -q "unraid-metrics-loop.sh" /boot/config/go || \
  echo "nohup /mnt/user/appdata/streamfuse/scripts/unraid-metrics-loop.sh bond0 >/var/log/streamfuse-metrics.log 2>&1 &" >> /boot/config/go
```

## 7) Common troubleshooting

### Script not executable / permission denied

```bash
chmod +x /mnt/user/appdata/streamfuse/scripts/*.sh
ls -l /mnt/user/appdata/streamfuse/scripts
```

### File not found from StreamFuse

Check host path exists:

```bash
ls -lh /mnt/user/appdata/streamfuse/data
```

Then verify container mapping (`/data/...`) in compose.

### Samba noise from directory browsing

StreamFuse only considers media file extensions and ignores non-media paths. Directory-only access should not create valid media sessions.

### SFTPGo logs path note

Current backend polling code uses provider path from env `STREAMFUSE_SFTPGO_TRANSFER_LOG_JSON_PATH` in some jobs.
If needed, set it in your compose env to the same file used in UI.

## 8) Suggested backup targets

Back up these files:

- `/mnt/user/appdata/streamfuse/scripts/streamfuse-smbstatus-loop.sh`
- `/mnt/user/appdata/streamfuse/scripts/unraid-metrics-loop.sh`
- `/boot/config/go`
- `/boot/config/plugins/streamfuse-widget/*` (Unraid plugin config)

## 9) Quick recovery sequence

```bash
pkill -f streamfuse-smbstatus-loop.sh || true
pkill -f unraid-metrics-loop.sh || true
nohup /mnt/user/appdata/streamfuse/scripts/streamfuse-smbstatus-loop.sh >/var/log/streamfuse-smbstatus.log 2>&1 &
nohup /mnt/user/appdata/streamfuse/scripts/unraid-metrics-loop.sh bond0 >/var/log/streamfuse-metrics.log 2>&1 &
```

Then trigger:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/internal/samba/poll
curl -X POST http://127.0.0.1:8000/api/v1/internal/sftpgo/poll
```
