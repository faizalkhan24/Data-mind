# Milestone 12: Containerization & Local Orchestration (Docker & Compose)

> **Milestone ID:** `M12-DOCKER-CONTAINERIZATION`  
> **Status:** Completed  
> **Date:** 2026-10-11  
> **Framework:** Docker, Docker Compose (v3.9 Specification), Multi-Stage OCI Images, Alpine Linux, PostgreSQL 16, Redis 7  
> **Infrastructure Directory:** `infrastructure/docker/` and root `docker-compose.yml`  
> **Test Coverage:** 9 Automated Tests in `tests/infrastructure/test_docker_configurations.py` (83 Total Passing Tests)  

---

## 1. Objective & Motivation

Moving a distributed machine learning platform from individual developer host processes into reliable, repeatable production requires complete container isolation, standardized runtime environments, reproducible builds, and seamless single-command orchestration.

Milestone 12 delivers production-ready containerization and orchestration across the entire DataMind ecosystem:
1. **Multi-Stage Docker Builds:** Optimized two-stage builds (`builder` $\to$ `runner`) based on `python:3.11-slim`, separating build-time compilers and wheels from lean runtime containers.
2. **Container Security Best Practices:** Enforces unprivileged execution via non-root user `datamind` (UID `10001`), immutable layer caches, and strict `.dockerignore` file filtering.
3. **Automated Health Probing:** Embeds container-native `HEALTHCHECK` directives into every Dockerfile, enabling orchestration schedulers to detect and recover from stalled processes.
4. **Master Multi-Container Orchestration:** Single-command local deployment (`docker compose up -d`) orchestrating 6 interdependent services:
   - **PostgreSQL 16:** Relational fleet state and audit ledger with persistent volume (`datamind_pgdata`).
   - **Redis 7:** High-throughput telemetry sliding window event cache with persistent volume (`datamind_redisdata`).
   - **DataMind.Prediction:** Real-time XGBoost inference and SHAP explainability engine (< 5 ms SLA).
   - **DataMind.Api:** Core fleet management, telemetry ingestion, and failure alerting REST API.
   - **DataMind.Ingestion:** Asynchronous queue worker and real-time sliding window feature calculation engine.
   - **DataMind.Dashboard:** Web operations console and interactive diagnostic simulation sandbox.
5. **Network Isolation & Inter-Service Discovery:** Dedicated isolated bridge network (`datamind_network`) with DNS-based container discovery and health-dependent startup sequencing (`condition: service_healthy`).

---

## 2. Containerized Mesh Topology & Architecture

```
                                Operations Engineer / Browser
                                              │
                                              ▼ (Port 8080)
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                   datamind_network (Bridge)                               │
│                                                                                           │
│   ┌───────────────────────────┐                   ┌───────────────────────────┐           │
│   │     datamind-dashboard    │                   │     datamind-prediction   │           │
│   │    (Port 8080 / FastAPI)  ├──────────────────►│    (Port 8000 / FastAPI)  │           │
│   └─────────────┬─────────────┘                   └─────────────▲─────────────┘           │
│                 │                                               │                         │
│                 ▼                                               │ (Real-Time Scoring)     │
│   ┌───────────────────────────┐                   ┌─────────────┴─────────────┐           │
│   │        datamind-api       │◄──────────────────┤     datamind-ingestion    │           │
│   │    (Port 8001 / FastAPI)  │  (Persist State)  │    (Port 8002 / FastAPI)  │           │
│   └─────────────┬─────────────┘                   └─────────────┬─────────────┘           │
│                 │                                               │                         │
│                 ▼                                               ▼                         │
│   ┌───────────────────────────┐                   ┌───────────────────────────┐           │
│   │     datamind-postgres     │                   │       datamind-redis      │           │
│   │   (Port 5432 / PG 16)     │                   │     (Port 6379 / Redis 7) │           │
│   │  Volume: datamind_pgdata  │                   │ Volume: datamind_redisdata│           │
│   └───────────────────────────┘                   └───────────────────────────┘           │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Multi-Stage Dockerfile Specifications

Each microservice utilizes a dedicated multi-stage Dockerfile located in `infrastructure/docker/`:

| Dockerfile | Base Image | Ports | User | Health Check Endpoint | Target Service |
| :--- | :--- | :---: | :---: | :--- | :--- |
| [`Dockerfile.prediction`](../../infrastructure/docker/Dockerfile.prediction) | `python:3.11-slim` | `8000` | `datamind` (10001) | `curl -f http://localhost:8000/health` | Real-time failure inference & SHAP |
| [`Dockerfile.api`](../../infrastructure/docker/Dockerfile.api) | `python:3.11-slim` | `8001` | `datamind` (10001) | `curl -f http://localhost:8001/health` | Fleet persistence, history & alerts |
| [`Dockerfile.ingestion`](../../infrastructure/docker/Dockerfile.ingestion) | `python:3.11-slim` | `8002` | `datamind` (10001) | `curl -f http://localhost:8002/health` | Sliding window queue worker |
| [`Dockerfile.dashboard`](../../infrastructure/docker/Dockerfile.dashboard) | `python:3.11-slim` | `8080` | `datamind` (10001) | `curl -f http://localhost:8080/health` | Operations console & diagnostic UI |

