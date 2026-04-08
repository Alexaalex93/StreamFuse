# Install Notes (Unraid)

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
- KPIs (active, tautulli, sftpgo, bandwidth)
- hasta 3-5 sesiones
- mini caratulas a la izquierda
- titulo + usuario + fuente + velocidad

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