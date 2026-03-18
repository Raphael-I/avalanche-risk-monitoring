const state = {
  zones: [],
  assessments: [],
  summary: null,
  alerts: [],
  analytics: null,
  health: null,
  selectedZoneId: null,
  zoneHistories: new Map(),
};

const levelOrder = {
  low: 0,
  moderate: 1,
  considerable: 2,
  high: 3,
  extreme: 4,
};

async function requestJson(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${path}`);
  }
  return response.json();
}

function fmt(value, digits = 0) {
  return Number(value).toFixed(digits);
}

function titleCase(value) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function levelClass(level) {
  return String(level || "low").toLowerCase();
}

function formatTimestamp(value) {
  return new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function bootstrap() {
  attachEvents();
  await loadDashboardData();
}

function attachEvents() {
  document.getElementById("refreshButton").addEventListener("click", async () => {
    const button = document.getElementById("refreshButton");
    button.disabled = true;
    button.textContent = "Generating...";
    try {
      await requestJson(`/runs?tick=${Date.now() % 1000}`, { method: "POST" });
      state.zoneHistories.clear();
      await loadDashboardData();
    } finally {
      button.disabled = false;
      button.textContent = "Generate New Run";
    }
  });
}

async function loadDashboardData() {
  document.body.classList.add("loading");
  try {
    const [zones, health, assessments, alerts, summary, analytics] = await Promise.all([
      requestJson("/zones"),
      requestJson("/health"),
      requestJson("/assessments/latest"),
      requestJson("/alerts/latest"),
      requestJson("/summary/latest"),
      requestJson("/analytics/zones?limit=24"),
    ]);

    state.zones = zones;
    state.health = health;
    state.assessments = assessments.sort((a, b) => levelOrder[b.level] - levelOrder[a.level] || b.score - a.score);
    state.alerts = alerts;
    state.summary = summary;
    state.analytics = analytics;
    state.selectedZoneId = state.selectedZoneId || state.assessments[0]?.zone_id || null;

    await ensureZoneHistory(state.selectedZoneId);
    renderOverview();
    renderZoneBoard();
    renderAlerts();
    renderSelectedZone();
  } catch (error) {
    console.error(error);
  } finally {
    document.body.classList.remove("loading");
  }
}

async function ensureZoneHistory(zoneId) {
  if (!zoneId || state.zoneHistories.has(zoneId)) {
    return;
  }
  const payload = await requestJson(`/history/zones/${zoneId}?limit=24`);
  state.zoneHistories.set(zoneId, payload.history);
}

function renderOverview() {
  const summary = state.summary;
  const analyticsOverview = state.analytics?.overview || {};
  const highestZone = getZone(summary?.highest_risk_zone_id);
  document.getElementById("headlineText").textContent = summary?.headline || "No summary available";
  document.getElementById("headlineSubtext").textContent = summary?.primary_concerns?.length
    ? `Primary concerns: ${summary.primary_concerns.map(titleCase).join(", ")}`
    : "Waiting for assessments";
  document.getElementById("averageScore").textContent = summary ? fmt(summary.average_score, 1) : "--";
  document.getElementById("averageScoreNote").textContent = `${analyticsOverview.zone_count || 0} zones in view`;
  document.getElementById("highestZone").textContent = highestZone?.name || summary?.highest_risk_zone_id || "--";
  document.getElementById("highestZoneLevel").textContent = summary?.highest_risk_level
    ? `${titleCase(summary.highest_risk_level)} danger`
    : "Waiting for data";
  document.getElementById("activeAlertCount").textContent = String(state.alerts.length);
  document.getElementById("activeAlertNote").textContent = state.alerts.length
    ? `${getZone(state.alerts[0].zone_id)?.name || state.alerts[0].zone_id} currently leads the alert queue`
    : "No active threshold breaches";
  document.getElementById("systemState").textContent = `${titleCase(state.health?.environment || "local")} / ${titleCase(state.health?.fabric_mode || "disabled")}`;
  document.getElementById("lastRefresh").textContent = summary?.generated_at
    ? formatTimestamp(summary.generated_at)
    : "Not available";
}

function renderZoneBoard() {
  const board = document.getElementById("zoneBoard");
  board.innerHTML = "";

  state.assessments.forEach((assessment) => {
    const analytics = state.analytics?.zones?.find((zone) => zone.zone_id === assessment.zone_id);
    const zone = getZone(assessment.zone_id);
    const card = document.createElement("button");
    card.type = "button";
    card.className = `zone-card ${state.selectedZoneId === assessment.zone_id ? "selected" : ""}`;
    card.innerHTML = `
      <div class="zone-card-head">
        <div class="zone-name-wrap">
          <h3>${zone?.name || assessment.zone_id}</h3>
          <p class="zone-meta">${zone ? `${zone.aspect} aspect · ${zone.elevation_m} m · ${zone.slope_angle}° slope` : assessment.zone_id}</p>
          <p class="zone-caption">${assessment.summary}</p>
        </div>
        <div>
          <div class="zone-score">${assessment.score}</div>
          <div class="zone-chip ${levelClass(assessment.level)}">${titleCase(assessment.level)}</div>
        </div>
      </div>
      <div class="zone-metrics">
        <div class="metric">
          <span>Confidence</span>
          <strong>${fmt(assessment.confidence * 100)}%</strong>
        </div>
        <div class="metric">
          <span>Trend</span>
          <strong>${analytics ? titleCase(analytics.trend) : "Stable"}</strong>
        </div>
        <div class="metric">
          <span>Peak score</span>
          <strong>${analytics ? analytics.max_score : assessment.score}</strong>
        </div>
      </div>
    `;
    card.addEventListener("click", async () => {
      state.selectedZoneId = assessment.zone_id;
      await ensureZoneHistory(assessment.zone_id);
      renderZoneBoard();
      renderSelectedZone();
    });
    board.appendChild(card);
  });
}

function renderAlerts() {
  const list = document.getElementById("alertsList");
  list.innerHTML = "";
  if (!state.alerts.length) {
    list.innerHTML = `<div class="empty-state">No active alerts. Generate another run to stress-test the simulation.</div>`;
    return;
  }

  state.alerts.forEach((alert) => {
    const zone = getZone(alert.zone_id);
    const item = document.createElement("article");
    item.className = "alert-item";
    item.innerHTML = `
      <div class="alert-topline">
        <div>
          <strong>${alert.title}</strong>
          <p class="alerts-meta">${zone?.name || alert.zone_id} · ${formatTimestamp(alert.generated_at)}</p>
        </div>
        <span class="zone-chip ${levelClass(alert.severity)}">${titleCase(alert.severity)}</span>
      </div>
      <p>${alert.message}</p>
      <p class="alerts-meta">Trigger factors: ${alert.trigger_factors.map(titleCase).join(", ")}</p>
    `;
    list.appendChild(item);
  });
}

function renderSelectedZone() {
  const assessment = state.assessments.find((item) => item.zone_id === state.selectedZoneId);
  const history = state.zoneHistories.get(state.selectedZoneId) || [];
  const analytics = state.analytics?.zones?.find((item) => item.zone_id === state.selectedZoneId);
  const zone = getZone(state.selectedZoneId);

  document.getElementById("selectedZoneTitle").textContent = zone?.name || assessment?.zone_id || "Choose a zone";
  document.getElementById("selectedZoneBadge").className = `selected-zone-badge ${levelClass(assessment?.level)}`;
  document.getElementById("selectedZoneBadge").textContent = assessment
    ? `${titleCase(assessment.level)} danger`
    : "Awaiting selection";
  document.getElementById("riskTrendLabel").textContent = analytics
    ? `${titleCase(analytics.trend)} trend, avg ${fmt(analytics.average_score, 1)}`
    : "No trend data";

  renderRiskChart(history);
  renderSensorTrends(history);
  renderRiskFactors(assessment);
  renderAnalyticsDetail(analytics, history);
}

function renderRiskFactors(assessment) {
  const host = document.getElementById("riskFactors");
  host.innerHTML = "";
  if (!assessment) {
    host.innerHTML = `<div class="empty-state">Select a zone to inspect contributing factors.</div>`;
    return;
  }

  const list = document.createElement("div");
  list.className = "factor-list";
  assessment.contributing_factors.slice(0, 4).forEach((factor) => {
    const item = document.createElement("div");
    item.className = "factor-item";
    item.innerHTML = `
      <strong>${titleCase(factor.factor)} <span class="factor-meta">(${factor.impact})</span></strong>
      <p>${factor.explanation}</p>
      <p class="factor-meta">Weighted contribution ${fmt(factor.score, 1)} / ${fmt(factor.weight, 1)}</p>
    `;
    list.appendChild(item);
  });
  host.appendChild(list);
}

function renderAnalyticsDetail(analytics, history) {
  const host = document.getElementById("analyticsDetail");
  host.innerHTML = "";
  if (!analytics) {
    host.innerHTML = `<div class="empty-state">No analytics available for the selected zone.</div>`;
    return;
  }

  const latest = history[history.length - 1];
  const rows = [
    `Latest score: ${analytics.latest_score}`,
    `Historical average: ${fmt(analytics.average_score, 1)}`,
    `Peak score in window: ${analytics.max_score}`,
    `Runs in window: ${analytics.run_count}`,
    latest ? `Latest snowfall 24h: ${fmt(latest.snowfall_24h_cm, 1)} cm` : null,
    latest ? `Latest wind speed: ${fmt(latest.wind_speed_kmh, 1)} km/h` : null,
  ].filter(Boolean);

  rows.forEach((text) => {
    const row = document.createElement("div");
    row.className = "analytics-row";
    row.innerHTML = `<p>${text}</p>`;
    host.appendChild(row);
  });
}

function renderSensorTrends(history) {
  const grid = document.getElementById("sensorTrendGrid");
  grid.innerHTML = "";
  if (!history.length) {
    grid.innerHTML = `<div class="empty-state">No sensor history available.</div>`;
    return;
  }

  const sensors = [
    { label: "24h snowfall", key: "snowfall_24h_cm", unit: "cm" },
    { label: "Wind speed", key: "wind_speed_kmh", unit: "km/h" },
    { label: "Weak layer", key: "weak_layer_index", unit: "" },
  ];

  sensors.forEach((sensor) => {
    const values = history.map((point) => point[sensor.key]);
    const latest = values[values.length - 1];
    const tile = document.createElement("div");
    tile.className = "sensor-tile";
    tile.innerHTML = `
      <header>
        <strong>${sensor.label}</strong>
        <span class="mini-note">${fmt(latest, sensor.key === "weak_layer_index" ? 2 : 1)} ${sensor.unit}</span>
      </header>
      <svg class="sensor-spark" viewBox="0 0 280 44" aria-hidden="true">${buildSparkSvg(values, 280, 44)}</svg>
    `;
    grid.appendChild(tile);
  });
}

function renderRiskChart(history) {
  const svg = document.getElementById("riskChart");
  if (!history.length) {
    svg.innerHTML = "";
    return;
  }

  const width = 560;
  const height = 220;
  const padX = 28;
  const padY = 18;
  const chartWidth = width - padX * 2;
  const chartHeight = height - padY * 2;
  const points = history.map((point, index) => {
    const x = padX + (chartWidth * index) / Math.max(history.length - 1, 1);
    const y = height - padY - (point.score / 100) * chartHeight;
    return { x, y, score: point.score, label: formatTimestamp(point.generated_at), level: point.level };
  });

  const path = points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");
  const areaPath = `${path} L ${points.at(-1).x} ${height - padY} L ${points[0].x} ${height - padY} Z`;
  const guides = [25, 50, 75].map((level) => {
    const y = height - padY - (level / 100) * chartHeight;
    return `<line x1="${padX}" x2="${width - padX}" y1="${y}" y2="${y}" stroke="rgba(16,35,49,0.11)" stroke-dasharray="4 6" />
      <text x="${padX}" y="${y - 6}" fill="rgba(96,114,130,0.9)" font-size="11">${level}</text>`;
  }).join("");

  const pointsMarkup = points.map((point) => `
    <circle cx="${point.x}" cy="${point.y}" r="4" fill="#123047" />
    <title>${point.label}: ${point.score} (${point.level})</title>
  `).join("");

  svg.innerHTML = `
    <defs>
      <linearGradient id="riskFill" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="rgba(197,58,55,0.35)" />
        <stop offset="100%" stop-color="rgba(197,58,55,0.03)" />
      </linearGradient>
    </defs>
    ${guides}
    <path d="${areaPath}" fill="url(#riskFill)"></path>
    <path d="${path}" fill="none" stroke="#0f3a51" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></path>
    ${pointsMarkup}
  `;
}

function buildSparkSvg(values, width, height) {
  const pad = 4;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(max - min, 1);
  const points = values.map((value, index) => {
    const x = pad + ((width - pad * 2) * index) / Math.max(values.length - 1, 1);
    const y = height - pad - ((value - min) / span) * (height - pad * 2);
    return `${index === 0 ? "M" : "L"} ${x} ${y}`;
  }).join(" ");
  return `<path d="${points}" fill="none" stroke="#2f627d" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>`;
}

function getZone(zoneId) {
  return state.zones.find((zone) => zone.zone_id === zoneId) || null;
}

bootstrap();