### Security & Build Optimizations
* **Minimal Base:** `python:3.11-slim` minimizes package surface area while preserving Debian glibc compatibility required by XGBoost and NumPy.
* **Separation of Concerns:** Build tools (`build-essential`) are strictly restricted to the `builder` stage and excluded from runtime images.
* **Non-Root Execution:** Running under non-root user `datamind` prevents privilege escalation container escape vulnerabilities.
* **Deterministic Environment:** `PYTHONUNBUFFERED=1` and `PYTHONPATH=/app` are standardized across all images.

---

## 4. Docker Compose Orchestration & Service Matrix

The master deployment file [`docker-compose.yml`](../../docker-compose.yml) coordinates the entire distributed stack:

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    container_name: datamind-postgres
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./infrastructure/docker/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d datamind"]

  redis:
    image: redis:7-alpine
    container_name: datamind-redis
    ports: ["6379:6379"]
    volumes:
      - redisdata:/data

  prediction:
    build:
      context: .
      dockerfile: infrastructure/docker/Dockerfile.prediction
    container_name: datamind-prediction
    ports: ["8000:8000"]

  api:
    build:
      context: .
      dockerfile: infrastructure/docker/Dockerfile.api
    container_name: datamind-api
    ports: ["8001:8001"]
    depends_on:
      postgres: { condition: service_healthy }

  ingestion:
    build:
      context: .
      dockerfile: infrastructure/docker/Dockerfile.ingestion
    container_name: datamind-ingestion
    ports: ["8002:8002"]
    depends_on:
      prediction: { condition: service_healthy }
      api: { condition: service_healthy }

  dashboard:
    build:
      context: .
      dockerfile: infrastructure/docker/Dockerfile.dashboard
    container_name: datamind-dashboard
    ports: ["8080:8080"]
    depends_on:
      api: { condition: service_healthy }
      prediction: { condition: service_healthy }
```

---

## 5. Automated Verification & Test Suite

The test suite in [`tests/infrastructure/test_docker_configurations.py`](../../tests/infrastructure/test_docker_configurations.py) provides comprehensive automated validation:

1. `test_dockerfiles_exist`: Verifies existence of all 4 microservice Dockerfiles.
2. `test_dockerfiles_multi_stage_structure`: Validates multi-stage `builder` and `runner` patterns.
3. `test_dockerfiles_security_non_root_user`: Enforces non-root user creation (`datamind`, UID `10001`).
4. `test_dockerfiles_healthcheck_directive`: Confirms presence of automated `HEALTHCHECK` instructions.
5. `test_dockerfiles_ports_and_cmd`: Validates that `EXPOSE` directives and entrypoints match ports 8000, 8001, 8002, and 8080.
6. `test_docker_compose_valid_yaml_and_services`: Parses Compose YAML and validates all 6 required services.
7. `test_docker_compose_service_dependencies_and_health`: Validates dependency DAG ordering and healthcheck gates.
8. `test_docker_compose_network_and_volume_topologies`: Verifies bridge network isolation and named volume persistence.
9. `test_dockerignore_compliance`: Verifies exclusion of `.git`, `.venv`, cache files, and training databases.

```text
tests.infrastructure.test_docker_configurations
  - test_docker_compose_network_and_volume_topologies: Verifies network and volume specs. [OK]
  - test_docker_compose_service_dependencies_and_health: Verifies dependency DAG. [OK]
  - test_docker_compose_valid_yaml_and_services: Verifies YAML syntax and services. [OK]
  - test_dockerfiles_exist: Verifies all Dockerfile assets exist. [OK]
  - test_dockerfiles_healthcheck_directive: Verifies container healthcheck probes. [OK]
  - test_dockerfiles_multi_stage_structure: Verifies multi-stage build patterns. [OK]
  - test_dockerfiles_ports_and_cmd: Verifies port bindings and entrypoints. [OK]
  - test_dockerfiles_security_non_root_user: Verifies unprivileged execution. [OK]
  - test_dockerignore_compliance: Verifies ignore rules. [OK]

----------------------------------------------------------------------
Ran 9 tests in 0.033s — ALL 9 TESTS PASSED (OK)
Total Repository Suite: 83 Tests Passing (100% Green)
```

---

## 6. Deployment Quickstart

```powershell
# 1. Copy environment template
cp .env.example .env

# 2. Build and start all 6 services in background
docker compose up --build -d

# 3. Verify health status of all containers
docker compose ps

# 4. Stream real-time logs across the service mesh
docker compose logs -f

# 5. Access services:
# - Dashboard UI:      http://localhost:8080
# - Core Persistence:  http://localhost:8001/docs
# - Ingestion Stream:  http://localhost:8002/docs
# - Prediction Model:  http://localhost:8000/docs
# - PostgreSQL:        localhost:5432 (datamind)
# - Redis:             localhost:6379

# 6. Stop and clean up containers
docker compose down
```
