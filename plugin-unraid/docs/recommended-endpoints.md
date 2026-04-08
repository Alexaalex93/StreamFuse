# StreamFuse Dashboard Widget Endpoint

Endpoint agregado para integracion compacta con Unraid Dashboard:

- `GET /api/dashboard/widget`
- `GET /api/v1/dashboard/widget`

Query params:

- `limit` (1..10, recomendado 3..5)

Respuesta:

- `summary`
  - `active_sessions`
  - `tautulli_sessions`
  - `sftpgo_sessions`
  - `total_bandwidth_bps`
  - `total_bandwidth_human`
  - `updated_at`
- `sessions[]`
  - `id`
  - `title`
  - `user_name`
  - `source`
  - `media_type`
  - `bandwidth_bps`
  - `bandwidth_human`
  - `ip_address`
  - `poster_url` (ruta lista para mini caratula)
- `hidden_count`

Objetivo:

- evitar multiples llamadas y logica duplicada en el plugin
- entregar payload compacto para tile/widget