# Future Tasks (Plugin Unraid)

## Fase 2.1 - Base plugin real

- Definir formato final de plugin Unraid (`.plg`) y metadatos.
- Crear instalador real (copiar assets, registrar pagina/tile).
- Exponer configuracion de URL/token desde UI de Unraid.

## Fase 2.2 - Seguridad y operacion

- Token de solo lectura para plugin.
- Soporte HTTPS y validacion de certificado.
- Manejo de timeout/reintentos y estado degradado.

## Fase 2.3 - UX y producto

- Tile compacto con metricas clave.
- Pagina expandida con tabla de sesiones activas.
- Estados `loading`, `empty`, `error` afinados para entorno Unraid.

## Fase 2.4 - Calidad

- Tests de contrato API para endpoint de resumen.
- Tests de frontend del tile.
- Capturas de referencia para regressions visuales.

## Fase 2.5 - Release

- Canal estable y changelog.
- Versionado semantico del plugin.
- Guia de instalacion y troubleshooting.