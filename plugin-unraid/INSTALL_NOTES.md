# Install Notes (Unraid Native Plugin)

## 1) Build package and push to GitHub

From `C:\src\StreamFuse`:

```powershell
powershell -ExecutionPolicy Bypass -File .\plugin-unraid\scripts\build-unraid-plugin.ps1
```

Then commit and push these paths to `main`:

- `plugin-unraid/plg/streamfuse-widget.plg`
- `plugin-unraid/release/streamfuse-widget-unraid.tar.gz`
- `plugin-unraid/runtime/...`

## 2) Install in Unraid

Go to `Plugins` -> `Install Plugin`, and paste:

```text
https://raw.githubusercontent.com/Alexaalex93/StreamFuse/main/plugin-unraid/plg/streamfuse-widget.plg
```

## 3) Configure plugin

Open `Settings` -> `StreamFuse Widget` and set:

- Backend URL: `http://192.168.0.111:8000`
- App URL: `http://192.168.0.111:5173`
- Refresh and limit values

Save.

## 4) Dashboard widget

The tile appears in Dashboard as **StreamFuse Sessions**.

If it does not show immediately, refresh the WebUI (Ctrl+F5).

## 5) Enable Samba detection (optional)

StreamFuse reads Samba sessions from a JSON file written by a host-side poller.
The `docker-compose.prod.yml` bind-mounts `/mnt/user/appdata/streamfuse/host-shared`
into the container at `/host-shared`, and the backend is pre-configured to read
`/host-shared/samba-status.json`.

**Install the poller (run once on Unraid terminal):**

```bash
# Copy the script to persistent flash storage
cp /path/to/streamfuse/plugin-unraid/scripts/smbstatus-poller.sh \
   /boot/config/custom/streamfuse-smbstatus-poller.sh
chmod +x /boot/config/custom/streamfuse-smbstatus-poller.sh

# Add auto-start on every boot (append to go script)
echo 'nohup /boot/config/custom/streamfuse-smbstatus-poller.sh >>/var/log/streamfuse-smbstatus.log 2>&1 &' \
  >> /boot/config/go

# Start it now without rebooting
nohup /boot/config/custom/streamfuse-smbstatus-poller.sh >>/var/log/streamfuse-smbstatus.log 2>&1 &
```

**Verify it works:**

```bash
# Should show PID and "started" message
cat /var/log/streamfuse-smbstatus.log

# Should contain valid JSON with sessions populated when someone is connected
cat /mnt/user/appdata/streamfuse/host-shared/samba-status.json
```

## Troubleshooting

- If tile says backend unreachable: verify backend URL and that StreamFuse backend is up.
- If no sessions appear: verify `GET /api/dashboard/widget?limit=5` returns data.
- If removed plugin, reinstall to recreate default cfg.
- Samba not detected: check poller is running (`cat /var/log/streamfuse-smbstatus.log`),
  and that `/mnt/user/appdata/streamfuse/host-shared/samba-status.json` contains real sessions.
