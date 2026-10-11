# Milestone 13: Observability, Metrics & Telemetry (Prometheus & Grafana)

> **Milestone ID:** `M13-OBSERVABILITY-MONITORING`  
> **Status:** Completed  
> **Date:** 2026-10-11  
> **Framework:** Prometheus 2.54, Grafana 11.2, Prometheus Client Python, PromQL, Automated Alerting  
> **Infrastructure Directory:** `infrastructure/observability/`  
> **SLA Monitoring Target:** Sub-5ms hard threshold ($P(99) < 0.005\,\text{s}$)  
> **Test Coverage:** 7 Automated Tests in `tests/infrastructure/test_observability.py` (90 Total Passing Tests)  

---

## 1. Objective & Motivation

Operating predictive intelligence models in real-world environments requires deep operational transparency. If an inference model begins suffering latency spikes (> 5 ms) or experiences feature/concept drift that silently flags half the fleet for failure, engineers must be alerted instantly before operations are impaired.

Milestone 13 establishes the **DataMind Enterprise Observability & Monitoring Stack**:
1. **Prometheus Metrics Instrumentation:** Embedded Prometheus exporter in `services/observability.py` exposing standardized `/metrics` endpoints across all 4 distributed microservices (`DataMind.Prediction`, `DataMind.Api`, `DataMind.Ingestion`, and `DataMind.Dashboard`).
2. **Model SLA & Operational Performance Metrics:** Real-time histograms and counters tracking:
   - `datamind_prediction_latency_seconds`: Multi-bucket histogram tracking p50, p90, p95, and p99 against the $< 5\,\text{ms}$ SLA target.
   - `datamind_prediction_risk_probability`: Distribution of scored failure probabilities [0.0 - 1.0].
   - `datamind_predictions_total`: Continuous classification count by risk severity (`HIGH` vs `NOMINAL`).
   - `datamind_stream_buffer_depth`: Buffer queue depth and processing backpressure.
   - `http_requests_total` & `http_request_duration_seconds`: Golden signals for request rates, durations, and HTTP errors (4xx/5xx).
3. **Automated Prometheus Alerting Rules (`alerts.yml`):** Production alerting thresholds for:
   - **PredictionLatencySlaBreached:** Critical alert when p99 latency exceeds 5 ms for 30s.
   - **HighRiskFailureCascadeSpike:** Warning alert when >30% of fleet devices score as high risk in a 5-minute window (drift/cascade detector).
   - **CoreApiHighErrorRate:** Critical alert when 5xx response rate exceeds 1%.
   - **IngestionQueueCongestionBackpressure:** Warning alert when event queue buffer exceeds 5,000 unconsumed observations.
   - **MicroserviceInstanceDown:** Critical infrastructure alert when any service target drops.
4. **Grafana Dashboards & Auto-Provisioning:** Ready-to-run executive monitoring dashboard (`datamind_fleet_overview.json`) with SLA gauges, throughput timeseries, donut risk charts, and service mesh health matrices.

---

## 2. Distributed Observability Topology

```
                  ┌────────────────────────┐      ┌────────────────────────┐
                  │  datamind-prediction   │      │      datamind-api      │
                  │   :8000/metrics        │      │      :8001/metrics     │
                  └───────────┬────────────┘      └───────────┬────────────┘
                              │                               │
                              │ (Scrape: 5s)                  │ (Scrape: 5s)
                              ▼                               ▼
                      ┌──────────────────────────────────────────────┐
                      │             Prometheus 2.54                  │
                      │               Port: 9090                     │
                      │  - Scrapes endpoints                         │
                      │  - Evaluates alerts.yml                      │
                      │  - Stores time-series data                   │
                      └───────┬──────────────────────────────▲───────┘
                              │                              │
                              │ (PromQL Proxy Query)         │ (Scrape: 5s)
                              ▼                              │
                      ┌────────────────────────┐   ┌─────────┴──────────────┐
                      │      Grafana 11.2      │   │   datamind-ingestion   │
                      │       Port: 3000       │   │   datamind-dashboard   │
                      │  - Executive Dashboard │   │      :8002 & :8080     │
                      │  - SLA Gauges & Donut  │   └────────────────────────┘
                      └────────────────────────┘
```

---

## 3. Prometheus Metrics Catalog

The metrics engine in [`services/observability.py`](../../services/observability.py) standardizes metric naming across the platform:

