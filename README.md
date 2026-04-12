# StreamFuse

StreamFuse unifica actividad de Tautulli y SFTPGo en una sola interfaz moderna.

## Arranque rapido

### Opcion 1 (Windows PowerShell)

```powershell
./scripts/bootstrap-dev.ps1
```

### Opcion 2 (Linux/macOS/Git Bash)

```bash
./scripts/bootstrap-dev.sh
```

Esto hace:
1. Crea `.env` desde `.env.example` si no existe.
2. Levanta backend + frontend con `docker compose up --build`.
3. Ejecuta migraciones al iniciar backend y si hay mocks activos, siembra datos mock automaticamente.

## URLs utiles

- Frontend dev: [http://localhost:5173](http://localhost:5173)
- Backend: [http://localhost:8000](http://localhost:8000)
- Health: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- API v1 health: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

## Modos Docker

### Desarrollo (por defecto)

```bash
docker compose up --build
```

Caracteristicas:
- Hot reload backend (`uvicorn --reload`).
- Vite dev server para frontend.
- Volumenes de codigo (`./backend`, `./frontend`).
- SQLite persistente en volumen `streamfuse_data`.
- Datos mock por defecto si no hay credenciales reales.

### Cercano a produccion

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

O con script:

```powershell
./scripts/bootstrap-prod.ps1
```

```bash
./scripts/bootstrap-prod.sh
```

Caracteristicas:
- Backend en modo `prod` (sin reload, workers configurables).
- Frontend servido por Nginx (build estatico).
- Postgres integrado en este modo (recomendado para entorno cercano a prod).
- Reinicio automatico `unless-stopped`.

## Variables de entorno

Usa `.env.example` como plantilla.

Claves importantes:
- `STREAMFUSE_DATABASE_URL`: DB en desarrollo (normalmente SQLite).
- `STREAMFUSE_TAUTULLI_USE_MOCK`, `STREAMFUSE_SFTPGO_USE_MOCK`: habilitan providers mock.
- `STREAMFUSE_AUTO_SEED_MOCK`: siembra sesiones mock automaticamente al arrancar backend (dev).
- VITE_API_BASE: base URL consumida por frontend.
- STREAMFUSE_DATABASE_URL_PROD, STREAMFUSE_AUTO_SEED_MOCK_PROD: overrides usados por docker-compose.prod.yml.

## Estructura relevante

- `backend/`: FastAPI, adapters, servicios, persistencia, migraciones.
- `frontend/`: React + Vite + TypeScript + Tailwind.
- `docker/`: Dockerfiles multistage, Nginx config, entrypoint backend.
- `scripts/`: bootstrap dev/prod.

## Comandos utiles

```bash
# Parar todo
docker compose down

# Ver logs backend
docker compose logs -f backend

# Ver logs frontend
docker compose logs -f frontend
```


## Publish helper scripts

- `scripts/publish-github.ps1`
- `scripts/publish-dockerhub.ps1`

### GitHub

```powershell
./scripts/publish-github.ps1 -RepoUrl "https://github.com/<user>/<repo>.git" -Branch "main"
```

### Docker Hub

```powershell
docker login
./scripts/publish-dockerhub.ps1 -DockerUser "<dockerhub-user>" -Tag "v0.3.0"
```


## Operacion Unraid

Guia operativa completa (scripts Samba/SFTPGo/metricas, persistencia y troubleshooting):

- [docs/UNRAID_OPERATIONS_RUNBOOK.md](docs/UNRAID_OPERATIONS_RUNBOOK.md)

