# StreamFuse — Referencia técnica completa

> Documento generado para uso directo por cualquier desarrollador o modelo de IA sin necesidad de leer el código fuente.
> Cubre arquitectura, todos los ficheros clave, sus funciones y propósitos.

---

## Índice

1. [Visión general](#1-vision-general)
2. [Arquitectura del sistema](#2-arquitectura-del-sistema)
3. [Despliegue / Docker](#3-despliegue--docker)
4. [Variables de entorno](#4-variables-de-entorno)
5. [Backend — estructura](#5-backend--estructura)
6. [Backend — enums y modelos de datos](#6-backend--enums-y-modelos-de-datos)
7. [Backend — API REST (endpoints)](#7-backend--api-rest-endpoints)
8. [Backend — servicios](#8-backend--servicios)
9. [Backend — adaptadores de fuente](#9-backend--adaptadores-de-fuente)
10. [Backend — jobs (sincronización)](#10-backend--jobs-sincronizacion)
11. [Backend — persistencia](#11-backend--persistencia)
12. [Backend — resolución de posters](#12-backend--resolucion-de-posters)
13. [Frontend — estructura](#13-frontend--estructura)
14. [Frontend — páginas](#14-frontend--paginas)
15. [Frontend — componentes de sesiones](#15-frontend--componentes-de-sesiones)
16. [Frontend — componentes de historial](#16-frontend--componentes-de-historial)
17. [Frontend — componentes de estadísticas](#17-frontend--componentes-de-estadisticas)
18. [Frontend — shared (API, i18n, UI)](#18-frontend--shared-api-i18n-ui)
19. [Frontend — tipos TypeScript](#19-frontend--tipos-typescript)
20. [Flujo de datos end-to-end](#20-flujo-de-datos-end-to-end)
21. [Cómo añadir una nueva fuente de datos](#21-como-anadir-una-nueva-fuente-de-datos)
22. [Cómo añadir una nueva página al frontend](#22-como-anadir-una-nueva-pagina-al-frontend)
23. [Puntos críticos y decisiones de diseño](#23-puntos-criticos-y-decisiones-de-diseno)

---

## 1. Visión general

**StreamFuse** es un panel de monitorización unificado para actividad multimedia y transferencias de ficheros en un servidor doméstico (típicamente Unraid).

Consolida en tiempo real sesiones procedentes de tres fuentes:
| Fuente | Protocolo | Qué monitoriza |
|---|---|---|
| **Tautulli** | HTTP/API REST | Reproducción Plex (películas, series, directo) |
| **SFTPGo** | HTTP/API REST + JSONL log | Transferencias FTP/SFTP |
| **Samba** | JSON snapshot (`smbstatus`) | Transferencias SMB |

El backend también lee un fichero JSON de métricas de Unraid para mostrar CPU, GPU, RAM, red y consumo energético en tiempo real.

---

## 2. Arquitectura del sistema

```
┌──────────────────────────────────────────────────────────┐
│                       FRONTEND                           │
│  React + Vite + TypeScript + TailwindCSS                 │
│  Puerto 5173 (dev) / Nginx (prod)                        │
│                                                          │
│  Pages: Dashboard · History · Stats · Settings · Login   │
└────────────────────┬─────────────────────────────────────┘
                     │  HTTP / Bearer JWT
                     ▼
┌──────────────────────────────────────────────────────────┐
│                       BACKEND                            │
│  FastAPI + SQLAlchemy + Alembic                          │
│  Puerto 8000                                             │
│                                                          │
│  /api/v1/...  (protegido con JWT)                        │
│  /api/...     (legacy, sin auth — usado por widget)      │
│                                                          │
│  BackgroundSyncRunner (asyncio task, cada N segundos)    │
│    ├── Tautulli sync                                     │
│    ├── SFTPGo sync                                       │
│    └── Samba sync                                        │
└────────┬───────────────────┬────────────────────────────-┘
         │                   │
         ▼                   ▼
   SQLite / PostgreSQL    Ficheros JSON en /data/
   (unified_stream_sessions,  ├── unraid-metrics.json
    app_settings,              ├── samba-status.json
    media_items, users…)       └── sftp-logs/transfers.jsonl
```

---

## 3. Despliegue / Docker

### Ficheros relevantes
| Fichero | Propósito |
|---|---|
| `docker-compose.yml` | Entorno de desarrollo (hot-reload) |
| `docker-compose.prod.yml` | Entorno de producción |
| `docker/backend.Dockerfile` | Imagen backend (FastAPI + uvicorn) |
| `docker/frontend.Dockerfile` | Imagen frontend (build Vite → Nginx) |
| `docker/nginx.conf` | Configuración Nginx: sirve estáticos + proxy `/api` → backend |

### Comandos esenciales
```bash
# Desarrollo
docker compose up

# Producción — build y push frontend
docker build -f docker/frontend.Dockerfile --target prod \
  -t alexaalex93/streamfuse-frontend:latest .
docker push alexaalex93/streamfuse-frontend:latest

# Aplicar migraciones de BD
docker exec <backend_container> alembic upgrade head
```

### Volúmenes Docker
| Volumen | Ruta en contenedor | Contenido |
|---|---|---|
| `streamfuse_data` | `/data` | BD SQLite, logs, JSONs de métricas |
| `streamfuse_frontend_node_modules` | `/app/node_modules` | Caché npm en dev |

---

## 4. Variables de entorno

Todas con prefijo `STREAMFUSE_`. Se leen en `backend/app/core/config.py`.

| Variable | Default | Descripción |
|---|---|---|
| `STREAMFUSE_DATABASE_URL` | `sqlite:///./streamfuse.db` | Cadena de conexión SQLAlchemy |
| `STREAMFUSE_DEBUG` | `true` | Modo debug FastAPI |
| `STREAMFUSE_CORS_ORIGINS` | `http://localhost:5173,...` | Orígenes CORS permitidos |
| `STREAMFUSE_TAUTULLI_BASE_URL` | `http://localhost:8181` | URL base Tautulli |
| `STREAMFUSE_TAUTULLI_API_KEY` | `changeme` | API key Tautulli |
| `STREAMFUSE_SFTPGO_BASE_URL` | `http://localhost:8080` | URL base SFTPGo |
| `STREAMFUSE_SFTPGO_API_KEY` | `changeme` | Token/API key SFTPGo |
| `STREAMFUSE_SFTPGO_TRANSFER_LOG_JSON_PATH` | `/data/sftp-logs/transfers.jsonl` | Ruta del log JSONL de SFTPGo |
| `STREAMFUSE_SAMBA_ENABLED` | `true` | Activar ingesta Samba |
| `STREAMFUSE_SAMBA_STATUS_JSON_PATH` | `/data/samba-status.json` | Ruta snapshot smbstatus |
| `STREAMFUSE_BACKGROUND_SYNC_ENABLED` | `true` | Activar sync automático |
| `STREAMFUSE_BACKGROUND_SYNC_INTERVAL_SECONDS` | `30` | Intervalo por defecto (sobreescrito por BD) |
| `STREAMFUSE_AUTH_SECRET` | `streamfuse-change-me-secret` | Secreto para firmar JWT |
| `STREAMFUSE_POSTER_PLACEHOLDER_PATH` | `app/poster_resolver/assets/placeholder.svg` | Placeholder cuando no hay poster |
| `STREAMFUSE_POSTER_ALLOWED_ROOTS` | `` | Rutas raíz permitidas para servir posters |

> **Nota:** La mayoría de estas variables tienen su equivalente editable en tiempo de ejecución desde la UI → Ajustes (se guardan en la tabla `app_settings` de la BD, que tiene prioridad sobre el `.env`).

---

## 5. Backend — estructura

```
backend/app/
├── main.py                    # Factory FastAPI, registro de routers, startup/shutdown
├── core/
│   ├── config.py              # Settings (pydantic-settings), get_settings()
│   └── time.py                # Utilidades de timezone
├── domain/
│   ├── enums.py               # StreamSource, SessionStatus, MediaType
│   └── entities/              # Entidades de dominio (no usadas directamente en prod)
├── api/
│   ├── deps.py                # Dependencias FastAPI (get_db, get_current_user)
│   └── v1/
│       ├── routers/           # Un fichero por recurso (ver sección 7)
│       └── schemas/           # Pydantic request/response schemas
├── services/                  # Lógica de negocio (ver sección 8)
├── adapters/                  # Clientes HTTP de cada fuente (ver sección 9)
├── jobs/                      # Tareas de sincronización (ver sección 10)
├── persistence/
│   ├── db.py                  # Engine SQLAlchemy, SessionLocal, Base
│   ├── models/                # Modelos ORM
│   ├── repositories/          # DAOs — toda la SQL está aquí
│   ├── migrations/            # Alembic migrations
│   └── seed.py                # Datos iniciales (usuario admin)
├── parsers/                   # Parsers de payloads de Tautulli, mediainfo
├── poster_resolver/           # Búsqueda de imágenes locales (poster/fanart)
└── security/
    └── auth.py                # JWT encode/decode, hash de contraseñas
```

---

## 6. Backend — enums y modelos de datos

### `backend/app/domain/enums.py`

```python
class StreamSource(str, Enum):
    TAUTULLI = "tautulli"   # Reproducción Plex vía Tautulli
    SFTPGO   = "sftpgo"     # Transferencias FTP/SFTP
    SAMBA    = "samba"      # Transferencias SMB

class SessionStatus(str, Enum):
    ACTIVE = "active"       # Sesión en curso
    ENDED  = "ended"        # Sesión finalizada normalmente
    ERROR  = "error"        # Finalizada por error

class MediaType(str, Enum):
    MOVIE         = "movie"
    EPISODE       = "episode"
    LIVE          = "live"
    FILE_TRANSFER = "file_transfer"
    OTHER         = "other"
```

### `unified_stream_sessions` — tabla principal

Columna clave | Tipo | Descripción
---|---|---
`id` | int PK | ID interno
`source` | StreamSource | Origen (tautulli/sftpgo/samba)
`source_session_id` | str UNIQUE con source | ID de sesión en el sistema origen
`status` | SessionStatus | active / ended / error
`user_name` | str | Nombre del usuario (con alias si configurado)
`title` | str | Título del medio o fichero
`title_clean` | str | Título normalizado para dedup
`media_type` | MediaType | Tipo de medio
`series_title` | str | Título de la serie (si episodio)
`season_number` / `episode_number` | int | S/E del episodio
`file_path` | str | Ruta absoluta del fichero en el servidor
`bandwidth_bps` | bigint | Velocidad actual en bits/s
`started_at` / `ended_at` / `updated_at` | datetime | Timestamps con timezone
`progress_percent` | float | Progreso de reproducción (0-100)
`transcode_decision` | str | direct play / transcode / copy
`resolution` / `video_codec` / `audio_codec` | str | Metadatos técnicos
`raw_payload` | JSON | Payload completo original del proveedor (para debug)

---

## 7. Backend — API REST (endpoints)

Base URL protegida: `/api/v1/` (requiere `Authorization: Bearer <token>`)
Base URL legacy: `/api/` (sin auth, para widget Unraid)

### Auth — `/api/v1/auth`
| Método | Path | Descripción |
|---|---|---|
| POST | `/auth/login` | Login con `{username, password}`. Devuelve `{access_token, token_type}` |
| POST | `/auth/change-password` | Cambiar contraseña admin. Body: `{current_password, new_password}` |

### Sessions — `/api/v1/sessions`
| Método | Path | Descripción |
|---|---|---|
| GET | `/sessions/active` | Lista sesiones ACTIVE + recientes ENDED. Query params: `user_name`, `source`, `media_type` |
| GET | `/sessions/history` | Historial paginado. Params: `user_name`, `source`, `media_type`, `date_from`, `date_to`, `limit` |

### Stats — `/api/v1/stats`
| Método | Path | Descripción |
|---|---|---|
| GET | `/stats/overview` | Totales globales: sesiones, usuarios únicos, horas, compartido. Params: `date_from`, `date_to`, `user_name` |
| GET | `/stats/distribution` | Distribuciones: por hora, por fuente, por día de semana, top usuarios, top medios |

### Settings — `/api/v1/settings`
| Método | Path | Descripción |
|---|---|---|
| GET | `/settings` | Lee toda la configuración actual |
| PUT | `/settings` | Actualiza configuración. Body: `StreamFuseSettingsUpdate` |
| GET | `/settings/detected-users` | Lista usuarios detectados en la BD para el selector de alias |

### System — `/api/v1/system`
| Método | Path | Descripción |
|---|---|---|
| GET | `/system/metrics` | Métricas del host Unraid (CPU, GPU, RAM, red, energía) leídas del JSON |

### Source Health — `/api/v1/sources/health`
| Método | Path | Descripción |
|---|---|---|
| GET | `/sources/health` | Estado de conectividad de Tautulli, SFTPGo y Samba |

### Posters — `/api/v1/posters`
| Método | Path | Descripción |
|---|---|---|
| GET | `/posters/{session_id}` | Devuelve imagen de poster o fanart. Query: `variant=poster\|fanart`, `width`, `height` |

### Internal Sync — `/api/v1/internal/sync`
| Método | Path | Descripción |
|---|---|---|
| POST | `/internal/sync/tautulli` | Fuerza sincronización manual de Tautulli |
| POST | `/internal/sync/sftpgo` | Fuerza sincronización manual de SFTPGo |
| POST | `/internal/sync/samba` | Fuerza sincronización manual de Samba |

### Health — `/api/health`
| Método | Path | Descripción |
|---|---|---|
| GET | `/health` | Ping. Devuelve `{"status": "ok"}`. Sin auth (usado por Docker healthcheck) |

---

## 8. Backend — servicios

### `SettingsService` (`services/settings_service.py`)

Gestiona toda la configuración de la aplicación. Lee/escribe en la tabla `app_settings` (clave-valor). Las claves de BD tienen prioridad sobre variables de entorno.

| Método | Descripción |
|---|---|
| `get_settings() → StreamFuseSettingsResponse` | Lee todos los ajustes y devuelve el objeto completo con valores por defecto |
| `update_settings(payload) → StreamFuseSettingsResponse` | Persiste los campos que vengan en el payload y devuelve el estado actualizado |
| `_set(key, value)` | Upsert de un ajuste individual en la BD |
| `_mask_secret(secret)` | Enmascara un secreto: `Ab****xy` para mostrar en la UI |
| `_default_secret(value)` | Devuelve `""` si el valor es `"changeme"` (secreto sin configurar) |
| `_parse_bool(raw)` | Interpreta `"true"/"1"/"yes"/"on"` como `True` |
| `_parse_list(raw)` | Deserializa JSON array o CSV en `list[str]` |
| `_parse_dict(raw)` | Deserializa JSON object en `dict[str, str]` (para alias de usuario) |
| `_validated_timezone(tz)` | Valida el timezone con `ZoneInfo`; fallback a `"UTC"` si inválido |
| `_float_or_default(by_key, key, default)` | Lee float de la BD con fallback |

**Claves almacenadas en `app_settings`:**
`ui_language`, `tautulli_url`, `tautulli_api_key`, `sftpgo_url`, `sftpgo_token`, `sftpgo_logs_path`, `sftpgo_path_mappings`, `samba_enabled`, `samba_status_json_path`, `samba_path_mappings`, `unraid_metrics_enabled`, `unraid_metrics_json_path`, `use_unraid_totals`, `energy_tariff_punta/llano/valle/weekend_eur_kwh`, `polling_frequency_seconds`, `timezone`, `media_root_paths`, `preferred_poster_names`, `user_aliases`, `placeholder_path`, `history_retention_days`

---

### `StatsService` (`services/stats_service.py`)

Genera todas las estadísticas del dashboard de stats.

| Método | Descripción |
|---|---|
| `get_overview(filters) → dict` | Totales (sesiones, usuarios, horas, compartido) + series temporales por día/semana/mes/año para sesiones, ancho de banda y datos compartidos. Incluye dedup por `(user, file, day)` para evitar contar reconexiones Infuse/FTP múltiples veces |
| `get_distribution(filters) → dict` | Distribuciones: por fuente, por día de semana, horas punta, top usuarios, top medios, top plataformas. El gráfico de horas punta distribuye cada sesión por **todas las horas que estuvo activa** (no solo la hora de inicio) |
| `_extract_shared_bytes(row) → int` | Calcula bytes reales transferidos por sesión. Prioridad: `bytes_sent` SFTPGo activo → `transfer.size` Samba (solo ENDED) → logs SFTPGo (solo ENDED) → ratio Tautulli → fallback bandwidth×tiempo. Todo capado por `os.path.getsize(file_path)` para evitar sobreestimaciones |
| `_where(filters)` | Construye cláusulas WHERE SQLAlchemy según `StatsFilters` |
| `_load_timezone()` | Lee el timezone configurado en la BD |

**`StatsFilters` dataclass:**
```python
date_from: datetime | None
date_to:   datetime | None
user_name: str | None
```

---

### `UnraidMetricsService` (`services/unraid_metrics_service.py`)

Lee un fichero JSON de snapshot de métricas del host Unraid.

| Método | Descripción |
|---|---|
| `get_metrics() → SystemMetrics` | Lee el JSON configurado y extrae CPU, GPU, RAM, red, potencia y calcula coste energético. Devuelve `SystemMetrics(enabled=False)` si no está habilitado |
| `_pick(data, keys)` | Extrae un valor de un JSON anidado probando múltiples claves alternativas (permite distintos formatos de JSON de métricas) |
| `_select_tariff_rate(now_local, cfg)` | Selecciona la tarifa eléctrica según hora y día (punta/llano/valle/fin de semana) |
| `_estimate_month_cost(watts, now, cfg)` | Simula hora a hora todo el mes aplicando la tarifa correspondiente para estimar el coste mensual |
| `format_bytes(value)` | Convierte bytes a string legible: `"8.7 GB"` |
| `format_bps(value)` | Convierte bps a `"29.0 Mbps"` o `"1.23 Gbps"` |

**`SystemMetrics` dataclass** (campos principales):
`enabled`, `source_available`, `cpu_percent`, `gpu_percent`, `ram_used_bytes`, `ram_free_bytes`, `inbound_bps`, `outbound_bps`, `power_watts`, `estimated_month_cost_eur`, `total_shared_bytes`

---

### `SFTPGoSyncService` (`services/sftpgo_sync_service.py`)

Sincroniza conexiones activas y logs de SFTPGo con la BD.

| Método | Descripción |
|---|---|
| `poll_once(log_limit) → dict` | Ciclo completo: recorta el log, reconstruye caché, consulta conexiones activas, procesa logs históricos, actualiza sesiones en BD |
| `_maybe_trim_log_file()` | Llama a `trim_transfer_log_file()` máximo una vez por hora para mantener el fichero de logs compacto |
| `_rebuild_active_session_cache()` | Reconstruye los dicts internos `_active_session_ids_by_key` y `_key_by_session_id` desde la BD |
| `_collapse_duplicate_active_sessions()` | Elimina sesiones duplicadas activas del mismo usuario+fichero (Infuse crea múltiples conexiones FTP) |
| `_merge_connections(connections)` | Agrupa conexiones del mismo usuario+fichero y toma el `bytes_sent` máximo (no suma) para evitar contar la misma transferencia varias veces |
| `_parse_path_mappings(mappings)` | Convierte strings `"origen:destino"` en lista de tuplas para remapear rutas |
| `_apply_path_mappings(path)` | Aplica los path mappings a una ruta de fichero |

**Variables de caché internas:**
- `_last_sample: dict[key, (bytes, datetime)]` — muestras anteriores para calcular velocidad incremental
- `_active_session_ids_by_key: dict[str, str]` — mapeo `connection_key → session_id`
- `_key_by_session_id: dict[str, str]` — inverso del anterior

---

### `SambaSyncService` (`services/samba_sync_service.py`)

Lee el fichero JSON de `smbstatus` e ingesta las transferencias SMB activas.

| Método | Descripción |
|---|---|
| `poll_once() → dict` | Lee el fichero JSON de Samba, mapea cada transfer activo a una sesión, upserta en BD, marca stale las que desaparezcan |
| `_read_samba_json(path)` | Lee y parsea el fichero `samba-status.json` |
| `_apply_path_mappings(path)` | Remapea rutas SMB a rutas del sistema de ficheros |

> **Limitación conocida:** `transfer.size` en Samba es el tamaño del fichero (de `stat()`), NO los bytes realmente leídos. No hay contador de bytes transferidos disponible en el protocolo SMB.

---

### `TautulliSyncService` (`services/tautulli_sync_service.py`)

Sincroniza sesiones activas e historial de Tautulli.

| Método | Descripción |
|---|---|
| `sync_active() → dict` | Consulta `/api?cmd=get_activity`, mapea sesiones activas y las upserta en BD |
| `sync_history(limit) → dict` | Consulta `/api?cmd=get_history`, importa sesiones históricas ENDED |
| `_map_session(raw)` | Convierte un objeto de sesión de Tautulli al formato `UnifiedStreamSessionCreate` |

---

### `SessionService` (`services/session_service.py`)

Capa de acceso a sesiones usada por los adaptadores de fuente.

| Método | Descripción |
|---|---|
| `upsert_session(data) → UnifiedStreamSessionModel` | Crea o actualiza una sesión por `(source, source_session_id)` |
| `end_session(source, source_session_id)` | Marca una sesión como ENDED y pone `ended_at = now()` |
| `end_stale_sessions(source, active_ids)` | Marca como ENDED todas las sesiones de una fuente que ya no están en `active_ids` |

---

### `UnifiedSessionService` (`services/unified_session_service.py`)

Servicio de consulta de sesiones para la API.

| Método | Descripción |
|---|---|
| `get_active_sessions(**filters) → list` | Devuelve sesiones ACTIVE + ENDED recientes, con filtros opcionales |
| `get_history(**filters) → list` | Devuelve historial paginado con filtros |
| `mark_stale_sessions(source)` | Marca como ENDED las sesiones activas que lleven más de `stale_seconds` sin actualizar |

---

### `UserAliasService` (`services/user_alias_service.py`)

Gestiona los alias de usuario (nombre mostrado vs nombre real).

| Método | Descripción |
|---|---|
| `resolve(user_name) → str` | Devuelve el alias configurado para `user_name` o el propio `user_name` si no hay alias |
| `get_detected_users() → list` | Lista todos los `user_name` únicos encontrados en la BD con su recuento de sesiones y alias actual |

---

### `AuthService` (`services/auth_service.py`)

| Método | Descripción |
|---|---|
| `authenticate(username, password) → str` | Valida credenciales y devuelve JWT si correctas |
| `change_password(username, current, new) → bool` | Cambia la contraseña verificando la actual |

---

### `NicRateMonitor` (`services/nic_rate_monitor.py`)

Monitor de tráfico de red en tiempo real basado en `/proc/net/dev` (Linux).

| Método | Descripción |
|---|---|
| `sample() → (rx_bps, tx_bps)` | Lee los contadores de bytes de la NIC y calcula la tasa diferencial desde la última muestra |
| `get_series(n) → (inbound_points, outbound_points)` | Devuelve los últimos N puntos de la serie temporal para el gráfico de red |

---

## 9. Backend — adaptadores de fuente

### `adapters/sftpgo/client.py` — `SFTPGoClient`

| Método | Descripción |
|---|---|
| `fetch_active_connections() → list[dict]` | GET `/api/v2/connections` — lista conexiones activas |
| `fetch_transfer_logs(limit) → list[dict]` | Lee el fichero JSONL de transferencias completadas via `parse_transfer_log_file()` |
| `test_connection() → bool` | Comprueba conectividad con SFTPGo |

### `adapters/sftpgo/log_parser.py`

| Función | Descripción |
|---|---|
| `parse_transfer_log_file(path, limit) → list[dict]` | Lee hasta `limit` entradas más recientes del JSONL usando lectura desde el final del fichero (O(limit), no O(tamaño del fichero)) |
| `parse_transfer_log_lines(lines) → list[dict]` | Parsea una lista de strings JSON a dicts |
| `trim_transfer_log_file(path, max_age_days) → int` | Elimina entradas más antiguas que `max_age_days`. Escritura atómica via `.tmp` + rename. Devuelve número de líneas eliminadas |
| `_read_tail_bytes(file_path, n_lines, chunk)` | Lee las últimas N líneas retrocediendo desde el final del fichero en chunks de 8KB (eficiente con ficheros grandes) |

### `adapters/sftpgo/mapper.py` — `build_sftpgo_session_payload`

Convierte una conexión activa de SFTPGo al formato `UnifiedStreamSessionCreate`. Incluye la resolución del tipo de medio por extensión de fichero y el cálculo de velocidad.

### `adapters/sftpgo/contracts.py`

Pydantic models para el formato de la API de SFTPGo: `SFTPGoConnection`, `SFTPGoTransfer`, `SFTPGoActiveConnections`.

### `adapters/tautulli/client.py` — `TautulliClient`

| Método | Descripción |
|---|---|
| `get_activity() → dict` | GET con `cmd=get_activity` — sesiones en curso |
| `get_history(length) → dict` | GET con `cmd=get_history` — historial |
| `test_connection() → bool` | Comprueba conectividad |

### `adapters/tautulli/mapper.py`

| Función | Descripción |
|---|---|
| `map_tautulli_session(raw) → UnifiedStreamSessionCreate` | Convierte un objeto de sesión de Tautulli (con todos sus campos) a la entidad unificada interna |

### `adapters/samba/client.py` — `SambaClient`

| Método | Descripción |
|---|---|
| `read_status() → dict` | Lee y parsea el fichero JSON de `smbstatus` |
| `test_connection() → bool` | Verifica que el fichero JSON existe y es legible |

---

## 10. Backend — jobs (sincronización)

### `BackgroundSyncRunner` (`jobs/background_sync.py`)

Tarea `asyncio` que se ejecuta en bucle infinito mientras el servidor está en marcha.

| Método | Descripción |
|---|---|
| `run_forever()` | Bucle principal: ejecuta los tres polls, espera el intervalo configurado, repite |
| `stop()` | Señaliza al bucle que pare (usado en shutdown de FastAPI) |
| `_resolve_polling_interval() → int` | Lee el intervalo de la BD (configurado por el usuario en Ajustes). Mínimo 5 segundos |

**Orden de ejecución en cada ciclo:**
1. `run_tautulli_import(include_history=False)` — solo sesiones activas
2. `run_sftpgo_poll()` — conexiones activas + logs
3. `run_samba_poll()` — snapshot SMB

### `jobs/import_tautulli.py` — `run_once(include_history)`

Ejecuta una sincronización completa de Tautulli: carga configuración de BD, instancia el cliente y el servicio, y llama a `sync_active()` (y opcionalmente `sync_history()`).

### `jobs/poll_sftpgo.py` — `run_once()`

Carga configuración, instancia `SFTPGoSyncService` y llama a `poll_once()`.

### `jobs/poll_samba.py` — `run_once()`

Carga configuración, instancia `SambaSyncService` y llama a `poll_once()`.

---

## 11. Backend — persistencia

### `persistence/db.py`

```python
engine = create_engine(DATABASE_URL)   # SQLAlchemy engine
SessionLocal = sessionmaker(...)       # Factoría de sesiones DB
Base = declarative_base()              # Base para todos los modelos ORM
```

### Modelos ORM (`persistence/models/`)

| Modelo | Tabla | Descripción |
|---|---|---|
| `UnifiedStreamSessionModel` | `unified_stream_sessions` | Tabla principal — todas las sesiones |
| `AppSettingModel` | `app_settings` | Configuración clave-valor persistente |
| `UserModel` | `users` | Usuarios del sistema (solo admin en prod) |
| `MediaItemModel` | `media_items` | Caché de metadatos de medios |
| `ActivityEventModel` | `activity_events` | Log de eventos de actividad |
| `IngestionLogModel` | `ingestion_logs` | Registro de ciclos de ingesta |

### Repositorios (`persistence/repositories/`)

Cada repositorio encapsula toda la SQL para su modelo:

| Repositorio | Métodos clave |
|---|---|
| `UnifiedStreamSessionRepository` | `list_active(filters)`, `list_history(filters)`, `create(data)`, `upsert(data)`, `mark_active_as_stale(cutoff, source)` |
| `AppSettingRepository` | `get(key)`, `get_many(keys)`, `set(key, value, description)` |
| `UserRepository` | `get_by_username(username)`, `create(username, hashed_password)` |

### `SessionQueryFilters` dataclass

```python
user_name:  str | None
source:     StreamSource | None
media_type: MediaType | None
date_from:  datetime | None
date_to:    datetime | None
limit:      int = 200
```

### Migraciones (Alembic)

```
persistence/migrations/versions/
├── 20260408_0001_initial_streamfuse_schema.py   # Schema inicial completo
└── 20260410_0002_add_samba_stream_source.py     # Añade "samba" al enum source
```

Para añadir una migración:
```bash
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
```

---

## 12. Backend — resolución de posters

### `PosterResolver` (`poster_resolver/resolver.py`)

Busca imágenes de poster y fanart en el sistema de ficheros local.

| Método | Descripción |
|---|---|
| `resolve(file_path, media_type, variant) → Path` | Punto de entrada principal. Devuelve ruta al poster/fanart o al placeholder si no encuentra nada. Usa caché interna thread-safe |
| `resolve_movie_image(file, variant) → Path` | Busca en el directorio del fichero y en el directorio padre: `poster.jpg`, `cover.jpg`, `folder.jpg`, `movie.jpg` (o equivalentes fanart) |
| `resolve_series_image(file, variant) → Path` | Busca hacia arriba por la jerarquía de directorios (episodio → temporada → serie) |
| `_sanitize_file_path(path) → Path | None` | Valida que la ruta esté dentro de las `allowed_roots` para evitar path traversal |

**Prioridad de búsqueda de poster:** `poster.jpg > cover.jpg > folder.jpg > movie.jpg`
**Prioridad de fanart:** `fanart.jpg > backdrop.jpg > background.jpg`

La ruta del endpoint `/api/v1/posters/{session_id}` llama a este resolver con la `file_path` almacenada en la BD y sirve la imagen directamente.

---

## 13. Frontend — estructura

```
frontend/src/
├── app/
│   ├── App.tsx              # Raíz: autenticación, selección de sección, AppShell
│   └── layout/
│       └── AppShell.tsx     # Layout principal: sidebar nav + topbar + main
├── pages/
│   ├── DashboardPage.tsx    # Dashboard en tiempo real
│   ├── HistoryPage.tsx      # Historial de sesiones
│   ├── StatsPage.tsx        # Estadísticas y gráficos
│   ├── SettingsPage.tsx     # Configuración
│   └── LoginPage.tsx        # Pantalla de login
├── features/
│   ├── sessions/components/ # SessionCard, FilterPanel, MediaDetailsDrawer, etc.
│   ├── history/components/  # HistoryTable, HistoryFilterPanel
│   └── stats/components/    # Gráficos (AreaChart, DonutChart, etc.)
├── shared/
│   ├── api/client.ts        # HTTP client con JWT
│   ├── lib/
│   │   ├── i18n.ts          # Sistema de traducción ES/EN
│   │   ├── date.ts          # Formateo de fechas
│   │   └── cn.ts            # Utilidad clsx/tailwind
│   └── ui/                  # Componentes UI base (Button, StatCard, badges, states)
└── types/                   # Tipos TypeScript (session, stats, settings, auth, system)
```

---

## 14. Frontend — páginas

### `App.tsx`

Punto de entrada de la aplicación React.

| Elemento | Descripción |
|---|---|
| Estado `isAuthenticated` | Controla si mostrar `LoginPage` o la app principal |
| Estado `language` | Idioma actual (`"es"` / `"en"`), se actualiza con el evento `streamfuse:language-changed` |
| Estado `currentSection` | Sección activa: `"dashboard"` / `"history"` / `"stats"` / `"settings"` |
| `onAuthenticated()` | Callback del login — pone `isAuthenticated = true` |
| `onLogout()` | Limpia el token JWT y vuelve al login |

---

### `AppShell.tsx`

Layout envolvente para toda la app autenticada.

| Elemento | Descripción |
|---|---|
| Sidebar | Navegación con 4 secciones, badge de estado de fuentes (Tautulli/SFTPGo/Samba) |
| Topbar | Título + botón "Cerrar sesión" |
| Source health polling | Cada 20 segundos llama a `/api/v1/sources/health` para actualizar los indicadores de conexión |
| Props | `language`, `currentSection`, `onChangeSection`, `onLogout`, `children` |

---

### `DashboardPage.tsx`

Dashboard en tiempo real. Polling automático cada `polling_frequency_seconds`.

**Secciones:**
1. **Estado del Sistema** — 5 StatCards (CPU, GPU, RAM, Red saliente, Potencia) + gráfico de red en tiempo real
2. **6 StatCards** — Sesiones activas, Usuarios activos, Sesiones Tautulli/SFTPGo/Samba, Total Compartido
3. **FilterPanel** — Filtros de usuario, fuente y tipo de medio
4. **Grid de sesiones activas** — SessionCards clicables que abren el MediaDetailsDrawer
5. **Actividad reciente** — Lista de sesiones ENDED recientes

**Funciones internas:**
| Función | Descripción |
|---|---|
| `formatPercent(v)` | `42.3 → "42.3%"` |
| `formatBytes(v)` | Bytes a string legible: `"8.7 GB"` |
| `formatTrafficRate(bps)` | `29000 → "29.0 kbps"` |
| `formatMoney(v)` | `1.23 → "€1.23"` |
| `relativeFromNow(iso)` | `"hace 2 min"` / `"2 min ago"` |
| `derived` (useMemo) | Calcula totales (sessionsActive, usersActive, totalBandwidth, etc.) desde las sesiones activas |
| `relatedSessions` (useMemo) | Filtra sesiones relacionadas (mismo usuario o mismo título) para el drawer |

---

### `HistoryPage.tsx`

Historial de sesiones con filtros y dos vistas.

| Elemento | Descripción |
|---|---|
| Vista tabla | `HistoryTable` con columnas expandibles que muestran detalle técnico + poster |
| Vista tarjetas | Grid de `PosterCard` con metadatos básicos |
| Filtros | `HistoryFilterPanel` (texto, usuario, fuente, tipo, fechas) |
| Chips | Indicadores visuales de filtros activos |
| Paginación | 12 elementos por página, cliente-side sobre los resultados del API |
| `filteredRows` (useMemo) | Filtro de texto en cliente sobre los resultados ya cargados |

---

### `StatsPage.tsx`

Estadísticas completas con gráficos interactivos.

**Secciones:**
1. **4 StatCards** — Sesiones totales, Activas ahora, Total compartido, Usuarios únicos
2. **Tendencias** — Sesiones/Ancho de banda/Compartido por día/semana/mes/año (con drill-down por usuario)
3. **Distribuciones** — Horas punta, por fuente (donut), por día de semana, por tipo de medio
4. **Top usuarios y medios** — Rankings de usuarios más activos y títulos más vistos

**Drill-down por usuario:** Al hacer clic en un periodo del gráfico de tendencias, se muestra un `MultiLineChart` con una línea por usuario. Se puede explorar día/semana/mes/año para cada dimensión (sesiones, ancho de banda, compartido).

---

### `SettingsPage.tsx`

Formulario completo de configuración.

**Secciones del formulario:**
1. Conexiones de proveedor (Tautulli + SFTPGo URLs, tokens, ruta de logs)
2. Samba (enable toggle, ruta JSON, path mappings)
3. Unraid System Metrics (enable, ruta JSON, use_unraid_totals, tarifas eléctricas)
4. Comportamiento (polling, timezone, idioma, placeholder, retención, rutas raíz, nombres de poster)
5. Alias de usuario (selector de usuario detectado → asignar nombre de visualización)
6. Admin Security (cambio de contraseña)

Al guardar, llama a `setStoredLanguage(updated.ui_language)` que despacha el evento `streamfuse:language-changed` para actualizar todos los componentes en tiempo real.

---

### `LoginPage.tsx`

Pantalla de login minimalista. Username por defecto `"admin"`, password vacío. Llama a `POST /api/v1/auth/login` y guarda el JWT en `localStorage`.

---

## 15. Frontend — componentes de sesiones

### `SessionCard.tsx`

Tarjeta completa de sesión activa. Muestra poster, fanart de fondo, metadatos técnicos y barra de progreso.

**Funciones internas:**
| Función | Descripción |
|---|---|
| `cardTitle(session)` | Para episodios devuelve `series_title`; para el resto `title` |
| `cardSubtitle(session)` | Para episodios construye `"Serie - S01E05 - Título del episodio"` limpiando duplicados |
| `formatEpisodeCode(session)` | `"S01E05"` a partir de `season_number` y `episode_number` |
| `extractBitrate(session)` | Extrae bitrate del `raw_payload` (mediainfo > stream_bitrate > bitrate > bandwidth_human) |
| `summarizePath(path)` | Trunca rutas largas a `"...últimos 80 chars"` |

---

### `MediaDetailsDrawer.tsx`

Panel lateral deslizante con el detalle completo de una sesión.

Muestra: poster grande, datos técnicos (tipo, IP, resolución, codecs, transcode, bitrate, cliente, reproductor), timeline (inicio/fin/actualización), ruta del fichero, sesiones relacionadas y payload debug.

---

### `FilterPanel.tsx`

Barra horizontal de filtros para el Dashboard. Campos: usuario, fuente (Tautulli/SFTPGo/Samba/All), tipo de medio.

---

### `BandwidthBadge.tsx`

Badge con el ancho de banda de la sesión. Color según velocidad:
- Verde: > 20 Mbps
- Amarillo: 5-20 Mbps
- Rojo/gris: < 5 Mbps

### `ProgressBar.tsx`

Barra de progreso de reproducción con gradiente cyan→sky→emerald.

### `PosterCard.tsx`

Imagen de poster/fanart cargada desde `/api/v1/posters/{sessionId}`. Con fallback al placeholder SVG.

---

## 16. Frontend — componentes de historial

### `HistoryFilterPanel.tsx`

Panel lateral de filtros del historial. Campos adicionales respecto a `FilterPanel`: texto libre, rango de fechas (desde/hasta).

### `HistoryTable.tsx`

Tabla del historial con filas expandibles.

**Funciones internas:**
| Función | Descripción |
|---|---|
| `rowTitle(session, untitled)` | Título de fila: para episodios usa `series_title` |
| `rowSubtitle(session)` | Para no-episodios: `file_path`. Para episodios: `"Serie - S01E05 - Título"` |
| `extractBitrateText(session)` | Mismo algoritmo que `SessionCard.extractBitrate` |
| `mediaLabel(session, seriesWord)` | Devuelve `"serie"` / `"series"` según idioma para el tipo `episode` |

Al expandir una fila se muestra poster + grid de datos técnicos (12 campos) + ruta.

---

## 17. Frontend — componentes de estadísticas

Todos los gráficos son SVG puros con React, sin librería externa de charts.

| Componente | Descripción |
|---|---|
| `AreaChart` | Gráfico de área para series temporales simples (eje X = tiempo, eje Y = valor) |
| `MultiLineChart` | Múltiples líneas, una por usuario, con leyenda y colores por usuario |
| `VerticalBarChart` | Barras verticales para distribución por hora o por día de semana |
| `GroupedBarChart` | Barras agrupadas para comparar múltiples series en el mismo periodo |
| `HorizontalBars` | Ranking horizontal (top usuarios, top medios) |
| `DonutChart` | Gráfico de donut para distribución por fuente |
| `TopMediaList` | Lista de top películas/series con título + recuento |
| `ChartCard` | Wrapper con título, descripción y tabs de periodo (Diario/Semanal/Mensual/Anual) |

---

## 18. Frontend — shared (API, i18n, UI)

### `shared/api/client.ts`

| Función | Descripción |
|---|---|
| `apiGet<T>(path)` | GET autenticado. Lanza `ApiError` si status ≠ 2xx |
| `apiPost<TRes, TBody>(path, body)` | POST con JSON body |
| `apiPut<TRes, TBody>(path, body)` | PUT con JSON body |
| `apiGetWithFallback<T>(paths[])` | Prueba cada path en orden, útil para endpoints legacy + v1 |
| `setAuthToken(token)` | Guarda JWT en `localStorage` |
| `getAuthToken()` | Lee JWT de `localStorage` |
| `clearAuthToken()` | Elimina JWT (logout) |
| `getBackendBase()` | Devuelve la URL base del backend sin `/api/v1` (para URLs de posters) |
| `resolveApiBase()` | Resuelve la URL de la API: si es localhost reemplaza el hostname con el del browser (útil para acceso remoto al contenedor) |

**`ApiError`** — extiende `Error` con `.status: number` y `.body: string`.

---

### `shared/lib/i18n.ts`

Sistema de traducción reactivo ES/EN.

| Función | Descripción |
|---|---|
| `getStoredLanguage() → UiLanguage` | Lee `"es"` / `"en"` de `localStorage` |
| `setStoredLanguage(lang)` | Guarda en `localStorage` Y despacha evento `streamfuse:language-changed` |
| `normalizeLanguage(value) → UiLanguage` | Coerce a `"en"` o `"es"` (default `"es"`) |
| `t(language, key) → string` | Traduce una clave del objeto `translations` central |

**Patrón estándar en componentes:**
```tsx
const [lang, setLang] = useState<UiLanguage>(getStoredLanguage());
useEffect(() => {
  const handler = (e: Event) =>
    setLang((e as CustomEvent<{ language: UiLanguage }>).detail.language);
  window.addEventListener("streamfuse:language-changed", handler);
  return () => window.removeEventListener("streamfuse:language-changed", handler);
}, []);
const tx = TEXT[lang];  // TEXT = { es: {...}, en: {...} } local al componente
```

**Claves centrales en `i18n.ts`** (usadas por `AppShell` vía `t()`):
`nav.dashboard/history/stats/settings`, `header.title/subtitle/logout`, `source.health/connected/disconnected/checking`

**Componentes con TEXT local propio** (patrón completo implementado):
`DashboardPage`, `HistoryPage`, `StatsPage`, `SettingsPage`, `LoginPage`, `SessionCard`, `FilterPanel`, `HistoryFilterPanel`, `HistoryTable`, `MediaDetailsDrawer`

---

### `shared/lib/date.ts`

| Función | Descripción |
|---|---|
| `formatLocalTime(iso)` | Hora local en formato corto: `"14:32"` |
| `formatLocalDateTime(iso)` | Fecha y hora completa local |
| `relativeFromNow(iso)` | Tiempo relativo: `"hace 2 min"` / `"2 min ago"` según idioma del browser |

### `shared/lib/cn.ts`

`cn(...classes)` — wrapper de `clsx` para combinar clases Tailwind condicionalmente.

---

### UI base (`shared/ui/`)

| Componente | Descripción |
|---|---|
| `Button` | Botón con variantes: `default` (cyan), `outline`, `ghost`. Props: `variant`, `disabled`, `onClick`, `type` |
| `StatCard` | Tarjeta de métrica: `label` (pequeño), `value` (grande), `hint` (subtexto) |
| `SourceBadge` | Badge de color por fuente: Tautulli=violeta, SFTPGo=cyan, Samba=naranja |
| `LoadingState` | Spinner + título centrado |
| `EmptyState` | Icono + título + descripción para estados vacíos |
| `ErrorState` | Icono de error + título + descripción |

---

## 19. Frontend — tipos TypeScript

### `types/session.ts` — `UnifiedSession`

Refleja exactamente `UnifiedStreamSessionResponse` del backend. Todos los campos opcionales son `| null`.

Campos clave: `id`, `source`, `source_session_id`, `status`, `user_name`, `title`, `title_clean`, `media_type`, `series_title`, `season_number`, `episode_number`, `file_path`, `bandwidth_bps`, `bandwidth_human`, `started_at`, `ended_at`, `updated_at`, `progress_percent`, `transcode_decision`, `resolution`, `video_codec`, `audio_codec`, `raw_payload`

### `types/domain.ts`

```typescript
type StreamSource = "tautulli" | "sftpgo" | "samba"
type MediaType    = "movie" | "episode" | "live" | "file_transfer" | "other"
type SessionStatus = "active" | "ended" | "error"
```

### `types/settings.ts` — `StreamFuseSettings` / `StreamFuseSettingsUpdate`

Refleja la respuesta de `GET /settings`. `StreamFuseSettingsUpdate` es parcial (todos los campos opcionales).

### `types/stats.ts`

`OverviewStats`, `MediaStatsResponse`, `UsersStatsResponse` — reflejan las respuestas del endpoint `/stats`.

### `types/system.ts` — `SystemMetricsResponse`

Estructura anidada:
```typescript
{
  enabled: boolean
  source_available: boolean
  identity: { cpu_model, gpu_model }
  load: { cpu_percent, gpu_percent, ram_used_bytes, ram_free_bytes }
  network: { inbound_bps, outbound_bps }
  energy: { power_watts, estimated_month_cost_eur }
}
```

### `types/auth.ts`

`LoginRequest`, `LoginResponse`, `ChangePasswordRequest`

---

## 20. Flujo de datos end-to-end

### Ciclo de sincronización (cada N segundos)

```
BackgroundSyncRunner.run_forever()
  │
  ├─ run_tautulli_import()
  │    └─ TautulliClient.get_activity()
  │         → map_tautulli_session()
  │              → SessionService.upsert_session()
  │                   → unified_stream_sessions (BD)
  │
  ├─ run_sftpgo_poll()
  │    └─ SFTPGoSyncService.poll_once()
  │         ├─ trim_transfer_log_file() [máx. 1x/hora]
  │         ├─ SFTPGoClient.fetch_active_connections()
  │         │    → _merge_connections() [dedup FTP reconexiones]
  │         │         → build_sftpgo_session_payload()
  │         │              → SessionService.upsert_session()
  │         └─ SFTPGoClient.fetch_transfer_logs()
  │              → sesiones ENDED por log
  │
  └─ run_samba_poll()
       └─ SambaSyncService.poll_once()
            └─ SambaClient.read_status()
                 → sesiones SMB activas
```

### Petición del frontend (Dashboard)

```
DashboardPage (polling cada N seg)
  │
  ├─ GET /api/v1/sessions/active
  │    → UnifiedSessionService.get_active_sessions()
  │         → unified_stream_session_repository.list_active()
  │              → SQL: status='active' ORDER BY updated_at DESC
  │
  ├─ GET /api/v1/system/metrics
  │    → UnraidMetricsService.get_metrics()
  │         → lee /data/unraid-metrics.json
  │
  └─ GET /api/v1/posters/{id}?variant=fanart
       → PosterResolver.resolve(file_path, media_type, variant="fanart")
            → busca fanart.jpg en directorios del fichero
```

---

## 21. Cómo añadir una nueva fuente de datos

1. **Añadir el enum:** `domain/enums.py` → `StreamSource.NUEVA = "nueva"`

2. **Crear la migración:**
   ```
   persistence/migrations/versions/YYYYMMDD_000N_add_nueva_source.py
   ```
   Actualiza los valores del enum de BD.

3. **Crear el adaptador:**
   ```
   adapters/nueva/
     __init__.py
     client.py      # NuevaClient con fetch_active() y test_connection()
     mapper.py      # map_nueva_session() → UnifiedStreamSessionCreate
   ```

4. **Crear el servicio de sync:**
   ```
   services/nueva_sync_service.py  # NuevaSyncService con poll_once()
   ```

5. **Crear el job:**
   ```
   jobs/poll_nueva.py  # run_once() que instancia cliente + servicio
   ```

6. **Registrar en el runner:**
   `jobs/background_sync.py` → añadir `await run_nueva_poll()` en `run_forever()`

7. **Añadir a source health:**
   `api/v1/routers/source_health.py` → añadir entrada para la nueva fuente

8. **Frontend — `HistoryFilterPanel` y `FilterPanel`:**
   Añadir `<option value="nueva">Nueva</option>` en los selects de fuente

9. **Frontend — `SourceBadge`:**
   Añadir color y label para la nueva fuente

---

## 22. Cómo añadir una nueva página al frontend

1. Crear `frontend/src/pages/NuevaPage.tsx` con el patrón de traducción:
   ```tsx
   const TEXT = { es: { ... }, en: { ... } } as const;
   
   export function NuevaPage() {
     const [lang, setLang] = useState<UiLanguage>(getStoredLanguage());
     useEffect(() => {
       const handler = (e: Event) =>
         setLang((e as CustomEvent<{ language: UiLanguage }>).detail.language);
       window.addEventListener("streamfuse:language-changed", handler);
       return () => window.removeEventListener("streamfuse:language-changed", handler);
     }, []);
     const tx = TEXT[lang];
     // ...
   }
   ```

2. Añadir la sección en `App.tsx`:
   - Añadir `"nueva"` al tipo `AppSection`
   - Añadir el `case "nueva": return <NuevaPage />` en el switch de renderizado

3. Añadir a la navegación en `AppShell.tsx`:
   - Añadir la entrada en `navItems`

4. Añadir las claves de traducción en `shared/lib/i18n.ts`:
   - `"nav.nueva"` y `"nav.nuevaHint"`

---

## 23. Puntos críticos y decisiones de diseño

### Deduplicación de sesiones SFTPGo (Infuse FTP)

**Problema:** Infuse abre múltiples conexiones FTP secuenciales para un mismo fichero (una por segmento). Cada reconexión genera un nuevo `connection_time` en SFTPGo, haciendo que el contador de sesiones se dispare.

**Solución aplicada:**
- `_merge_connections()`: agrupa conexiones por `(user, file)` y toma `bytes_sent = max(...)`, no suma
- Dedup en gráficos de tendencia: clave `(user_name, file_path, day)` — si la misma persona ve el mismo fichero el mismo día, cuenta como 1 sesión
- Dedup en gráfico de horas punta: un `(user, file)` por hora — evita contar 10 reconexiones en la misma hora

### Cálculo de "Total Compartido"

**Prioridad en `_extract_shared_bytes()`:**
1. `bytes_sent` de SFTPGo activo (dato real del contador de red)
2. `transfer.size` de Samba ENDED (es el tamaño del fichero, NO bytes leídos)
3. `size_bytes` del log de SFTPGo para sesiones ENDED
4. Ratio de progreso × tamaño (Tautulli)
5. `bandwidth_bps × elapsed_seconds` como fallback

Todo se capa con `os.path.getsize(file_path)` para no sobreestimar en ficheros grandes (Blu-ray remux 50+ GB).

### Gestión del log JSONL de SFTPGo

El log puede crecer indefinidamente. Dos mecanismos de control:
- **Lectura eficiente:** `_read_tail_bytes()` lee solo las últimas N líneas desde el final (O(N), no O(tamaño))
- **Rotación automática:** `trim_transfer_log_file()` se llama máximo 1 vez/hora y elimina entradas > 7 días. Usa escritura atómica via `.tmp` + `rename()` para seguridad concurrente

### Sistema de traducción (i18n)

Cada componente tiene su propio `TEXT = { es: {...}, en: {...} }` y escucha el evento `streamfuse:language-changed` para actualizarse en tiempo real sin recargar la página. El idioma se persiste en `localStorage` y también en la BD (campo `ui_language` en `app_settings`) para que se restaure entre sesiones.

No se usa ninguna librería de i18n externa. El patrón es deliberadamente simple y autocontenido.

### Resolución de posters

El sistema no llama a ninguna API externa de metadatos (TMDB, TVDB, etc.). Busca imágenes directamente en los directorios del sistema de ficheros local partiendo de la `file_path` almacenada en la BD. Esto requiere que los volúmenes con los medios estén montados en el contenedor Docker con `poster_allowed_roots` configurado.

### Seguridad

- Solo existe el usuario `admin`. No hay gestión de múltiples usuarios.
- JWT con tiempo de expiración configurable via `auth_secret`.
- Las API keys (Tautulli, SFTPGo) se almacenan en la BD sin cifrar. Asegurar acceso a la BD.
- El endpoint `/api/health` (sin `/v1/`) no requiere auth — usado por Docker healthcheck.
- Los posters (`/api/v1/posters/`) tampoco requieren auth para facilitar la carga de imágenes en el frontend antes de la inicialización del token.
