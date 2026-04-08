# Propuesta Tecnica de Integracion Unraid

## Objetivo

Integrar StreamFuse como panel/tile dentro de Unraid para visualizar actividad unificada de Tautulli + SFTPGo.

## Enfoque recomendado

1. Fase inicial: plugin web liviano consumiendo API REST de StreamFuse.
2. Fase intermedia: autenticacion y configuracion desde UI de Unraid.
3. Fase final: empaquetado `.plg`, update channel y experiencia nativa de Unraid.

## Arquitectura de integracion

- Unraid UI (tile/page) -> HTTP -> StreamFuse API
- StreamFuse backend -> DB local -> datos unificados

El plugin no necesita logica de negocio pesada: se recomienda mantener toda la logica en StreamFuse backend y solo consumir endpoints agregados.

## Seguridad recomendada

- Token de solo lectura para el plugin.
- CORS restringido al host de Unraid.
- TLS en despliegues externos.
- Ocultar secretos en UI.

## Modelo de datos para tile

### Sessions list item

- `id`
- `user_name`
- `title`
- `source`
- `bandwidth_human`
- `media_type`
- `status`

### Summary

- `active_sessions_total`
- `active_tautulli`
- `active_sftpgo`

## Consideraciones UX

- Vista compacta para tile (top sesiones + resumen).
- Enlace a dashboard completo de StreamFuse.
- Refresh automatico cada 10-20 segundos.