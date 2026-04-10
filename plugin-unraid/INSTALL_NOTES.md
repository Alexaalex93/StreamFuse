# Install Notes (Unraid)

## Option A (Recommended): Install as Unraid Plugin (.plg)

1. Push these files to GitHub (branch `main`):
   - `plugin-unraid/plg/streamfuse-widget.plg`
   - `plugin-unraid/release/unraid-widget.tar.gz`
2. In Unraid go to `Plugins` -> `Install Plugin`.
3. Paste:

```text
https://raw.githubusercontent.com/Alexaalex93/StreamFuse/main/plugin-unraid/plg/streamfuse-widget.plg
```

4. Open the widget URL:

```text
http://<UNRAID-IP>/plugins/streamfuse-widget/index.html?apiBase=http://<STREAMFUSE-HOST>:8000/api&appUrl=http://<STREAMFUSE-HOST>:5173&refresh=10&limit=5
```

## Option B: Manual copy (legacy)

## 1. Requisito previo

Levantar StreamFuse API y verificar:

- `http://<host>:8000/api/health`
- `http://<host>:8000/api/dashboard/widget`

## 2. Copiar widget

Copiar carpeta `plugin-unraid/widget/` al path donde tengas widgets/paginas custom en Unraid.

## 3. Configurar endpoint

Usar la URL del widget con parametros:

```text
index.html?apiBase=http://<host>:8000/api&appUrl=http://<host>:5173&refresh=10&limit=5
```

## 4. Verificacion visual

Debe mostrar:

- cabecera `StreamFuse`
- KPIs (active, tautulli, sftpgo)
- hasta 3-5 sesiones
- mini caratulas a la izquierda
- titulo + usuario + fuente + velocidad

## Build del paquete .tar.gz

Desde tu PC, en `C:\src\StreamFuse`:

```powershell
powershell -ExecutionPolicy Bypass -File .\plugin-unraid\scripts\build-unraid-plugin.ps1
```

## Troubleshooting

1. `Cannot reach StreamFuse`
- revisar `apiBase`
- validar CORS/red entre Unraid y StreamFuse
- comprobar backend activo

2. Sin posters
- revisar endpoint `/api/v1/posters/{id}`
- comprobar `poster_allowed_roots` y placeholder configurado

3. Lista vacia
- validar que existan sesiones activas (`/api/sessions/active`)
- revisar mocks si estas en entorno de desarrollo
