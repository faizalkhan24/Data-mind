"""
DataMind Executive Presentation Generator
=========================================
Generates a 14-slide 16:9 widescreen presentation in PowerPoint (.pptx) format
covering the architecture, capabilities, ML benchmarks, infrastructure,
and operational workflows of the DataMind platform.
"""

from pathlib import Path
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

OUTPUT_FILE = Path(__file__).resolve().parent / "DataMind_Presentation.pptx"

# Theme Palette (Modern Deep Tech Aesthetic)
COLOR_BG_DARK = RGBColor(15, 23, 42)        # Slate 900
COLOR_CARD_BG = RGBColor(30, 41, 59)        # Slate 800
COLOR_CARD_BORDER = RGBColor(51, 65, 85)    # Slate 700
COLOR_TEXT_WHITE = RGBColor(248, 250, 252)  # Slate 50
COLOR_TEXT_MUTED = RGBColor(148, 163, 184)  # Slate 400
COLOR_PRIMARY = RGBColor(56, 189, 248)      # Cyan 400
COLOR_ACCENT_GREEN = RGBColor(52, 211, 153) # Emerald 400
COLOR_ACCENT_ROSE = RGBColor(244, 63, 94)   # Rose 500
COLOR_ACCENT_AMBER = RGBColor(251, 191, 36) # Amber 400


