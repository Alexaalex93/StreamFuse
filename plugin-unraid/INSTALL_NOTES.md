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

## Troubleshooting

- If tile says backend unreachable: verify backend URL and that StreamFuse backend is up.
- If no sessions appear: verify `GET /api/dashboard/widget?limit=5` returns data.
- If removed plugin, reinstall to recreate default cfg.
