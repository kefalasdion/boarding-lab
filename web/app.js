const state = { config: null, result: null, comparison: [], provenanceFilter: "all" };
const byId = (id) => document.getElementById(id);
const svgNS = "http://www.w3.org/2000/svg";

function svgElement(name, attributes = {}) {
  const element = document.createElementNS(svgNS, name);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
  return element;
}

function clear(element) {
  while (element.firstChild) element.removeChild(element.firstChild);
}

function setBusy(message, isError = false) {
  const holder = byId("run-status").parentElement;
  holder.classList.toggle("is-busy", !isError && /Running|Loading/.test(message));
  holder.classList.toggle("is-error", isError);
  byId("run-status").textContent = message;
}

async function request(path, body) {
  const response = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = await response.json();
  if (!response.ok) {
    const detail = payload.issues?.map((issue) => `${issue.path}: ${issue.message}`).join(" · ") || payload.message || payload.error;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return payload;
}

function scenarioFromForm(strategyOverride = null, accessOverride = null) {
  return {
    flightContext: {
      delayMinutes: Number(byId("delay-minutes").value),
      priorDelayUpdates: Number(byId("delay-updates").value),
      priorGateWaitMinutes: Number(byId("prior-gate-wait").value),
    },
    population: {
      familyPassengerShare: Number(byId("family-share").value) / 100,
      handLuggageShare: Number(byId("bag-share").value) / 100,
    },
    preparation: {
      policy: { readinessTarget: Number(byId("readiness-target").value) / 100 },
    },
    access: { mode: accessOverride || byId("access-mode").value },
    boarding: {
      strategy: strategyOverride || byId("strategy").value,
      serviceModel: byId("service-model").value,
    },
  };
}

function seconds(value) {
  if (value === null || value === undefined) return "Not completed";
  const rounded = Math.max(0, Math.round(value));
  const minutes = Math.floor(rounded / 60);
  return `${minutes}:${String(rounded % 60).padStart(2, "0")}`;
}

function number(value, digits = 2) {
  return value === null || value === undefined ? "—" : Number(value).toFixed(digits);
}

function passengerColor(value) {
  const bounded = Math.max(0, Math.min(1, value));
  const stops = bounded < 0.5
    ? [[69, 143, 99], [221, 180, 78], bounded * 2]
    : [[221, 180, 78], [185, 69, 60], (bounded - 0.5) * 2];
  return `rgb(${stops[0].map((channel, index) => Math.round(channel + (stops[1][index] - channel) * stops[2])).join(",")})`;
}

function renderPopulation(result) {
  const holder = byId("t0-population");
  clear(holder);
  const fragment = document.createDocumentFragment();
  result.passengers.forEach((passenger, index) => {
    const mark = document.createElement("span");
    mark.className = `passenger-mark${passenger.family_id ? " is-family" : ""}`;
    mark.style.setProperty("--passenger-color", passengerColor(passenger.initial_frustration));
    mark.style.setProperty("--passenger-index", index);
    mark.title = `${passenger.row}${passenger.seat} · initial F ${number(passenger.initial_frustration)} · tolerance ${number(passenger.tolerance_threshold)}${passenger.family_id ? ` · family ${passenger.family_id}` : ""}`;
    mark.setAttribute("aria-label", mark.title);
    fragment.appendChild(mark);
  });
  holder.appendChild(fragment);
  const summary = result.phases.part1_t0_state.initial_frustration;
  byId("t0-summary").textContent = `Mean ${number(summary.mean)} · P90 ${number(summary.p90)} · range ${number(summary.minimum)}–${number(summary.maximum)}`;
}

function chartFrame(svg, width, height, yTicks, yFormatter = (value) => value) {
  const padding = { left: 54, right: 20, top: 18, bottom: 38 };
  yTicks.forEach((value) => {
    const y = padding.top + (height - padding.top - padding.bottom) * (1 - value);
    svg.appendChild(svgElement("line", { x1: padding.left, y1: y, x2: width - padding.right, y2: y, class: "chart-grid" }));
    const label = svgElement("text", { x: padding.left - 10, y: y + 4, "text-anchor": "end" });
    label.textContent = yFormatter(value);
    svg.appendChild(label);
  });
  svg.appendChild(svgElement("line", { x1: padding.left, y1: height - padding.bottom, x2: width - padding.right, y2: height - padding.bottom, class: "chart-axis" }));
  return padding;
}

function linePath(data, xAccessor, yAccessor, xMin, xMax, yMin, yMax, frame, width, height) {
  const plotWidth = width - frame.left - frame.right;
  const plotHeight = height - frame.top - frame.bottom;
  return data.map((item, index) => {
    const x = frame.left + ((xAccessor(item) - xMin) / Math.max(1e-9, xMax - xMin)) * plotWidth;
    const y = frame.top + (1 - (yAccessor(item) - yMin) / Math.max(1e-9, yMax - yMin)) * plotHeight;
    return `${index ? "L" : "M"}${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");
}

function timeAxis(svg, frame, width, height, start, end) {
  [0, 0.25, 0.5, 0.75, 1].forEach((ratio) => {
    const x = frame.left + ratio * (width - frame.left - frame.right);
    const label = svgElement("text", { x, y: height - 12, "text-anchor": "middle" });
    label.textContent = seconds(start + ratio * (end - start));
    svg.appendChild(label);
  });
}

function renderPreparation(result) {
  const svg = byId("preparation-chart");
  clear(svg);
  const width = 700, height = 300, data = result.phases.part2_preparation.progress;
  const frame = chartFrame(svg, width, height, [0, .25, .5, .75, 1], (value) => `${Math.round(value * 100)}%`);
  const end = data.at(-1).time_seconds;
  const passengerCount = result.metrics.passenger_count;
  const path = linePath(data, (item) => item.time_seconds, (item) => item.prepared_count / passengerCount, 0, end, 0, 1, frame, width, height);
  svg.appendChild(svgElement("path", { d: path, class: "chart-path", stroke: "#1768b8", "stroke-width": 4 }));
  result.phases.part2_preparation.events.filter((event) => event.type === "preparation_correction").forEach((event) => {
    const x = frame.left + (event.time_seconds / Math.max(1, end)) * (width - frame.left - frame.right);
    svg.appendChild(svgElement("circle", { cx: x, cy: 26, r: 3.2, class: "correction-mark" }));
  });
  timeAxis(svg, frame, width, height, 0, end);
  const phase = result.phases.part2_preparation;
  byId("preparation-caption").textContent = `${phase.correction_count} corrections · ${Math.round(phase.readiness.overall * 100)}% ready overall · ${Math.round(phase.readiness.first_cohort * 100)}% of first cohort ready.`;
}

function renderEmbarkation(result) {
  const svg = byId("embarkation-chart");
  clear(svg);
  const width = 700, height = 300, data = result.phases.part3_embarkation.aircraft.progress;
  const frame = chartFrame(svg, width, height, [0, .25, .5, .75, 1], (value) => `${Math.round(value * 100)}%`);
  const start = data[0].time_seconds, end = data.at(-1).time_seconds, total = result.metrics.passenger_count;
  const series = [
    ["access_arrived_count", "#b87616", 2],
    ["entered_count", "#7057c6", 2.5],
    ["seated_count", "#1768b8", 4],
  ];
  series.forEach(([key, color, strokeWidth]) => {
    const path = linePath(data, (item) => item.time_seconds, (item) => item[key] / total, start, end, 0, 1, frame, width, height);
    svg.appendChild(svgElement("path", { d: path, class: "chart-path", stroke: color, "stroke-width": strokeWidth }));
  });
  timeAxis(svg, frame, width, height, start, end);
  const access = result.phases.part3_embarkation.access;
  byId("embarkation-caption").textContent = `${access.mode === "bus" ? `${access.buses.length} buses` : "Jet bridge"} · last aircraft-door arrival at ${seconds(access.last_door_arrival_time_seconds)} · ${result.metrics.seated_count}/${total} seated.`;
}

function renderTrajectory(result) {
  const svg = byId("frustration-chart");
  clear(svg);
  const width = 1200, height = 380, data = result.trajectory;
  const frame = chartFrame(svg, width, height, [0, .25, .5, .75, 1], (value) => value.toFixed(2));
  const start = 0, end = data.at(-1).time_seconds;
  [["mean_frustration", "#1768b8", 4, ""], ["p90_frustration", "#7057c6", 2.5, "is-p90"]].forEach(([key, color, strokeWidth, extraClass]) => {
    const path = linePath(data, (item) => item.time_seconds, (item) => item[key], start, end, 0, 1, frame, width, height);
    svg.appendChild(svgElement("path", { d: path, class: `chart-path${extraClass ? ` ${extraClass}` : ""}`, stroke: color, "stroke-width": strokeWidth }));
  });
  const prepEnd = result.metrics.timings_seconds.preparation;
  const prepX = frame.left + (prepEnd / Math.max(1, end)) * (width - frame.left - frame.right);
  svg.appendChild(svgElement("line", { x1: prepX, y1: frame.top, x2: prepX, y2: height - frame.bottom, stroke: "#b87616", "stroke-dasharray": "4 5" }));
  const label = svgElement("text", { x: prepX + 7, y: frame.top + 14 });
  label.textContent = "Embarkation starts";
  svg.appendChild(label);
  timeAxis(svg, frame, width, height, start, end);
  const experience = result.metrics.passenger_experience;
  byId("trajectory-summary").textContent = `${Math.round(experience.share_peak_above_threshold * 100)}% peak above ${experience.threshold}`;
}

function renderHistogram(svgId, values, color, captionId, summary, unit) {
  const svg = byId(svgId);
  clear(svg);
  const width = 700, height = 280, frame = { left: 48, right: 18, top: 15, bottom: 38 };
  const bins = 14;
  const minimum = Math.min(...values), maximum = Math.max(...values);
  const span = Math.max(1e-9, maximum - minimum);
  const counts = Array(bins).fill(0);
  values.forEach((value) => { counts[Math.min(bins - 1, Math.floor(((value - minimum) / span) * bins))] += 1; });
  const maxCount = Math.max(...counts, 1);
  const plotWidth = width - frame.left - frame.right;
  const plotHeight = height - frame.top - frame.bottom;
  counts.forEach((count, index) => {
    const barWidth = plotWidth / bins - 3;
    const barHeight = (count / maxCount) * plotHeight;
    const bar = svgElement("rect", { x: frame.left + index * (plotWidth / bins) + 1, y: frame.top + plotHeight - barHeight, width: barWidth, height: barHeight, class: "histogram-bar", fill: color });
    bar.style.animationDelay = `${index * 24}ms`;
    svg.appendChild(bar);
  });
  svg.appendChild(svgElement("line", { x1: frame.left, y1: height - frame.bottom, x2: width - frame.right, y2: height - frame.bottom, class: "chart-axis" }));
  [[frame.left, minimum], [frame.left + plotWidth / 2, minimum + span / 2], [width - frame.right, maximum]].forEach(([x, value]) => {
    const label = svgElement("text", { x, y: height - 12, "text-anchor": x === frame.left ? "start" : x === width - frame.right ? "end" : "middle" });
    label.textContent = number(value, unit ? 1 : 2);
    svg.appendChild(label);
  });
  byId(captionId).textContent = `Mean ${number(summary.mean)}${unit} · P90 ${number(summary.p90)}${unit} · 95% mean interval ${number(summary.mean_ci95_low)}–${number(summary.mean_ci95_high)}${unit}`;
}

function renderMetrics(result) {
  const timings = result.metrics.timings_seconds;
  byId("metric-total").textContent = seconds(timings.total_t0_to_last_seat);
  byId("metric-preparation").textContent = seconds(timings.preparation);
  byId("metric-embarkation").textContent = seconds(timings.embarkation);
  byId("metric-cabin").textContent = seconds(timings.cabin_boarding);
  byId("part-1-value").textContent = `${result.metrics.passenger_count} individual passengers`;
  byId("part-2-value").textContent = `${seconds(timings.preparation)} · ${result.metrics.correction_events} corrections`;
  byId("part-3-value").textContent = `${seconds(timings.embarkation)} · ${result.metrics.seated_count}/${result.metrics.passenger_count} seated`;
  document.querySelectorAll(".phase-block").forEach((element) => element.classList.add("has-result"));
}

function renderRun(result) {
  state.result = result;
  renderMetrics(result);
  renderPopulation(result);
  renderPreparation(result);
  renderEmbarkation(result);
  renderTrajectory(result);
  const experience = result.metrics.passenger_experience;
  renderHistogram("burden-histogram", result.passengers.map((passenger) => passenger.frustration_burden), "#1768b8", "burden-caption", experience.frustration_burden_f_minutes, " F·min");
  renderHistogram("peak-histogram", result.passengers.map((passenger) => passenger.peak_frustration), "#7057c6", "peak-caption", experience.peak_frustration, "");
  const workspace = byId("results");
  workspace.classList.remove("results-enter");
  void workspace.offsetWidth;
  workspace.classList.add("results-enter");
  setBusy(result.status === "valid" ? `${result.metrics.seated_count}/${result.metrics.passenger_count} seated` : "Timed out — partial result shown", result.status !== "valid");
}

function appendCell(row, text, className = "") {
  const cell = document.createElement("td");
  cell.textContent = text;
  if (className) cell.className = className;
  row.appendChild(cell);
}

function renderComparison(rows) {
  const body = byId("monte-carlo-table").querySelector("tbody");
  clear(body);
  rows.sort((a, b) => (a.data.summaries.total_seconds?.mean ?? Infinity) - (b.data.summaries.total_seconds?.mean ?? Infinity));
  rows.forEach(({ strategy, data }) => {
    const row = document.createElement("tr");
    row.tabIndex = 0;
    row.addEventListener("click", () => {
      body.querySelectorAll("tr").forEach((item) => item.classList.remove("is-selected"));
      row.classList.add("is-selected");
    });
    const total = data.summaries.total_seconds;
    appendCell(row, strategy.name, "strategy-name");
    appendCell(row, strategy.recommendedAccess);
    appendCell(row, String(data.valid_runs));
    appendCell(row, String(data.timed_out_runs), data.timed_out_runs ? "run-problem" : "");
    appendCell(row, String(data.invalid_runs), data.invalid_runs ? "run-problem" : "");
    appendCell(row, total ? seconds(total.mean) : "—", "interval");
    appendCell(row, total ? `${seconds(total.p10)}–${seconds(total.p90)}` : "—", "interval");
    appendCell(row, total ? `${seconds(total.mean_ci95_low)}–${seconds(total.mean_ci95_high)}` : "—", "interval");
    appendCell(row, data.summaries.preparation_seconds ? seconds(data.summaries.preparation_seconds.mean) : "—", "interval");
    appendCell(row, data.summaries.cabin_boarding_seconds ? seconds(data.summaries.cabin_boarding_seconds.mean) : "—", "interval");
    appendCell(row, data.summaries.mean_frustration_burden ? number(data.summaries.mean_frustration_burden.mean) : "—", "interval");
    body.appendChild(row);
  });
}

function renderProvenance() {
  const body = byId("provenance-table").querySelector("tbody");
  clear(body);
  state.config.parameterProvenance
    .filter((entry) => state.provenanceFilter === "all" || entry.category === state.provenanceFilter)
    .forEach((entry) => {
      const row = document.createElement("tr");
      appendCell(row, entry.path, "parameter-path");
      const statusCell = document.createElement("td");
      const badge = document.createElement("span");
      badge.className = "provenance-badge";
      badge.dataset.category = entry.category;
      badge.textContent = entry.category;
      badge.title = entry.status;
      statusCell.appendChild(badge);
      row.appendChild(statusCell);
      appendCell(row, typeof entry.value === "object" ? JSON.stringify(entry.value) : String(entry.value));
      appendCell(row, [entry.source, entry.note].filter(Boolean).join(" · "), "source-note");
      body.appendChild(row);
    });
}

async function runFlight(event) {
  event?.preventDefault();
  const runButton = byId("run-flight");
  runButton.disabled = true;
  setBusy("Running deterministic flight…");
  try {
    const result = await request("/api/run", { scenario: scenarioFromForm(), seed: Number(byId("seed").value) });
    renderRun(result);
  } catch (error) {
    setBusy(error.message, true);
  } finally {
    runButton.disabled = false;
  }
}

async function compareStrategies() {
  const button = byId("compare-strategies");
  button.disabled = true;
  const runCount = Number(byId("monte-carlo-runs").value);
  const seed = Number(byId("seed").value);
  setBusy("Running Monte Carlo comparison…");
  byId("comparison-status").textContent = `0/${state.config.strategies.length} strategies complete`;
  let completed = 0;
  try {
    const promises = state.config.strategies.map(async (strategy, index) => {
      const data = await request("/api/monte-carlo", {
        scenario: scenarioFromForm(strategy.id, strategy.recommendedAccess),
        runs: runCount,
        baseSeed: seed + index * 1000,
      });
      completed += 1;
      byId("comparison-status").textContent = `${completed}/${state.config.strategies.length} strategies complete`;
      return { strategy, data };
    });
    state.comparison = await Promise.all(promises);
    renderComparison(state.comparison);
    const valid = state.comparison.reduce((sum, row) => sum + row.data.valid_runs, 0);
    const timedOut = state.comparison.reduce((sum, row) => sum + row.data.timed_out_runs, 0);
    const invalid = state.comparison.reduce((sum, row) => sum + row.data.invalid_runs, 0);
    byId("comparison-status").textContent = `${valid} valid · ${timedOut} timed out · ${invalid} invalid`;
    setBusy("Comparison complete");
  } catch (error) {
    byId("comparison-status").textContent = "Comparison failed";
    setBusy(error.message, true);
  } finally {
    button.disabled = false;
  }
}

function bindRange(inputId, outputId, suffix = "") {
  const input = byId(inputId), output = byId(outputId);
  input.addEventListener("input", () => { output.textContent = `${input.value}${suffix}`; });
}

async function initialize() {
  try {
    state.config = await request("/api/config");
    byId("schema-version").textContent = state.config.schemaVersion;
    const strategySelect = byId("strategy");
    state.config.strategies.forEach((strategy) => {
      const option = document.createElement("option");
      option.value = strategy.id;
      option.textContent = strategy.name;
      option.dataset.access = strategy.recommendedAccess;
      strategySelect.appendChild(option);
    });
    const defaults = state.config.defaultScenario;
    strategySelect.value = defaults.boarding.strategy;
    byId("access-mode").value = defaults.access.mode;
    byId("service-model").value = defaults.boarding.serviceModel;
    strategySelect.addEventListener("change", () => { byId("access-mode").value = strategySelect.selectedOptions[0].dataset.access; });
    renderProvenance();
    setBusy("Model ready");
    await runFlight();
  } catch (error) {
    setBusy(error.message, true);
  }
}

bindRange("delay-minutes", "delay-output", " min");
bindRange("prior-gate-wait", "gate-wait-output", " min");
bindRange("delay-updates", "updates-output");
bindRange("family-share", "family-output", "%");
bindRange("bag-share", "bag-output", "%");
bindRange("readiness-target", "readiness-output", "%");
byId("scenario-form").addEventListener("submit", runFlight);
byId("compare-strategies").addEventListener("click", compareStrategies);
byId("provenance-filter").addEventListener("change", (event) => { state.provenanceFilter = event.target.value; renderProvenance(); });
initialize();
