/**
 * DataMind: Enterprise Fleet Health Operations Console & Predictive Studio
 * Client Application Logic, Multi-View Orchestrator & Real-Time Diagnostics (v1.0.0.1)
 */

(function () {
  'use strict';

  // Global State Store
  const state = {
    fleet: [],
    alerts: [],
    summary: null,
    topology: null,
    simulator: null,
    searchQuery: '',
    riskFilter: 'ALL',
    statusFilter: 'ALL',
    activeTab: 'overview',
    soundEnabled: false,
    refreshInterval: null,
    simPollInterval: null,
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

  // DOM Elements Registry
  const dom = {
    // Header & KPIs
    btnRefresh: document.getElementById('btn-refresh'),
    systemStatus: document.getElementById('system-status-text'),
    btnToggleSound: document.getElementById('btn-toggle-sound'),
    soundIcon: document.getElementById('sound-icon'),
    btnExportFleet: document.getElementById('btn-export-fleet'),
    btnExportAlerts: document.getElementById('btn-export-alerts'),
    kpiTotal: document.getElementById('kpi-total-devices'),
    kpiActive: document.getElementById('kpi-active-devices'),
    kpiHighRisk: document.getElementById('kpi-high-risk'),
    kpiOpenAlerts: document.getElementById('kpi-open-alerts'),
    kpiLatency: document.getElementById('kpi-latency'),

    // Tab Navigation
    navTabs: document.getElementById('main-nav-tabs'),
    tabButtons: document.querySelectorAll('.nav-tab-btn'),
    tabPanes: document.querySelectorAll('.tab-pane'),

    // Mission Control Overview
    badgeHealthScore: document.getElementById('badge-health-score'),
    vitalTemp: document.getElementById('vital-temp'),
    vitalVolt: document.getElementById('vital-volt'),
    vitalBatt: document.getElementById('vital-batt'),
    overviewAlertsPreview: document.getElementById('overview-alerts-preview'),

    // Fleet Explorer
    fleetTableBody: document.getElementById('fleet-table-body'),
    deviceSearch: document.getElementById('device-search'),
    filterRisk: document.getElementById('filter-risk'),
    filterStatus: document.getElementById('filter-status'),
    btnOpenRegisterModal: document.getElementById('btn-open-register-modal'),

    // What-If Simulator & SHAP
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
    featureImportanceBody: document.getElementById('feature-importance-table-body'),

    // Stream Simulator Daemon Controls
    simDaemonBadge: document.getElementById('sim-daemon-badge'),
    simStatRunning: document.getElementById('sim-stat-running'),
    simStatDevices: document.getElementById('sim-stat-devices'),
    simStatTicks: document.getElementById('sim-stat-ticks'),
    simStatDispatched: document.getElementById('sim-stat-dispatched'),
    simStatAnomalies: document.getElementById('sim-stat-anomalies'),
    btnStartSimulator: document.getElementById('btn-start-simulator'),
    btnStopSimulator: document.getElementById('btn-stop-simulator'),
    btnFaultThermal: document.getElementById('btn-fault-thermal'),
    btnFaultSag: document.getElementById('btn-fault-sag'),
    btnFaultWatchdog: document.getElementById('btn-fault-watchdog'),

    // Incident Command Desk
    alertsTableBody: document.getElementById('alerts-table-body'),
    alertCounterBadge: document.getElementById('alert-counter-badge'),

    // Topology Mesh
    topologyGrid: document.getElementById('topology-mesh-grid'),
    topologyGlobalBadge: document.getElementById('topology-global-badge'),

    // Modals
    deviceModal: document.getElementById('device-modal'),
    modalDeviceId: document.getElementById('modal-device-id'),
    modalBody: document.getElementById('modal-body'),
    btnCloseModal: document.getElementById('btn-close-modal'),

    registerDeviceModal: document.getElementById('register-device-modal'),
    btnCloseRegisterModal: document.getElementById('btn-close-register-modal'),
    registerDeviceForm: document.getElementById('register-device-form'),
    regDeviceId: document.getElementById('reg-device-id'),
    regFirmware: document.getElementById('reg-firmware'),
    regStatus: document.getElementById('reg-status'),

    editDeviceModal: document.getElementById('edit-device-modal'),
    btnCloseEditModal: document.getElementById('btn-close-edit-modal'),
    editDeviceForm: document.getElementById('edit-device-form'),
    editDeviceId: document.getElementById('edit-device-id'),
    editFirmware: document.getElementById('edit-firmware'),
    editStatus: document.getElementById('edit-status'),

    toastContainer: document.getElementById('toast-container'),
  };

  // Chart instances
  let telemetryChart = null;
  let fleetDonutChart = null;

  // ==============================================================================
  // Initialization & Boot Lifecycle
  // ==============================================================================
  function init() {
    bindEvents();
    loadDashboardData();
    executeSimulation();
    loadFeatureImportance();
    loadTopology();
    loadSimulatorStatus();

    // Auto-refresh poll every 5 seconds
    state.refreshInterval = setInterval(loadDashboardData, 5000);
    // Poll simulator stats every 3 seconds
    state.simPollInterval = setInterval(loadSimulatorStatus, 3000);
  }

  // ==============================================================================
  // Tab Navigation Engine
  // ==============================================================================
  function switchTab(tabId) {
    state.activeTab = tabId;
    dom.tabButtons.forEach((btn) => {
      const isActive = btn.dataset.tab === tabId;
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
      if (isActive && typeof btn.scrollIntoView === 'function') {
        btn.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      }
    });
    dom.tabPanes.forEach((pane) => {
      pane.classList.toggle('active', pane.id === `pane-${tabId}`);
    });

    if (tabId === 'overview') {
      renderFleetDonutChart();
    } else if (tabId === 'topology') {
      loadTopology();
    } else if (tabId === 'simulator') {
      loadSimulatorStatus();
    }
  }
  window.switchTab = switchTab;

  // ==============================================================================
  // Toast Notification Engine
  // ==============================================================================
  function showToast(message, type = 'info') {
    if (!dom.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ? '✓' : type === 'danger' ? '⚠' : type === 'warning' ? '⚡' : 'ℹ';
    toast.innerHTML = `<strong>${icon}</strong> <span>${message}</span>`;
    dom.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = window.innerWidth <= 640 ? 'translateY(16px)' : 'translateX(40px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  // ==============================================================================
  // Web Audio Alarm Synthesizer
  // ==============================================================================
  function playAlarmChime() {
    if (!state.soundEnabled) return;
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(880, audioCtx.currentTime); // A5
      osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.25);
      gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.25);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.25);
    } catch {
      // AudioContext policy suppression fallback
    }
  }

  // ==============================================================================
  // Event Bindings
  // ==============================================================================
  function bindEvents() {
    // Tab switching
    dom.tabButtons.forEach((btn) => {
      btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Refresh button
    if (dom.btnRefresh) {
      dom.btnRefresh.addEventListener('click', () => {
        const icon = dom.btnRefresh.querySelector('.btn-icon');
        if (icon) icon.style.transform = 'rotate(360deg)';
        loadDashboardData().finally(() => {
          setTimeout(() => { if (icon) icon.style.transform = 'none'; }, 400);
          showToast('Dashboard metrics refreshed.', 'info');
        });
      });
    }

    // Sound toggle
    if (dom.btnToggleSound) {
      dom.btnToggleSound.addEventListener('click', () => {
        state.soundEnabled = !state.soundEnabled;
        if (dom.soundIcon) dom.soundIcon.textContent = state.soundEnabled ? '🔔' : '🔕';
        showToast(`Audible alerts ${state.soundEnabled ? 'ENABLED' : 'MUTED'}.`, state.soundEnabled ? 'success' : 'info');
        if (state.soundEnabled) playAlarmChime();
      });
    }

    // Export Fleet CSV
    if (dom.btnExportFleet) {
      dom.btnExportFleet.addEventListener('click', () => {
        window.location.href = '/api/dashboard/export/fleet';
        showToast('Exporting fleet inventory report...', 'success');
      });
    }

    // Export Alerts CSV
    if (dom.btnExportAlerts) {
      dom.btnExportAlerts.addEventListener('click', () => {
        window.location.href = '/api/dashboard/export/alerts';
        showToast('Exporting incident ledger report...', 'success');
      });
    }

    // Fleet search and filter
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
    if (dom.filterStatus) {
      dom.filterStatus.addEventListener('change', (e) => {
        state.statusFilter = e.target.value;
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

    // Simulator Daemon Controls
    if (dom.btnStartSimulator) {
      dom.btnStartSimulator.addEventListener('click', async () => {
        try {
          const res = await fetch('/api/dashboard/simulator/start', { method: 'POST' });
          if (res.ok) {
            showToast('Autonomous fleet telemetry simulator STARTED.', 'success');
            loadSimulatorStatus();
          }
        } catch (err) {
          showToast('Failed to start simulator: ' + err.message, 'danger');
        }
      });
    }
    if (dom.btnStopSimulator) {
      dom.btnStopSimulator.addEventListener('click', async () => {
        try {
          const res = await fetch('/api/dashboard/simulator/stop', { method: 'POST' });
          if (res.ok) {
            showToast('Continuous simulator STOPPED.', 'info');
            loadSimulatorStatus();
          }
        } catch (err) {
          showToast('Failed to stop simulator: ' + err.message, 'danger');
        }
      });
    }

    // Fault Injection Quick Buttons
    if (dom.btnFaultThermal) {
      dom.btnFaultThermal.addEventListener('click', () => {
        applyPreset('thermal');
        switchTab('whatif');
        executeSimulation();
        showToast('Thermal runaway fault scenario injected.', 'warning');
      });
    }
    if (dom.btnFaultSag) {
      dom.btnFaultSag.addEventListener('click', () => {
        applyPreset('sag');
        switchTab('whatif');
        executeSimulation();
        showToast('Power rail sag fault scenario injected.', 'warning');
      });
    }
    if (dom.btnFaultWatchdog) {
      dom.btnFaultWatchdog.addEventListener('click', () => {
        applyPreset('battery');
        switchTab('whatif');
        executeSimulation();
        showToast('Battery depletion / watchdog fault scenario injected.', 'danger');
      });
    }

    // Modals Close Bindings
    if (dom.btnCloseModal) dom.btnCloseModal.addEventListener('click', closeModal);
    if (dom.deviceModal) {
      dom.deviceModal.addEventListener('click', (e) => {
        if (e.target === dom.deviceModal) closeModal();
      });
    }

    // Register Modal
    if (dom.btnOpenRegisterModal) {
      dom.btnOpenRegisterModal.addEventListener('click', () => {
        if (dom.registerDeviceModal) dom.registerDeviceModal.style.display = 'flex';
      });
    }
    if (dom.btnCloseRegisterModal) dom.btnCloseRegisterModal.addEventListener('click', closeRegisterModal);
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
            body: JSON.stringify({ device_id: deviceId, firmware_version: firmware, status: devStatus }),
          });
          if (resp.ok) {
            closeRegisterModal();
            dom.registerDeviceForm.reset();
            showToast(`Device ${deviceId} registered successfully.`, 'success');
            await fetchFleet();
            await fetchSummary();
          } else {
            const err = await resp.json();
            showToast('Registration failed: ' + (err.detail || 'Error'), 'danger');
          }
        } catch (err) {
          showToast('Registration failed: ' + err.message, 'danger');
        }
      });
    }

    // Edit Modal
    if (dom.btnCloseEditModal) dom.btnCloseEditModal.addEventListener('click', closeEditModal);
    if (dom.editDeviceModal) {
      dom.editDeviceModal.addEventListener('click', (e) => {
        if (e.target === dom.editDeviceModal) closeEditModal();
      });
    }
    if (dom.editDeviceForm) {
      dom.editDeviceForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const deviceId = dom.editDeviceId.value;
        const firmware = dom.editFirmware.value;
        const devStatus = dom.editStatus.value;
        try {
          const resp = await fetch(`/api/dashboard/devices/${deviceId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ firmware_version: firmware, status: devStatus }),
          });
          if (resp.ok) {
            closeEditModal();
            showToast(`Device ${deviceId} updated successfully.`, 'success');
            await fetchFleet();
            await fetchSummary();
          } else {
            const err = await resp.json();
            showToast('Update failed: ' + (err.detail || 'Error'), 'danger');
          }
        } catch (err) {
          showToast('Update error: ' + err.message, 'danger');
        }
      });
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeModal();
        closeRegisterModal();
        closeEditModal();
      }
    });
  }

  // ==============================================================================
  // Data Loading & API Calls
  // ==============================================================================
  async function loadDashboardData() {
    await Promise.allSettled([fetchSummary(), fetchFleet(), fetchAlerts()]);
  }

  async function fetchSummary() {
    try {
      const res = await fetch('/api/dashboard/summary');
      if (!res.ok) throw new Error('Summary fetch failed');
      const data = await res.json();
      state.summary = data;
      renderKPIs(data);
      renderFleetDonutChart();
    } catch (e) {
      console.warn('Summary fetch fallback:', e);
    }
  }

  async function fetchFleet() {
    try {
      const res = await fetch('/api/dashboard/fleet?limit=100');
      if (!res.ok) throw new Error('Fleet fetch failed');
      const data = await res.json();
      state.fleet = data.devices || [];
      renderFleetTable();
    } catch (e) {
      console.warn('Fleet fetch fallback:', e);
    }
  }

  async function fetchAlerts() {
    try {
      const res = await fetch('/api/dashboard/alerts');
      if (!res.ok) throw new Error('Alerts fetch failed');
      const data = await res.json();
      const prevOpenCount = state.alerts.filter((a) => a.status === 'OPEN').length;
      state.alerts = data || [];
      const newOpenCount = state.alerts.filter((a) => a.status === 'OPEN').length;

      // Trigger audio alarm if new critical alert emerged
      if (newOpenCount > prevOpenCount && state.soundEnabled) {
        playAlarmChime();
        showToast('CRITICAL FAILURE ALERT DETECTED!', 'danger');
      }

      renderAlertsTable();
      renderOverviewAlertsPreview();
    } catch (e) {
      console.warn('Alerts fetch fallback:', e);
    }
  }

  async function loadFeatureImportance() {
    if (!dom.featureImportanceBody) return;
    try {
      const res = await fetch('/api/dashboard/model/feature-importance');
      if (!res.ok) return;
      const data = await res.json();
      renderFeatureImportance(data.features || []);
    } catch (e) {
      console.warn('Feature importance fetch fallback:', e);
    }
  }

  async function loadTopology() {
    if (!dom.topologyGrid) return;
    try {
      const res = await fetch('/api/dashboard/topology');
      if (!res.ok) return;
      const data = await res.json();
      state.topology = data;
      renderTopology(data);
    } catch (e) {
      console.warn('Topology fetch fallback:', e);
    }
  }

  async function loadSimulatorStatus() {
    if (!dom.simStatRunning) return;
    try {
      const res = await fetch('/api/dashboard/simulator/status');
      if (!res.ok) return;
      const data = await res.json();
      state.simulator = data;
      renderSimulatorStatus(data);
    } catch (e) {
      console.warn('Simulator status fetch fallback:', e);
    }
  }

  // ==============================================================================
  // UI Renderers
  // ==============================================================================
  function renderKPIs(summary) {
    if (dom.kpiTotal) dom.kpiTotal.textContent = summary.total_devices ?? '--';
    if (dom.kpiActive) dom.kpiActive.textContent = summary.active_devices ?? '--';
    if (dom.kpiHighRisk) dom.kpiHighRisk.textContent = summary.high_risk_devices ?? '--';
    if (dom.kpiOpenAlerts) dom.kpiOpenAlerts.textContent = summary.open_alerts ?? '--';
    if (dom.kpiLatency) dom.kpiLatency.textContent = summary.avg_inference_sla ?? '< 0.50 ms';
    if (dom.systemStatus) dom.systemStatus.textContent = summary.system_status ?? 'SYSTEM HEALTHY';

    // Vitals
    if (dom.vitalTemp && summary.avg_temperature) dom.vitalTemp.textContent = `${summary.avg_temperature}°C`;
    if (dom.vitalVolt && summary.avg_voltage) dom.vitalVolt.textContent = `${summary.avg_voltage} V`;
    if (dom.vitalBatt && summary.avg_battery) dom.vitalBatt.textContent = `${summary.avg_battery}%`;
    if (dom.badgeHealthScore && summary.fleet_health_score !== undefined) {
      dom.badgeHealthScore.textContent = `Health Index: ${summary.fleet_health_score}%`;
    }
  }

  function renderFleetDonutChart() {
    if (typeof Chart === 'undefined') return;
    const canvas = document.getElementById('chart-fleet-distribution');
    if (!canvas) return;

    const s = state.summary;
    if (!s) return;

    const nominal = s.nominal_devices || (s.total_devices - s.high_risk_devices);
    const elevated = s.elevated_devices || 0;
    const high = s.high_risk_devices || 0;

    if (fleetDonutChart) {
      fleetDonutChart.data.datasets[0].data = [nominal, elevated, high];
      fleetDonutChart.update();
      return;
    }

    fleetDonutChart = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: ['Nominal', 'Elevated (Watch)', 'Critical Risk'],
        datasets: [
          {
            data: [nominal, elevated, high],
            backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
            borderColor: '#151c2e',
            borderWidth: 3,
            hoverOffset: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ${ctx.label}: ${ctx.raw} devices (${Math.round((ctx.raw / (nominal + elevated + high || 1)) * 100)}%)`,
            },
          },
        },
        cutout: '72%',
      },
    });
  }

  function renderFleetTable() {
    if (!dom.fleetTableBody) return;

    let filtered = [...state.fleet];
    if (state.searchQuery) {
      const q = state.searchQuery.toLowerCase();
      filtered = filtered.filter((d) => d.device_id.toLowerCase().includes(q));
    }
    if (state.riskFilter !== 'ALL') {
      filtered = filtered.filter((d) => d.risk_level === state.riskFilter);
    }
    if (state.statusFilter !== 'ALL') {
      filtered = filtered.filter((d) => d.status === state.statusFilter);
    }

    if (filtered.length === 0) {
      dom.fleetTableBody.innerHTML = '<tr><td colspan="10" class="table-loading">No matching fleet devices found.</td></tr>';
      return;
    }

    const rows = filtered.map((d) => {
      const probPct = `${(d.failure_probability * 100).toFixed(1)}%`;
      const isHigh = d.risk_level === 'HIGH';
      const badgeClass = isHigh ? 'badge-danger' : 'badge-nominal';
      const statusBadge = d.status === 'ACTIVE' ? 'badge-nominal' : (d.status === 'MAINTENANCE' ? 'badge-warning' : 'badge-info');

      return `
        <tr>
          <td><strong style="font-family: var(--font-mono);">${d.device_id}</strong></td>
          <td style="font-size: 11px; color: var(--text-dim);">${d.hardware_model || 'SensorEdge-v2'}</td>
          <td><span class="badge badge-info">v${d.firmware_version}</span></td>
          <td><span class="badge ${statusBadge}">${d.status}</span></td>
          <td style="font-family: var(--font-mono); font-weight: 700; color: ${isHigh ? 'var(--color-danger)' : 'var(--text-main)'};">${probPct}</td>
          <td><span class="badge ${badgeClass}">${d.risk_level}</span></td>
          <td>${d.temperature ? d.temperature + '°C' : '--'}</td>
          <td>${d.voltage ? d.voltage + 'V' : '--'}</td>
          <td>${d.battery_level ? d.battery_level + '%' : '--'}</td>
          <td>
            <div style="display: flex; gap: 4px;">
              <button class="btn btn-sm btn-inspect" data-device="${d.device_id}">Inspect</button>
              <button class="btn btn-sm btn-edit" data-device="${d.device_id}" data-firmware="${d.firmware_version}" data-status="${d.status}">Edit</button>
              <button class="btn btn-sm btn-delete" data-device="${d.device_id}" title="Decommission" style="color: var(--color-danger);">✕</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    dom.fleetTableBody.innerHTML = rows;

    // Attach inspect, edit, delete handlers
    dom.fleetTableBody.querySelectorAll('.btn-inspect').forEach((btn) => {
      btn.addEventListener('click', () => openDeviceModal(btn.dataset.device));
    });
    dom.fleetTableBody.querySelectorAll('.btn-edit').forEach((btn) => {
      btn.addEventListener('click', () => openEditModal(btn.dataset.device, btn.dataset.firmware, btn.dataset.status));
    });
    dom.fleetTableBody.querySelectorAll('.btn-delete').forEach((btn) => {
      btn.addEventListener('click', () => deleteDevice(btn.dataset.device));
    });
  }

  function renderOverviewAlertsPreview() {
    if (!dom.overviewAlertsPreview) return;
    const openAlerts = state.alerts.filter((a) => a.status !== 'RESOLVED').slice(0, 4);

    if (openAlerts.length === 0) {
      dom.overviewAlertsPreview.innerHTML = '<tr><td colspan="6" class="table-loading">No active failure incidents. All fleet units nominal.</td></tr>';
      return;
    }

    const rows = openAlerts.map((a) => {
      const sevBadge = a.alert_level === 'CRITICAL' ? 'badge-danger' : 'badge-warning';
      return `
        <tr>
          <td><strong style="font-family: var(--font-mono);">#${a.id}</strong></td>
          <td><span style="font-family: var(--font-mono); font-weight:600;">${a.device_id}</span></td>
          <td><span class="badge ${sevBadge}">${a.alert_level}</span></td>
          <td>${a.summary}</td>
          <td style="font-size: 11px; color: var(--text-dim);">${a.created_at || 'Just now'}</td>
          <td><span class="badge badge-warning">${a.status}</span></td>
        </tr>
      `;
    }).join('');

    dom.overviewAlertsPreview.innerHTML = rows;
  }

  function renderAlertsTable() {
    if (!dom.alertsTableBody) return;

    if (dom.alertCounterBadge) {
      const openCount = state.alerts.filter((a) => a.status === 'OPEN').length;
      dom.alertCounterBadge.textContent = `${openCount} Critical Alerts`;
      dom.alertCounterBadge.className = openCount > 0 ? 'badge badge-danger' : 'badge badge-nominal';
    }

    if (state.alerts.length === 0) {
      dom.alertsTableBody.innerHTML = '<tr><td colspan="6" class="table-loading">No active operational alerts. Fleet nominal.</td></tr>';
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
        const alert = state.alerts.find((a) => a.id === alertId);
        if (alert) alert.status = newStatus;
        renderAlertsTable();
        renderOverviewAlertsPreview();
        fetchSummary();
        showToast(`Incident #${alertId} updated to ${newStatus}.`, 'success');
      }
    } catch (e) {
      showToast('Failed to update alert: ' + e.message, 'danger');
    }
  }

  function renderFeatureImportance(features) {
    if (!dom.featureImportanceBody) return;
    const rows = features.map((f) => `
      <tr>
        <td><strong style="font-family: var(--font-mono);">#${f.rank}</strong></td>
        <td><span style="font-family: var(--font-mono); font-weight: 600;">${f.feature}</span></td>
        <td>
          <div style="display: flex; align-items: center; gap: 8px;">
            <div style="flex: 1; height: 6px; background: rgba(255,255,255,0.08); border-radius: 99px; overflow: hidden;">
              <div style="width: ${Math.round(f.importance * 350)}%; height: 100%; background: var(--color-primary); border-radius: 99px;"></div>
            </div>
            <span style="font-family: var(--font-mono); font-size: 11px;">${(f.importance * 100).toFixed(1)}%</span>
          </div>
        </td>
        <td style="font-size: 11px; color: var(--text-dim);">${f.description}</td>
      </tr>
    `).join('');
    dom.featureImportanceBody.innerHTML = rows;
  }

  function renderTopology(data) {
    if (!dom.topologyGrid) return;
    const mesh = data.mesh || [];
    const html = mesh.map((node) => {
      const isHealthy = node.status === 'HEALTHY';
      const badgeClass = isHealthy ? 'badge-nominal' : 'badge-warning';
      return `
        <div class="topology-node-card">
          <div class="topology-node-header">
            <div>
              <div class="topology-node-name">${node.name}</div>
              <div class="topology-node-role">${node.role}</div>
            </div>
            <span class="badge ${badgeClass}">${node.status}</span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--border-subtle);">
            <span style="font-size: 11px; color: var(--text-dim);">Port: :${node.port}</span>
            <span class="topology-node-latency">RTT: ${node.latency_ms} ms</span>
          </div>
        </div>
      `;
    }).join('');
    dom.topologyGrid.innerHTML = html;
  }

  function renderSimulatorStatus(data) {
    if (!dom.simStatRunning) return;
    const isRunning = data.running;
    dom.simStatRunning.textContent = isRunning ? 'RUNNING' : 'STOPPED';
    dom.simStatRunning.style.color = isRunning ? 'var(--color-success)' : 'var(--text-dim)';
    if (dom.simDaemonBadge) {
      dom.simDaemonBadge.textContent = isRunning ? 'DAEMON STREAMING ACTIVE' : 'DAEMON IDLE';
      dom.simDaemonBadge.className = isRunning ? 'badge badge-nominal' : 'badge badge-warning';
    }
    if (dom.simStatDevices) dom.simStatDevices.textContent = `${data.device_count || 25} Endpoints`;
    if (dom.simStatTicks) dom.simStatTicks.textContent = data.total_ticks || 0;
    if (dom.simStatDispatched) dom.simStatDispatched.textContent = data.total_payloads_sent || 0;
    if (dom.simStatAnomalies) dom.simStatAnomalies.textContent = data.total_anomalies_injected || 0;
  }

  // ==============================================================================
  // Diagnostic Simulation Execution & SHAP
  // ==============================================================================
  function applyPreset(presetKey) {
    const p = PRESETS[presetKey];
    if (!p) return;
    dom.simTemp.value = p.temp;
    dom.simVolt.value = p.volt;
    dom.simCurr.value = p.curr;
    dom.simBattery.value = p.battery;
    dom.simNet.value = p.net;
    dom.simUptime.value = p.uptime;
  }

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
    dom.simRiskBadge.textContent = isHigh ? 'CRITICAL RISK' : 'LOW RISK';

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
  // Device Inspection Modal & RUL Prognostics
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

    // RUL Prognostics Calculation
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
      rulText = `~${rulHours} Hours Remaining (Immediate Maintenance Required)`;
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
      rulText = '> 720 Hours (Optimal Baseline)';
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
          },
          yVolt: {
            type: 'linear',
            position: 'right',
            grid: { drawOnChartArea: false },
            ticks: { color: '#3b82f6', font: { size: 9 } },
          },
          yBatt: {
            type: 'linear',
            position: 'right',
            grid: { drawOnChartArea: false },
            ticks: { color: '#10b981', font: { size: 9 } },
          },
        },
      },
    });
  }

  // ==============================================================================
  // Edit & Delete Device Actions
  // ==============================================================================
  function openEditModal(deviceId, firmware, devStatus) {
    if (!dom.editDeviceModal) return;
    dom.editDeviceId.value = deviceId;
    dom.editFirmware.value = firmware || '1.2.0';
    dom.editStatus.value = devStatus || 'ACTIVE';
    dom.editDeviceModal.style.display = 'flex';
  }

  async function deleteDevice(deviceId) {
    if (!confirm(`Are you sure you want to decommission and remove '${deviceId}'?`)) return;
    try {
      const res = await fetch(`/api/dashboard/devices/${deviceId}`, { method: 'DELETE' });
      if (res.ok) {
        showToast(`Device ${deviceId} decommissioned.`, 'info');
        await fetchFleet();
        await fetchSummary();
      }
    } catch (e) {
      showToast('Decommission failed: ' + e.message, 'danger');
    }
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

  function closeEditModal() {
    if (dom.editDeviceModal) dom.editDeviceModal.style.display = 'none';
  }

  // Start on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