def create_presentation():
    prs = Presentation()
    # 16:9 Widescreen standard dimensions
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def add_slide_background(slide):
        bg = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height
        )
        bg.fill.solid()
        bg.fill.fore_color.rgb = COLOR_BG_DARK
        bg.line.color.rgb = COLOR_BG_DARK
        return bg

    def add_header(slide, title_text, category_text="DATAMIND ARCHITECTURE & CAPABILITIES"):
        # Category Eyebrow
        tx_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.4))
        tf = tx_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p_cat = tf.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.size = Pt(11)
        p_cat.font.bold = True
        p_cat.font.color.rgb = COLOR_PRIMARY
        p_cat.font.name = "Segoe UI"

        # Main Title
        tx_box_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.7), Inches(0.7))
        tf_title = tx_box_title.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        p_title.text = title_text
        p_title.font.size = Pt(24)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_TEXT_WHITE
        p_title.font.name = "Segoe UI"

    def add_card(slide, left, top, width, height, title, items, badge=""):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_CARD_BG
        card.line.color.rgb = COLOR_CARD_BORDER
        card.line.width = Pt(1)

        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.25)
        tf.margin_right = Inches(0.25)
        tf.margin_top = Inches(0.2)
        tf.margin_bottom = Inches(0.2)

        # Title
        p_title = tf.paragraphs[0]
        p_title.text = title
        p_title.font.size = Pt(16)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_PRIMARY
        p_title.font.name = "Segoe UI"

        if badge:
            p_badge = tf.add_paragraph()
            p_badge.text = badge
            p_badge.font.size = Pt(10)
            p_badge.font.bold = True
            p_badge.font.color.rgb = COLOR_ACCENT_GREEN
            p_badge.font.name = "Segoe UI"
            p_badge.space_after = Pt(8)

        for item in items:
            p = tf.add_paragraph()
            p.text = f"•  {item}"
            p.font.size = Pt(12)
            p.font.color.rgb = COLOR_TEXT_WHITE
            p.font.name = "Segoe UI"
            p.space_after = Pt(6)

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    add_slide_background(s1)

    # Accent decorative glow bar
    bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.8), Inches(0.15), Inches(3.6))
    bar.fill.solid()
    bar.fill.fore_color.rgb = COLOR_PRIMARY
    bar.line.color.rgb = COLOR_PRIMARY

    tx_s1 = s1.shapes.add_textbox(Inches(1.2), Inches(1.7), Inches(11.2), Inches(3.8))
    tf_s1 = tx_s1.text_frame
    tf_s1.word_wrap = True

    p_badge = tf_s1.paragraphs[0]
    p_badge.text = "ENTERPRISE PREDICTIVE INTELLIGENCE PLATFORM (V1.0.0.0)"
    p_badge.font.size = Pt(12)
    p_badge.font.bold = True
    p_badge.font.color.rgb = COLOR_ACCENT_GREEN
    p_badge.font.name = "Segoe UI"

    p_main = tf_s1.add_paragraph()
    p_main.text = "DataMind"
    p_main.font.size = Pt(54)
    p_main.font.bold = True
    p_main.font.color.rgb = COLOR_TEXT_WHITE
    p_main.font.name = "Segoe UI"
    p_main.space_after = Pt(4)

    p_sub = tf_s1.add_paragraph()
    p_sub.text = "IoT Hardware Failure Prevention, Ultra-Low Latency Inference & Game-Theoretic Explainability"
    p_sub.font.size = Pt(20)
    p_sub.font.color.rgb = COLOR_PRIMARY
    p_sub.font.name = "Segoe UI"
    p_sub.space_after = Pt(24)

    p_desc = tf_s1.add_paragraph()
    p_desc.text = "A production-grade distributed intelligence system engineered to Google SWE standards.\nIngests real-time telemetry, computes zero-leakage temporal features, predicts failures 24h ahead (<0.4ms),\nand pinpoints mechanical root causes via SHAP."
    p_desc.font.size = Pt(13)
    p_desc.font.color.rgb = COLOR_TEXT_MUTED
    p_desc.font.name = "Segoe UI"

    # Footer Metadata Card
    fcard = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(6.0), Inches(11.7), Inches(0.9))
    fcard.fill.solid()
    fcard.fill.fore_color.rgb = COLOR_CARD_BG
    fcard.line.color.rgb = COLOR_CARD_BORDER
    ftf = fcard.text_frame
    ftf.margin_left = Inches(0.3)
    ftf.margin_top = Inches(0.2)
    fp = ftf.paragraphs[0]
    fp.text = "Architect: Faizal Khan   |   Repository: github.com/faizalkhan24/Data-mind   |   14/14 Milestones Complete (100%)   |   98 Passing Tests"
    fp.font.size = Pt(11)
    fp.font.color.rgb = COLOR_TEXT_WHITE
    fp.font.name = "Segoe UI"

    # =========================================================================
    # SLIDE 2: Executive Summary & The Core Challenge
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_slide_background(s2)
    add_header(s2, "Executive Overview: Solving Unplanned Industrial Downtime")

    add_card(
        s2, Inches(0.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "1. The Problem",
        [
            "Industrial fleets face massive costs from unplanned hardware outages ($50k+/hr).",
            "Traditional systems are reactive: alarms trigger only after irreversible damage occurs.",
            "Raw accuracy is misleading due to severe class imbalance (7.35% failure rate).",
            "Lack of root-cause transparency leads to hours of diagnostic guesswork."
        ],
        badge="THE INDUSTRIAL CHALLENGE"
    )

    add_card(
        s2, Inches(4.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "2. The Objective",
        [
            "Predict whether an active device will fail in the next 24h (failed_within_24h).",
            "Provide sub-5ms inference latency to support streaming fleets in real-time.",
            "Generate game-theoretic SHAP attributions explaining WHY each device will fail.",
            "Trigger automated ticketing and alerts before catastrophic outages occur."
        ],
        badge="PREDICTIVE INTELLIGENCE"
    )

    add_card(
        s2, Inches(8.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "3. Key Results Achieved",
        [
            "PR-AUC: 0.9608 and 93.9% failure recall on unseen test fleet (15k observations).",
            "Inference SLA: ~0.40 ms (~400 microseconds), 12x faster than the 5ms SLA budget.",
            "Full Distributed Mesh: 4 microservices, Postgres, Redis, Prometheus, Grafana.",
            "100% Test Coverage: 98 unit & integration tests passing with zero failures."
        ],
        badge="PRODUCTION BENCHMARK"
    )

    # =========================================================================
    # SLIDE 3: System Architecture
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_slide_background(s3)
    add_header(s3, "End-to-End Distributed Microservices Mesh")

    add_card(
        s3, Inches(0.8), Inches(1.8), Inches(2.75), Inches(4.8),
        "Ingestion Service",
        [
            "Port: 8002",
            "High-throughput non-blocking telemetry event queue.",
            "24-hour temporal sliding window buffer per device.",
            "Computes 25 rolling signals with zero future leakage.",
            "Async batch forwarding to inference & persistence."
        ],
        badge="DATA STREAMING (:8002)"
    )

    add_card(
        s3, Inches(3.8), Inches(1.8), Inches(2.75), Inches(4.8),
        "Prediction Engine",
        [
            "Port: 8000",
            "FastAPI inference server with in-memory model cache.",
            "XGBoost gradient boosting classifier (tuned threshold 0.7173).",
            "Embedded SHAP TreeExplainer for instant risk factor attribution.",
            "Latency: 0.40 ms (SLA < 5 ms)."
        ],
        badge="ML INFERENCE (:8000)"
    )

    add_card(
        s3, Inches(6.8), Inches(1.8), Inches(2.75), Inches(4.8),
        "Fleet API Service",
        [
            "Port: 8001",
            "SQLAlchemy 2.0 async engine (PostgreSQL 16 & SQLite).",
            "Device registration, metadata CRUD, and observation logging.",
            "Automated alert creation upon high-risk predictions.",
            "Fleet aggregate health stats."
        ],
        badge="DATA SYSTEMS (:8001)"
    )

    add_card(
        s3, Inches(9.8), Inches(1.8), Inches(2.75), Inches(4.8),
        "Operations Console",
        [
            "Port: 8003",
            "Live Web Operations Console & Interactive Risk Grid.",
            "Slide-out diagnostic drawer with historical sensor trends.",
            "Real-time diagnostic simulator for sensor surge testing.",
            "Prometheus & Grafana telemetry."
        ],
        badge="WEB CONSOLE (:8003)"
    )

    # =========================================================================
    # SLIDE 4: Physics-Grounded Data Generation
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_slide_background(s4)
    add_header(s4, "Physics-Grounded Simulation vs Naive Random Noise")

    add_card(
        s4, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8),
        "Coupled Physical Failure Kinetics",
        [
            "Thermal Runaway: Internal resistance elevates die temperature by up to +45°C (peaking at 92.3°C).",
            "Current Draw Surge: Circuit wear drives current from nominal 1.2A up to 2.8A.",
            "Power Rail Droop: High current induces severe internal IR drops, sagging battery voltage to 2.8V.",
            "Error Acceleration: Thermal noise triggers Poisson error bursts (up to 31 errors/hr).",
            "Watchdog Crash Loops: Voltage drops trigger hardware reboots, resetting uptime_hours to near zero."
        ],
        badge="REALISTIC SENSOR BEHAVIOR"
    )

    add_card(
        s4, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8),
        "13-Rule Pre-ML Quality Assurance",
        [
            "Schema Enforcement: Validates data types, ranges, and null counts across all 100k rows.",
            "Physical Boundary Audit: Flags impossible sensor values (e.g., negative voltage, temp > 150°C).",
            "Temporal Continuity: Verifies 1-hour uniform cadence without missing timesteps.",
            "Label Validity: Verifies ground truth failed_within_24h aligns strictly with failure timestamps.",
            "Class Imbalance Audit: Confirms 7.35% realistic fleet failure prevalence (12.6:1 negative ratio)."
        ],
        badge="AUTOMATED VALIDATION GATE"
    )

    # =========================================================================
    # SLIDE 5: Zero-Leakage Feature Engineering
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_slide_background(s5)
    add_header(s5, "Zero-Leakage Temporal Feature Pipeline")

    add_card(
        s5, Inches(0.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "Rolling Statistics",
        [
            "1-Hour, 6-Hour & 24-Hour Windows",
            "temperature_mean_6h & std_6h",
            "voltage_min_6h (sag detector)",
            "current_mean_6h & max_6h",
            "Captures short-term spikes vs sustained thermal saturation."
        ],
        badge="MULTI-HORIZON SIGNALS"
    )

    add_card(
        s5, Inches(4.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "Rate-of-Change Signals",
        [
            "First-Order Temporal Differencing",
            "battery_change_24h (rapid drain rate)",
            "temperature_diff_1h (rate of rise)",
            "voltage_diff_1h (drop rate)",
            "Differentiates steady aging from acute catastrophic runaway."
        ],
        badge="DEGRADATION DYNAMICS"
    )

    add_card(
        s5, Inches(8.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "Causal Split Guarantee",
        [
            "Zero Information Leakage",
            "Features at time t strictly use sensor readings from tau <= t.",
            "Group-Aware Fleet Split: 70% Train (700 devices), 15% Val (150 devices), 15% Test (150 devices).",
            "Prevents cross-device correlation bleed."
        ],
        badge="GROUP-AWARE SPLIT"
    )

    # =========================================================================
    # SLIDE 6: Model Benchmark & Evaluation
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_slide_background(s6)
    add_header(s6, "Machine Learning Progression: Benchmark on Holdout Fleet")

    # Table of Model Comparison
    table_shape = s6.shapes.add_table(5, 7, Inches(0.8), Inches(1.8), Inches(11.7), Inches(2.6))
    table = table_shape.table
    table.columns[0].width = Inches(2.3)
    table.columns[1].width = Inches(1.5)
    table.columns[2].width = Inches(1.5)
    table.columns[3].width = Inches(1.5)
    table.columns[4].width = Inches(1.5)
    table.columns[5].width = Inches(1.7)
    table.columns[6].width = Inches(1.7)

    headers = ["Model", "Threshold", "Precision", "Recall", "F1-Score", "PR-AUC", "Latency"]
    for col_idx, h in enumerate(headers):
        cell = table.cell(0, col_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = COLOR_CARD_BG
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.bold = True
        p.font.size = Pt(12)
        p.font.color.rgb = COLOR_PRIMARY
        p.font.name = "Segoe UI"

    rows_data = [
        ["Majority Dummy", "0.50", "0.00%", "0.00%", "0.0000", "0.0654", "< 1 µs"],
        ["Logistic Regression", "0.24", "95.81%", "93.17%", "0.9447", "0.9625", "0.36 ms"],
        ["Random Forest (150)", "0.39", "94.14%", "95.01%", "0.9457", "0.9671", "26.18 ms"],
        ["XGBoost Champion", "0.72", "94.46%", "93.88%", "0.9417", "0.9608", "0.40 ms"],
    ]

    for row_idx, r in enumerate(rows_data, start=1):
        for col_idx, val in enumerate(r):
            cell = table.cell(row_idx, col_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = COLOR_CARD_BG if row_idx % 2 == 0 else COLOR_BG_DARK
            p = cell.text_frame.paragraphs[0]
            p.text = val
            p.font.size = Pt(11)
            p.font.name = "Segoe UI"
            if row_idx == 4:
                p.font.bold = True
                p.font.color.rgb = COLOR_ACCENT_GREEN
            else:
                p.font.color.rgb = COLOR_TEXT_WHITE

    # Key takeaways card
    add_card(
        s6, Inches(0.8), Inches(4.7), Inches(11.7), Inches(1.9),
        "Strategic Model Selection Insights",
        [
            "PR-AUC Primacy: On 7.35% class imbalance, accuracy is misleading (Dummy gets 93.5% with 0 recall). PR-AUC proves true discriminatory capability.",
            "XGBoost Chosen for Production: Delivers near-identical PR-AUC to Random Forest (0.9608 vs 0.9671) while executing 65x faster (0.40ms vs 26.18ms).",
            "Optimal Threshold Tuning: Tuning decision threshold to tau = 0.7173 achieves optimal balance between precision (94.5%) and recall (93.9%)."
        ],
        badge="PRODUCTION TRADEOFF ANALYSIS"
    )

    # =========================================================================
    # SLIDE 7: Explainable AI (SHAP)
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_slide_background(s7)
    add_header(s7, "Explainable AI (XAI): SHAP Game-Theoretic Attribution")

    add_card(
        s7, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8),
        "Why Black-Box Models Fail in Ops",
        [
            "Telling an engineer 'Risk is 88%' is useless without root causes.",
            "Without attribution, technicians spend hours testing components randomly.",
            "DataMind embeds SHAP TreeExplainer directly into the FastAPI serving layer.",
            "Every prediction calculates exact Shapley values across all 25 features in sub-millisecond time.",
            "Translates raw feature names into human-understandable mechanical categories."
        ],
        badge="EXPLAINABLE INTELLIGENCE"
    )

    add_card(
        s7, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8),
        "Top Human Risk Factor Categories",
        [
            "Thermal Runaway: Die temperature sustained above safe thresholds (+0.28 log-odds impact).",
            "Power Rail Sag: Internal battery impedance collapsing voltage under load (+0.19 log-odds).",
            "Rapid Battery Depletion: Accelerated charge loss over 24 hours (+0.34 log-odds).",
            "Electrical Jitter: High voltage variance and power instability (+0.86 log-odds).",
            "Watchdog Crash Loops: Repetitive restarts resetting uptime (+0.45 log-odds)."
        ],
        badge="ROOT-CAUSE ATTRIBUTION"
    )

    # =========================================================================
    # SLIDE 8: Real-Time Prediction API
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_slide_background(s8)
    add_header(s8, "Real-Time Prediction API: Architecture & SLA")

    add_card(
        s8, Inches(0.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "Sub-5ms Latency SLA",
        [
            "SLA Contract: P99 < 5.0 ms",
            "Actual Latency: ~0.40 ms (400 µs)",
            "12x headroom under latency SLA budget.",
            "In-memory model weights eliminate disk I/O.",
            "Non-blocking async request lifecycle."
        ],
        badge="PERFORMANCE CRITICAL"
    )

    add_card(
        s8, Inches(4.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "REST API Endpoints",
        [
            "POST /api/v1/predict: Single device prediction + SHAP explainability.",
            "POST /api/v1/predict/batch: High-throughput batch scoring (500 devices in < 30ms).",
            "GET /api/v1/model/metadata: Model version, feature count, threshold config.",
            "GET /health: Kubernetes liveness & readiness."
        ],
        badge="FASTAPI MICROSERVICE"
    )

    add_card(
        s8, Inches(8.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "Pydantic Validation",
        [
            "Strict Input Validation: Validates physical sensor ranges before inference.",
            "Structured Error Handling: 422 Unprocessable Entity with exact error traces.",
            "Comprehensive Swagger Docs: Auto-generated OpenAPI docs at /docs.",
            "Prometheus metrics at /metrics."
        ],
        badge="ENTERPRISE STANDARDS"
    )

    # =========================================================================
    # SLIDE 9: Operations Dashboard (Web UI)
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_slide_background(s9)
    add_header(s9, "Fleet Health Operations Console: Web UI & Simulator")

    add_card(
        s9, Inches(0.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "Executive KPI Bar",
        [
            "Total Monitored Fleet: 1,000 devices.",
            "Active Nodes vs Maintenance.",
            "High-Risk Count: Devices with impending 24h failure.",
            "Open Incidents & Critical Alert count.",
            "Zero external UI frameworks (pure lightweight vanilla JS/CSS3)."
        ],
        badge="FLEET HEALTH VISIBILITY"
    )

    add_card(
        s9, Inches(4.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "Interactive Fleet Grid",
        [
            "Live sorting by failure probability.",
            "Filter by risk severity (HIGH RISK vs NOMINAL).",
            "Real-time sensor telemetry badges (Temperature, Voltage, Battery).",
            "One-click [Diagnose] button to expand device inspection drawer."
        ],
        badge="LIVE OPERATIONS GRID"
    )

    add_card(
        s9, Inches(8.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "Diagnostic Simulator",
        [
            "Live What-If Analysis in Browser.",
            "Adjust sensor sliders (temp rise, voltage drop, current spike, error bursts).",
            "Click [Simulate Prediction] to execute live model inference.",
            "Inspect instant shift in failure probability and SHAP attribution ranks."
        ],
        badge="DIAGNOSTIC SIMULATOR"
    )

    # =========================================================================
    # SLIDE 10: Observability & Monitoring
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_slide_background(s10)
    add_header(s10, "SRE Observability: Prometheus Metrics & Grafana Dashboards")

    add_card(
        s10, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8),
        "Prometheus Metrics & SLA Tracking",
        [
            "Standardized /metrics endpoint mounted on all 4 microservices.",
            "datamind_prediction_latency_seconds: Multi-bucket histogram tracking p50, p90, p95, p99 against the 5ms SLA.",
            "datamind_prediction_risk_probability: Distribution of scored failure probabilities [0.0 - 1.0].",
            "datamind_predictions_total: Counter partitioned by risk severity (HIGH vs NOMINAL).",
            "datamind_stream_buffer_depth: Tracks queue congestion and backpressure."
        ],
        badge="CONTINUOUS TELEMETRY"
    )

    add_card(
        s10, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8),
        "Automated Production Alert Rules",
        [
            "PredictionLatencySlaBreached: Fires if P99 latency exceeds 5ms for 30 seconds.",
            "HighRiskFailureCascadeSpike: Fires if >30% of fleet enters high-risk state within 5 minutes (drift/cascade alarm).",
            "CoreApiHighErrorRate: Fires if 5xx HTTP response rate exceeds 1%.",
            "IngestionQueueCongestionBackpressure: Fires if buffer queue exceeds 5,000 unconsumed items.",
            "MicroserviceInstanceDown: Fires if any pod target drops scrape heartbeat."
        ],
        badge="AUTOMATED ALERT RULES"
    )

    # =========================================================================
    # SLIDE 11: Cloud-Native Deployment & Kubernetes
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_slide_background(s11)
    add_header(s11, "Cloud-Native Infrastructure: Docker & Kubernetes Architecture")

    add_card(
        s11, Inches(0.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "Docker Containerization",
        [
            "Multi-Stage Dockerfiles (python:3.11-slim).",
            "Non-root security context (uid 1000).",
            "1-Command Local Orchestration:",
            "docker compose up -d",
            "Spawns all 4 services, Postgres, Redis, Prometheus & Grafana."
        ],
        badge="DOCKER COMPOSE"
    )

    add_card(
        s11, Inches(4.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "Kubernetes Workloads",
        [
            "Namespace Isolation: datamind.",
            "StatefulSet: Postgres 16 with 10Gi PVC & pg_isready health checks.",
            "Deployments: 4 stateless microservices with zero-downtime RollingUpdate.",
            "HTTP /health readiness & liveness probes on all pods."
        ],
        badge="KUBERNETES CLUSTER"
    )

    add_card(
        s11, Inches(8.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "Elastic Autoscaling (HPA)",
        [
            "HorizontalPodAutoscaler on Prediction, API, Ingestion & Dashboard.",
            "Auto-scales 2 to 10 replicas under load.",
            "Ingress NGINX Reverse Proxy routing /, /api/v1/predict, /api/v1/fleet.",
            "1-Command GitOps Bundle: kubectl apply -k infrastructure/k8s/"
        ],
        badge="ELASTIC AUTOSCALING"
    )

    # =========================================================================
    # SLIDE 12: CI/CD & Open-Source Governance
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_slide_background(s12)
    add_header(s12, "CI/CD Automation & Protected Main Branch Governance")

    add_card(
        s12, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8),
        "GitHub Actions CI/CD Pipeline",
        [
            "Continuous Integration (ci.yml): Triggers on every push & pull request to main.",
            "Flake8 Linting & PEP8 Enforcement: Catches syntax errors and dead code.",
            "Kubernetes Manifest Syntax Validation: Validates all 11 YAML manifests.",
            "Full Automated Test Suite: Executes all 98 tests on Python 3.11 (0 failures allowed).",
            "Continuous Delivery (cd.yml): Multi-stage builds and pushes images to GitHub Container Registry (ghcr.io) tagged with short Git SHA."
        ],
        badge="AUTOMATED PIPELINES"
    )

    add_card(
        s12, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8),
        "Global Open-Source Governance",
        [
            "Protected main Branch: Direct pushes are blocked. Nobody can overwrite production history.",
            "Fork & Pull Request Workflow: External contributors fork to user/Data-mind and submit PRs.",
            "Automated CI Gates: GitHub disables the merge button until all 98 tests pass 100% green.",
            "Maintainer Review: Maintainer reviews code diff and approves merges.",
            "Standard Open-Source Templates: CONTRIBUTING.md, PULL_REQUEST_TEMPLATE.md, MIT License."
        ],
        badge="SECURE COLLABORATION"
    )

    # =========================================================================
    # SLIDE 13: Project Achievements Ledger
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    add_slide_background(s13)
    add_header(s13, "Master Project Ledger: 14/14 Milestones Completed (100%)")

    add_card(
        s13, Inches(0.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "Phases 1 & 2: ML & MLOps",
        [
            "M1: Data Gen & Validation (13 tests)",
            "M2: Exploratory Data Analysis (4 tests)",
            "M3: Feature Engineering (7 tests)",
            "M4: Baseline Models (8 tests)",
            "M5: Model Progression (1 test)",
            "M6: Model Explainability (9 tests)",
            "M7: Model Registry / MLflow (5 tests)",
            "M8: Real-Time Prediction API (8 tests)"
        ],
        badge="ML FOUNDATIONS & SERVING"
    )

    add_card(
        s13, Inches(4.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "Phases 3 & 4: Systems & Cloud",
        [
            "M9: Database Persistence (5 tests)",
            "M10: Streaming Ingestion Queue (5 tests)",
            "M11: Fleet Health Dashboard UI (9 tests)",
            "M12: Docker & Compose (9 tests)",
            "M13: Observability & Telemetry (7 tests)",
            "M14: Kubernetes & CI/CD (8 tests)",
            "Total Test Count: 98 passing tests",
            "Pass Rate: 100% (0 errors, 0 failures)"
        ],
        badge="DATA PLATFORM & DEVOPS"
    )

    add_card(
        s13, Inches(8.8), Inches(1.8), Inches(3.7), Inches(4.8),
        "Release v1.0.0.0 Assets",
        [
            "VERSION: 1.0.0.0 tag live on GitHub",
            "LICENSE: Official MIT License",
            "USER_MANUAL.md: Comprehensive guide",
            "CONTRIBUTING.md: Open-source rules",
            "run_platform.py: 1-command local launcher",
            "docker-compose.yml: 1-command container stack",
            "infrastructure/k8s/: 1-command K8s bundle"
        ],
        badge="PRODUCTION ARTIFACTS"
    )

    # =========================================================================
    # SLIDE 14: Conclusion & Q&A
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    add_slide_background(s14)
    add_header(s14, "Conclusion & Project Resources", "SUMMARY & NEXT STEPS")

    add_card(
        s14, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8),
        "Platform Highlights",
        [
            "Engineered to Google SWE Standards: Modular, type-hinted, zero data leakage, and 100% tested.",
            "Sub-Millisecond Inference: Scored in ~400 microseconds, easily satisfying industrial SLAs.",
            "Actionable Explainability: Every failure risk is accompanied by mechanical root-cause attribution.",
            "Turnkey Scalability: Operates locally, via Docker Compose, or as a self-healing Kubernetes cluster."
        ],
        badge="KEY TAKEAWAYS"
    )

    add_card(
        s14, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8),
        "Project Access Links",
        [
            "GitHub Repository: https://github.com/faizalkhan24/Data-mind.git",
            "Release Tag: v1.0.0.0",
            "Live Web Console: http://localhost:8003/",
            "Swagger Prediction API Docs: http://localhost:8000/docs",
            "User & Operator Manual: docs/USER_MANUAL.md",
            "Contribution Guidelines: CONTRIBUTING.md"
        ],
        badge="PROJECT RESOURCES"
    )

    prs.save(str(OUTPUT_FILE))
    print(f"[+] Presentation saved successfully to: {OUTPUT_FILE}")


if __name__ == "__main__":
    create_presentation()
