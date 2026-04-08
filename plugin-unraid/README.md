# StreamFuse Unraid Dashboard Widget

Integracion funcional inicial (Fase 2) de StreamFuse para Unraid Dashboard.

## Que implementa esta fase

- Widget compacto y visual para sesiones activas.
- Mini caratulas (40x60) junto a cada sesion.
- Consumo directo de StreamFuse API (`/api/dashboard/widget`).
- Estados `loading`, `empty`, `error`.
- Auto-refresh cada pocos segundos.
- Enlace para abrir StreamFuse completo.

## Estructura

- `manifest.json`: metadatos del scaffold funcional.
- `config/config.example.json`: ejemplo de configuracion.
- `widget/index.html`: widget card.
- `widget/widget.css`: estilos compactos.
- `widget/widget.js`: cliente API y render.
- `widget/assets/poster-placeholder.svg`: fallback de caratula.
- `INSTALL_NOTES.md`: guia de integracion en Unraid.

## API requerida

Endpoint principal consumido por el widget:

- `GET /api/dashboard/widget?limit=5`

Contrato esperado (resumen):

```json
{
  "summary": {
    "active_sessions": 3,
    "tautulli_sessions": 2,
    "sftpgo_sessions": 1,
    "total_bandwidth_bps": 43000000,
    "total_bandwidth_human": "43.0 Mbps",
    "updated_at": "2026-04-08T14:20:00Z"
  },
  "sessions": [
    {
      "id": 12,
      "title": "Dune: Part Two",
      "user_name": "alice",
      "source": "tautulli",
      "media_type": "movie",
      "bandwidth_human": "12 Mbps",
      "poster_url": "/api/v1/posters/12"
    }
  ],
  "hidden_count": 2
}
```

## Configuracion rapida

El widget soporta query params en la URL:

- `apiBase`: base API de StreamFuse (default `http://localhost:8000/api`)
- `appUrl`: URL de la app completa (default `http://localhost:5173`)
- `refresh`: segundos de refresh
- `limit`: maximo visible (3-5 recomendado)

Ejemplo:

```text
widget/index.html?apiBase=http://192.168.1.50:8000/api&appUrl=http://192.168.1.50:5173&refresh=10&limit=5
```

## Notas importantes

- El widget no reimplementa logica de negocio.
- Toda la unificacion/posters/normalizacion sigue en StreamFuse.
- Si StreamFuse no responde, muestra estado de error y boton Retry.