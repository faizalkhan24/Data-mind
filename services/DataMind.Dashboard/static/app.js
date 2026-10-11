/**
 * DataMind: Fleet Health Operations Console
 * Client Application Logic & Real-Time Diagnostics
 */

(function () {
  'use strict';

  // State Management
  const state = {
    fleet: [],
    alerts: [],
    summary: null,
    searchQuery: '',
    riskFilter: 'ALL',
    refreshInterval: null,
  };

  // Presets definition for diagnostic simulator
  const PRESETS = {
    healthy: {
      temp: 44.5,
      volt: 3.74,
      curr: 1.20,
      battery: 88.0,
      net: 94.0,
      uptime: 120,
    },
    thermal: {
      temp: 88.5,
      volt: 3.65,
      curr: 2.45,
      battery: 75.0,
      net: 80.0,
      uptime: 450,
    },
    battery: {
      temp: 52.0,
      volt: 3.35,
      curr: 1.80,
      battery: 18.0,
      net: 65.0,
      uptime: 890,
    },
    sag: {
      temp: 68.0,
      volt: 2.95,
      curr: 2.90,
      battery: 42.0,
      net: 45.0,
      uptime: 1200,
    },
  };

  // DOM Elements
  const dom = {
    btnRefresh: document.getElementById('btn-refresh'),
    systemStatus: document.getElementById('system-status-text'),
    kpiTotal: document.getElementById('kpi-total-devices'),
    kpiActive: document.getElementById('kpi-active-devices'),
    kpiHighRisk: document.getElementById('kpi-high-risk'),
    kpiOpenAlerts: document.getElementById('kpi-open-alerts'),
    kpiLatency: document.getElementById('kpi-latency'),
    fleetTableBody: document.getElementById('fleet-table-body'),
    deviceSearch: document.getElementById('device-search'),
    filterRisk: document.getElementById('filter-risk'),
    simulatorForm: document.getElementById('simulator-form'),
    simTemp: document.getElementById('sim-temp'),
    simVolt: document.getElementById('sim-volt'),
    simCurr: document.getElementById('sim-curr'),
    simBattery: document.getElementById('sim-battery'),
    simNet: document.getElementById('sim-net'),
    simUptime: document.getElementById('sim-uptime'),
    simResultCard: document.getElementById('sim-result-card'),
    simRiskBadge: document.getElementById('sim-risk-badge'),
    simProbText: document.getElementById('sim-prob-text'),
    simLatencyBadge: document.getElementById('sim-latency-badge'),
    simRiskFactorsList: document.getElementById('sim-risk-factors-list'),
    presetButtons: document.querySelectorAll('.btn-preset'),
    alertsTableBody: document.getElementById('alerts-table-body'),
    alertCounterBadge: document.getElementById('alert-counter-badge'),
    deviceModal: document.getElementById('device-modal'),
    modalDeviceId: document.getElementById('modal-device-id'),
    modalBody: document.getElementById('modal-body'),
    btnCloseModal: document.getElementById('btn-close-modal'),
    btnOpenRegisterModal: document.getElementById('btn-open-register-modal'),
    registerDeviceModal: document.getElementById('register-device-modal'),
    btnCloseRegisterModal: document.getElementById('btn-close-register-modal'),
    registerDeviceForm: document.getElementById('register-device-form'),
    regDeviceId: document.getElementById('reg-device-id'),
    regFirmware: document.getElementById('reg-firmware'),
    regStatus: document.getElementById('reg-status'),
  };

  let telemetryChart = null;

  // ==============================================================================
  // Initialization
  // ==============================================================================
  function init() {
    bindEvents();
    loadDashboardData();
    // Run initial simulation for healthy preset
    executeSimulation();
    // Auto-refresh poll every 5 seconds
    state.refreshInterval = setInterval(loadDashboardData, 5000);
  }

  // ==============================================================================
  // Event Bindings
  // ==============================================================================
  function bindEvents() {
    if (dom.btnRefresh) {
      dom.btnRefresh.addEventListener('click', () => {
        const icon = dom.btnRefresh.querySelector('.btn-icon');
        if (icon) icon.style.transform = 'rotate(360deg)';
        loadDashboardData().finally(() => {
          setTimeout(() => { if (icon) icon.style.transform = 'none'; }, 400);
        });
      });
    }

    if (dom.deviceSearch) {
      dom.deviceSearch.addEventListener('input', (e) => {
        state.searchQuery = e.target.value;
        renderFleetTable();
      });
    }

    if (dom.filterRisk) {
      dom.filterRisk.addEventListener('change', (e) => {
        state.riskFilter = e.target.value;
        renderFleetTable();
      });
    }

    // Diagnostic Presets
    dom.presetButtons.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        dom.presetButtons.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        const presetKey = btn.dataset.preset;
        applyPreset(presetKey);
        executeSimulation();
      });
    });

    // Diagnostic Form Submit
    if (dom.simulatorForm) {
      dom.simulatorForm.addEventListener('submit', (e) => {
        e.preventDefault();
        executeSimulation();
      });
    }

    // Modal Close
    if (dom.btnCloseModal) {
      dom.btnCloseModal.addEventListener('click', closeModal);
    }
    if (dom.deviceModal) {
      dom.deviceModal.addEventListener('click', (e) => {
        if (e.target === dom.deviceModal) closeModal();
      });
    }

    // Register Modal Events
    if (dom.btnOpenRegisterModal) {
      dom.btnOpenRegisterModal.addEventListener('click', () => {
        if (dom.registerDeviceModal) dom.registerDeviceModal.style.display = 'flex';
      });
    }
    if (dom.btnCloseRegisterModal) {
      dom.btnCloseRegisterModal.addEventListener('click', closeRegisterModal);
    }
    if (dom.registerDeviceModal) {
      dom.registerDeviceModal.addEventListener('click', (e) => {
        if (e.target === dom.registerDeviceModal) closeRegisterModal();
      });
    }
    if (dom.registerDeviceForm) {
      dom.registerDeviceForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const deviceId = dom.regDeviceId.value.trim();
        const firmware = dom.regFirmware.value;
        const devStatus = dom.regStatus.value;
        try {
          const resp = await fetch('/api/dashboard/devices', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              device_id: deviceId,
              firmware_version: firmware,
              status: devStatus,
            }),
          });
          if (resp.ok) {
            closeRegisterModal();
            dom.registerDeviceForm.reset();
            await fetchFleet();
            await fetchSummary();
          } else {
            const err = await resp.json();
            alert('Registration failed: ' + (err.detail || 'Error'));
          }
        } catch (err) {
          console.error('Registration failed:', err);
        }
      });
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeModal();
        closeRegisterModal();
      }
    });
  }

  // ==============================================================================
  // Preset Management
  // ==============================================================================
  function applyPreset(key) {
    const p = PRESETS[key];
    if (!p) return;
    dom.simTemp.value = p.temp;
    dom.simVolt.value = p.volt;
    dom.simCurr.value = p.curr;
    dom.simBattery.value = p.battery;
    dom.simNet.value = p.net;
    dom.simUptime.value = p.uptime;
  }

  // ==============================================================================
  // Data Loading & API Calls
  // ==============================================================================
  async function loadDashboardData() {
    try {
      await Promise.all([
        fetchSummary(),
        fetchFleet(),
        fetchAlerts(),
      ]);
    } catch (err) {
      console.warn('Dashboard sync note:', err);
    }
  }

  async function fetchSummary() {
    try {
      const res = await fetch('/api/dashboard/summary');
      if (!res.ok) throw new Error('Failed to fetch summary');
      const data = await res.json();
      state.summary = data;
      renderKPIs(data);
    } catch (e) {
      console.error(e);
    }
  }

  async function fetchFleet() {
    try {
      const res = await fetch('/api/dashboard/fleet?limit=100');
      if (!res.ok) throw new Error('Failed to fetch fleet');
      const data = await res.json();
      state.fleet = data.devices || [];
      renderFleetTable();
    } catch (e) {
      console.error(e);
    }
  }

  async function fetchAlerts() {
    try {
      const res = await fetch('/api/dashboard/alerts');
      if (!res.ok) throw new Error('Failed to fetch alerts');
      const data = await res.json();
      state.alerts = data || [];
      renderAlertsTable();
    } catch (e) {
      console.error(e);
    }
  }

  // ==============================================================================
  // Render KPI Metrics
  // ==============================================================================
  function renderKPIs(data) {
    if (!data) return;
    dom.kpiTotal.textContent = data.total_devices || '--';
    dom.kpiActive.textContent = data.active_devices || '--';
    dom.kpiHighRisk.textContent = data.high_risk_devices || '0';
    dom.kpiOpenAlerts.textContent = data.open_alerts || '0';
    if (data.avg_inference_sla) dom.kpiLatency.textContent = data.avg_inference_sla;
    if (data.system_status && dom.systemStatus) {
      dom.systemStatus.textContent = data.system_status;
    }
  }

  // ==============================================================================
  // Render Fleet Health Table
  // ==============================================================================
  function renderFleetTable() {
    if (!dom.fleetTableBody) return;

    let filtered = state.fleet.slice();

    if (state.searchQuery.trim()) {
      const q = state.searchQuery.trim().toLowerCase();
      filtered = filtered.filter((d) => d.device_id.toLowerCase().includes(q));
    }

    if (state.riskFilter !== 'ALL') {
      filtered = filtered.filter((d) => d.risk_level === state.riskFilter);
    }

    if (filtered.length === 0) {
      dom.fleetTableBody.innerHTML = `
        <tr>
          <td colspan="6" class="table-loading">No devices match active search/filter criteria.</td>
        </tr>
      `;
      return;
    }

    const rows = filtered.map((d) => {
      const isHigh = d.risk_level === 'HIGH';
      const probPct = (d.failure_probability * 100).toFixed(1) + '%';
      const badgeClass = isHigh ? 'badge-danger' : 'badge-nominal';
      const statusBadge = d.status === 'ACTIVE' ? 'badge-nominal' : 'badge-warning';

      return `
        <tr>
          <td><strong style="font-family: var(--font-mono);">${d.device_id}</strong></td>
          <td><span class="badge badge-info">v${d.firmware_version}</span></td>
          <td><span class="badge ${statusBadge}">${d.status}</span></td>
          <td style="font-family: var(--font-mono);">${probPct}</td>
          <td><span class="badge ${badgeClass}">${d.risk_level}</span></td>
          <td>
            <button class="btn btn-sm btn-inspect" data-device="${d.device_id}">Inspect</button>
          </td>
        </tr>
      `;
    }).join('');

    dom.fleetTableBody.innerHTML = rows;

    // Attach inspect click handlers
    dom.fleetTableBody.querySelectorAll('.btn-inspect').forEach((btn) => {
      btn.addEventListener('click', () => {
        const devId = btn.dataset.device;
        openDeviceModal(devId);
      });
    });
  }

  // ==============================================================================
  // Real-Time Diagnostic Simulation & SHAP Attribution
  // ==============================================================================
  async function executeSimulation() {
    const payload = {
      device_id: 'DEV-SIMULATOR',
      temperature: parseFloat(dom.simTemp.value) || 45.0,
      voltage: parseFloat(dom.simVolt.value) || 3.70,
      current: parseFloat(dom.simCurr.value) || 1.20,
      battery_level: parseFloat(dom.simBattery.value) || 85.0,
      network_quality: parseFloat(dom.simNet.value) || 90.0,
      uptime_hours: parseFloat(dom.simUptime.value) || 120.0,
      firmware_version: '1.2.0',
    };

    try {
      const res = await fetch('/api/dashboard/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error('Simulation failed');
      const data = await res.json();
      renderSimulationResult(data);
    } catch (e) {
      console.error('Simulation error:', e);
    }
  }

  function renderSimulationResult(data) {
    if (!data) return;

    const isHigh = data.risk_level === 'HIGH';
    dom.simRiskBadge.className = `sim-risk-badge ${isHigh ? 'badge-danger' : 'badge-nominal'}`;
    dom.simRiskBadge.textContent = isHigh ? 'HIGH RISK' : 'LOW RISK';

    dom.simProbText.textContent = `P(Fail) = ${data.failure_probability.toFixed(3)}`;
    dom.simLatencyBadge.textContent = `${data.latency_ms.toFixed(2)} ms`;

    // Render SHAP Factors
    if (!data.top_risk_factors || data.top_risk_factors.length === 0) {
      dom.simRiskFactorsList.innerHTML = '<div class="factor-empty">No dominant risk factors identified.</div>';
      return;
    }

    const factorsHtml = data.top_risk_factors.map((f) => {
      const isPositive = f.impact.startsWith('+');
      const impactClass = isPositive ? 'impact-pos' : 'impact-neg';
      const barClass = isPositive ? 'impact-bar-pos' : 'impact-bar-neg';
      const absVal = Math.min(100, Math.round(Math.abs(f.impact_value) * 180));

      return `
        <div class="factor-item">
          <div class="factor-info">
            <div>
              <span class="factor-name">${f.factor}</span>
              <span class="factor-feature">(${f.feature})</span>
            </div>
            <span class="factor-impact ${impactClass}">${f.impact}</span>
          </div>
          <div class="impact-bar-wrap">
            <div class="impact-bar ${barClass}" style="width: ${absVal}%;"></div>
          </div>
        </div>
      `;
    }).join('');

    dom.simRiskFactorsList.innerHTML = factorsHtml;
  }

  // ==============================================================================
  // Operational Incident Alerts Management
  // ==============================================================================
  function renderAlertsTable() {
    if (!dom.alertsTableBody) return;

    if (dom.alertCounterBadge) {
      const openCount = state.alerts.filter((a) => a.status === 'OPEN').length;
      dom.alertCounterBadge.textContent = `${openCount} Critical Alerts`;
      dom.alertCounterBadge.className = openCount > 0 ? 'badge badge-danger' : 'badge badge-nominal';
    }

    if (state.alerts.length === 0) {
      dom.alertsTableBody.innerHTML = `
        <tr>
          <td colspan="6" class="table-loading">No active operational alerts. Fleet nominal.</td>
        </tr>
      `;
      return;
    }

    const rows = state.alerts.map((a) => {
      const sevBadge = a.alert_level === 'CRITICAL' ? 'badge-danger' : 'badge-warning';
      const isResolved = a.status === 'RESOLVED';
      const isAck = a.status === 'ACKNOWLEDGED';

      let actionHtml = '';
      if (!isResolved) {
        if (!isAck) {
          actionHtml += `<button class="btn btn-sm btn-ack" data-id="${a.id}">Acknowledge</button> `;
        }
        actionHtml += `<button class="btn btn-sm btn-resolve" data-id="${a.id}">Resolve</button>`;
      } else {
        actionHtml = '<span class="badge badge-nominal">RESOLVED</span>';
      }

      return `
        <tr>
          <td><strong style="font-family: var(--font-mono);">#${a.id}</strong></td>
          <td><span style="font-family: var(--font-mono); font-weight:600;">${a.device_id}</span></td>
          <td><span class="badge ${sevBadge}">${a.alert_level}</span></td>
          <td>${a.summary}</td>
          <td style="font-size: 11px; color: var(--text-dim);">${a.created_at || 'Just now'}</td>
          <td>${actionHtml}</td>
        </tr>
      `;
    }).join('');

    dom.alertsTableBody.innerHTML = rows;

    // Attach actions
    dom.alertsTableBody.querySelectorAll('.btn-ack').forEach((btn) => {
      btn.addEventListener('click', () => updateAlertStatus(parseInt(btn.dataset.id, 10), 'ACKNOWLEDGED'));
    });
    dom.alertsTableBody.querySelectorAll('.btn-resolve').forEach((btn) => {
      btn.addEventListener('click', () => updateAlertStatus(parseInt(btn.dataset.id, 10), 'RESOLVED'));
    });
  }

  async function updateAlertStatus(alertId, newStatus) {
    try {
      const res = await fetch(`/api/dashboard/alerts/${alertId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        // Optimistic update
        const alert = state.alerts.find((a) => a.id === alertId);
        if (alert) alert.status = newStatus;
        renderAlertsTable();
        fetchSummary();
      }
    } catch (e) {
      console.error('Failed to update alert:', e);
    }
  }

  // ==============================================================================
  // Device Inspection Modal
  // ==============================================================================
  async function openDeviceModal(deviceId) {
    if (!dom.deviceModal) return;
    dom.modalDeviceId.textContent = `Device Inspection — ${deviceId}`;
    dom.modalBody.innerHTML = '<p class="table-loading">Querying device telemetry and health ledger...</p>';
    dom.deviceModal.style.display = 'flex';

    try {
      const res = await fetch(`/api/dashboard/devices/${deviceId}`);
      if (!res.ok) throw new Error('Device not found');
      const data = await res.json();
      renderDeviceModalContent(data);
    } catch (e) {
      dom.modalBody.innerHTML = `<p class="table-loading" style="color: var(--color-danger);">Failed to load device details: ${e.message}</p>`;
    }
  }

  function renderDeviceModalContent(data) {
    const dev = data.device;
    const hist = data.history || [];
    const isHigh = dev.risk_level === 'HIGH';

    // Remaining Useful Life (RUL) Prognostics Computation
    const prob = dev.failure_probability || 0.0;
    let rulHours = 0;
    let rulBadgeClass = 'badge-nominal';
    let rulBarColor = 'var(--color-success)';
    let rulText = '';
    let rulStatus = 'NOMINAL';
    let barWidth = '100%';

    if (prob >= 0.70) {
      rulHours = Math.max(2, Math.round((1 - prob) * 36));
      rulBadgeClass = 'badge-danger';
      rulBarColor = 'var(--color-danger)';
      rulText = `~${rulHours} Hours Remaining (Immediate Action Required)`;
      rulStatus = 'CRITICAL IMPENDING FAILURE';
      barWidth = `${Math.max(10, Math.round((1 - prob) * 100))}%`;
    } else if (prob >= 0.30) {
      rulHours = Math.round((1 - prob) * 168);
      rulBadgeClass = 'badge-warning';
      rulBarColor = 'var(--color-warning)';
      rulText = `~${rulHours} Hours Remaining (Inspection Recommended)`;
      rulStatus = 'ELEVATED DEGRADATION RISK';
      barWidth = `${Math.round((1 - prob) * 100)}%`;
    } else {
      rulHours = 720;
      rulBadgeClass = 'badge-nominal';
      rulBarColor = 'var(--color-success)';
      rulText = '> 720 Hours (Optimal Lifecycle)';
      rulStatus = 'NOMINAL LIFECYCLE';
      barWidth = '95%';
    }

    const historyRows = hist.map((h) => `
      <tr>
        <td style="font-family: var(--font-mono); font-size: 11px;">${h.timestamp.slice(11, 19)}</td>
        <td>${h.temperature}°C</td>
        <td>${h.voltage}V</td>
        <td>${h.current}A</td>
        <td>${h.battery_level}%</td>
        <td>${h.network_quality}%</td>
        <td>${h.error_count}</td>
      </tr>
    `).join('');

    dom.modalBody.innerHTML = `
      <!-- Remaining Useful Life (RUL) Card -->
      <div class="rul-prognostic-card">
        <div class="rul-header">
          <div class="rul-title">Prognostic Remaining Useful Life (RUL)</div>
          <span class="badge ${rulBadgeClass}">${rulStatus}</span>
        </div>
        <div class="rul-countdown" style="color: ${rulBarColor};">${rulText}</div>
        <div class="rul-bar-wrap">
          <div class="rul-bar" style="width: ${barWidth}; background: ${rulBarColor};"></div>
        </div>
      </div>

      <!-- Multi-Metric Telemetry Trend Chart -->
      <div class="chart-container">
        <canvas id="device-telemetry-chart"></canvas>
      </div>

      <!-- Hardware Spec Grid -->
      <div class="modal-spec-grid">
        <div class="modal-spec-item">
          <span class="modal-spec-label">Failure Probability</span>
          <span class="modal-spec-val" style="color: ${isHigh ? 'var(--color-danger)' : 'var(--color-success)'};">
            ${(dev.failure_probability * 100).toFixed(1)}% (${dev.risk_level})
          </span>
        </div>
        <div class="modal-spec-item">
          <span class="modal-spec-label">Hardware Profile</span>
          <span class="modal-spec-val">${dev.hardware_model}</span>
        </div>
        <div class="modal-spec-item">
          <span class="modal-spec-label">Firmware</span>
          <span class="modal-spec-val">v${dev.firmware_version}</span>
        </div>
        <div class="modal-spec-item">
          <span class="modal-spec-label">Chassis Temp</span>
          <span class="modal-spec-val">${dev.temperature}°C</span>
        </div>
        <div class="modal-spec-item">
          <span class="modal-spec-label">Supply Rail</span>
          <span class="modal-spec-val">${dev.voltage}V</span>
        </div>
        <div class="modal-spec-item">
          <span class="modal-spec-label">Cumulative Uptime</span>
          <span class="modal-spec-val">${dev.uptime_hours}h</span>
        </div>
      </div>

      <div>
        <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; color: var(--text-dim);">
          Trailing 10-Hour Telemetry Audit
        </div>
        <div class="table-responsive" style="max-height: 180px;">
          <table class="data-table">
            <thead>
              <tr>
                <th>Time (UTC)</th>
                <th>Temp</th>
                <th>Voltage</th>
                <th>Current</th>
                <th>Battery</th>
                <th>Net</th>
                <th>Errors</th>
              </tr>
            </thead>
            <tbody>
              ${historyRows}
            </tbody>
          </table>
        </div>
      </div>
    `;

    // Render Chart.js Multi-Metric Sparklines
    renderTelemetryChart(hist);
  }

  function renderTelemetryChart(history) {
    if (typeof Chart === 'undefined') return;
    const canvas = document.getElementById('device-telemetry-chart');
    if (!canvas) return;

    if (telemetryChart) {
      telemetryChart.destroy();
      telemetryChart = null;
    }

    const reversed = [...history].reverse();
    const labels = reversed.map((h) => h.timestamp.slice(11, 16));
    const temps = reversed.map((h) => h.temperature);
    const volts = reversed.map((h) => h.voltage);
    const batts = reversed.map((h) => h.battery_level);

    telemetryChart = new Chart(canvas, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Temp (°C)',
            data: temps,
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.08)',
            borderWidth: 2,
            tension: 0.35,
            pointRadius: 3,
            yAxisID: 'yTemp',
          },
          {
            label: 'Voltage (V)',
            data: volts,
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.08)',
            borderWidth: 2,
            tension: 0.35,
            pointRadius: 3,
            yAxisID: 'yVolt',
          },
          {
            label: 'Battery (%)',
            data: batts,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.08)',
            borderWidth: 2,
            tension: 0.35,
            pointRadius: 3,
            yAxisID: 'yBatt',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            position: 'top',
            labels: { color: '#94a3b8', boxWidth: 12, font: { size: 10 } },
          },
        },
        scales: {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.04)' },
            ticks: { color: '#64748b', font: { size: 9 } },
          },
          yTemp: {
            type: 'linear',
            position: 'left',
            grid: { color: 'rgba(255, 255, 255, 0.04)' },
            ticks: { color: '#ef4444', font: { size: 9 } },
            title: { display: false },
          },
          yVolt: {
            type: 'linear',
            position: 'right',
            grid: { drawOnChartArea: false },
            ticks: { color: '#3b82f6', font: { size: 9 } },
            title: { display: false },
          },
          yBatt: {
            type: 'linear',
            position: 'right',
            grid: { drawOnChartArea: false },
            ticks: { color: '#10b981', font: { size: 9 } },
            title: { display: false },
          },
        },
      },
    });
  }

  function closeModal() {
    if (telemetryChart) {
      telemetryChart.destroy();
      telemetryChart = null;
    }
    if (dom.deviceModal) dom.deviceModal.style.display = 'none';
  }

  function closeRegisterModal() {
    if (dom.registerDeviceModal) dom.registerDeviceModal.style.display = 'none';
  }

  // Start on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