| Metric Name | Type | Labels | Description |
| :--- | :---: | :--- | :--- |
| `datamind_prediction_latency_seconds` | Histogram | `model_name` | Model scoring latency in seconds. SLA target $< 0.005\,\text{s}$. |
| `datamind_prediction_risk_probability` | Histogram | `model_name` | Probability distribution [0.0 - 1.0]. |
| `datamind_predictions_total` | Counter | `model_name`, `risk_level` | Total inference predictions scored by risk level (`HIGH`, `NOMINAL`). |
| `datamind_stream_buffer_depth` | Gauge | — | Backpressure indicator for sliding window queue. |
| `datamind_active_devices` | Gauge | — | Total managed fleet device count. |
| `datamind_active_alerts` | Gauge | `severity` | Open failure incidents count by severity (`CRITICAL`, `WARNING`). |
| `http_requests_total` | Counter | `service`, `method`, `endpoint`, `status_code` | HTTP traffic throughput and response codes. |
| `http_request_duration_seconds` | Histogram | `service`, `method`, `endpoint` | End-to-end HTTP processing latency. |

---

## 4. Prometheus Alerting Rules Specification

Configured in [`infrastructure/observability/prometheus/alerts.yml`](../../infrastructure/observability/prometheus/alerts.yml):

```yaml
groups:
  - name: datamind_sla_and_model_alerts
    rules:
      - alert: PredictionLatencySlaBreached
        expr: histogram_quantile(0.99, rate(datamind_prediction_latency_seconds_bucket[1m])) > 0.005
        for: 30s
        labels: { severity: critical, tier: inference }

      - alert: HighRiskFailureCascadeSpike
        expr: rate(datamind_predictions_total{risk_level="HIGH"}[5m]) / rate(datamind_predictions_total[5m]) > 0.30
        for: 1m
        labels: { severity: warning, tier: mlops }

      - alert: CoreApiHighErrorRate
        expr: sum(rate(http_requests_total{status_code=~"5.."}[2m])) / sum(rate(http_requests_total[2m])) > 0.01
        for: 1m
        labels: { severity: critical, tier: persistence }

      - alert: IngestionQueueCongestionBackpressure
        expr: datamind_stream_buffer_depth > 5000
        for: 45s
        labels: { severity: warning, tier: stream-processing }

      - alert: MicroserviceInstanceDown
        expr: up == 0
        for: 30s
        labels: { severity: critical, tier: infrastructure }
```

---

## 5. Automated Verification & Test Suite

The test suite in [`tests/infrastructure/test_observability.py`](../../tests/infrastructure/test_observability.py) validates the entire monitoring subsystem:

1. `test_prometheus_config_valid_yaml`: Validates YAML syntax, scrape interval (5s), target endpoints, and rule file references.
2. `test_prometheus_alerts_valid_yaml_and_rules`: Confirms rule groups, PromQL formulas, and critical/warning severity tags.
3. `test_grafana_datasource_provisioning`: Confirms auto-provisioned Prometheus datasource pointing to port 9090.
4. `test_grafana_dashboard_provisioning`: Validates provider folder mapping.
5. `test_grafana_fleet_dashboard_json_schema`: Validates dashboard JSON schema, panel configurations, and SLA gauges.
6. `test_docker_compose_includes_observability_services`: Ensures `prometheus` (port 9090) and `grafana` (port 3000) are joined to `datamind_network`.
7. `test_application_metrics_endpoint_integration`: Exercises `setup_metrics()` on FastAPI instances and verifies valid Prometheus exposition text.

```text
tests.infrastructure.test_observability
  - test_application_metrics_endpoint_integration: Verifies FastAPI metrics emission. [OK]
  - test_docker_compose_includes_observability_services: Verifies compose mesh inclusion. [OK]
  - test_grafana_dashboard_provisioning: Verifies dashboard provider config. [OK]
  - test_grafana_datasource_provisioning: Verifies datasource config. [OK]
  - test_grafana_fleet_dashboard_json_schema: Verifies dashboard JSON structure. [OK]
  - test_prometheus_alerts_valid_yaml_and_rules: Verifies PromQL alert rules. [OK]
  - test_prometheus_config_valid_yaml: Verifies scrape targets and config. [OK]

----------------------------------------------------------------------
Ran 7 tests in 0.079s — ALL 7 TESTS PASSED (OK)
Total Repository Suite: 90 Tests Passing (100% Green)
```

---

## 6. Accessing Observability Consoles

When orchestrated via `docker compose up -d`:
- **Prometheus UI & Targets:** `http://localhost:9090/targets`
- **Prometheus Alert Rules:** `http://localhost:9090/alerts`
- **Grafana Executive Dashboards:** `http://localhost:3000` (User: `admin`, Password: `admin`)
