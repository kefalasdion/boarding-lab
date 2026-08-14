import {requestJson} from './api.js';

const SVG_NS = 'http://www.w3.org/2000/svg';

function svgElement(name, attributes = {}) {
  const element = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
  return element;
}

function lineChart(svg, samples, valueKey, maximum) {
  svg.replaceChildren();
  if (!samples?.length) return;
  const width = 700;
  const height = 300;
  const padding = 34;
  const end = Math.max(...samples.map((sample) => sample.time_seconds), 1);
  const points = samples.map((sample) => [
    padding + sample.time_seconds / end * (width - padding * 2),
    height - padding - (sample[valueKey] ?? 0) / maximum * (height - padding * 2),
  ]);
  for (let index = 0; index <= 4; index += 1) {
    const y = padding + index * (height - padding * 2) / 4;
    svg.append(svgElement('line', {x1: padding, y1: y, x2: width - padding, y2: y, class: 'expert-gridline'}));
  }
  svg.append(svgElement('polyline', {
    points: points.map((point) => point.join(',')).join(' '),
    class: 'expert-line',
  }));
}

function histogram(svg, values) {
  svg.replaceChildren();
  if (!values.length) return;
  const width = 700;
  const height = 280;
  const bins = 16;
  const maximumValue = Math.max(...values, 1e-9);
  const counts = Array(bins).fill(0);
  for (const value of values) counts[Math.min(bins - 1, Math.floor(value / maximumValue * bins))] += 1;
  const maximumCount = Math.max(...counts, 1);
  counts.forEach((count, index) => {
    const barWidth = (width - 54) / bins;
    const barHeight = count / maximumCount * (height - 52);
    svg.append(svgElement('rect', {
      x: 36 + index * barWidth + 1,
      y: height - 28 - barHeight,
      width: Math.max(1, barWidth - 2),
      height: barHeight,
      class: 'expert-bar',
    }));
  });
}

function renderFlight(result) {
  lineChart(document.getElementById('preparation-chart'), result.phases.part2_preparation.progress, 'prepared_count', result.metrics.passenger_count);
  lineChart(document.getElementById('embarkation-chart'), result.phases.part3_embarkation.aircraft.progress, 'seated_count', result.metrics.passenger_count);
  histogram(document.getElementById('burden-histogram'), result.passengers.map((passenger) => passenger.frustration_burden));
  histogram(document.getElementById('peak-histogram'), result.passengers.map((passenger) => passenger.peak_frustration));
}

function renderProvenance(config) {
  const table = document.getElementById('provenance-table');
  table.replaceChildren();
  const head = document.createElement('thead');
  head.innerHTML = '<tr><th>Parameter</th><th>Evidence status</th><th>Default</th><th>Source / note</th></tr>';
  const body = document.createElement('tbody');
  for (const entry of config.parameterProvenance) {
    const row = document.createElement('tr');
    const path = document.createElement('th');
    path.scope = 'row';
    path.textContent = entry.path;
    const status = document.createElement('td');
    const badge = document.createElement('span');
    badge.className = 'provenance-badge';
    badge.dataset.category = entry.category;
    badge.textContent = entry.category;
    badge.title = entry.status;
    status.append(badge);
    const value = document.createElement('td');
    value.textContent = typeof entry.value === 'object' ? JSON.stringify(entry.value) : String(entry.value);
    const source = document.createElement('td');
    source.textContent = [entry.source, entry.note].filter(Boolean).join(' · ');
    row.append(path, status, value, source);
    body.append(row);
  }
  table.append(head, body);
}

function renderMonteCarlo(data, strategyName) {
  const table = document.getElementById('monte-carlo-table');
  table.replaceChildren();
  const head = document.createElement('thead');
  head.innerHTML = '<tr><th>Strategy</th><th>Valid</th><th>Timed out</th><th>Invalid</th><th>Total mean</th><th>P10–P90</th><th>95% mean interval</th></tr>';
  const body = document.createElement('tbody');
  const row = document.createElement('tr');
  const total = data.summaries.total_seconds;
  const values = [
    strategyName,
    data.valid_runs,
    data.timed_out_runs,
    data.invalid_runs,
    total ? total.mean.toFixed(1) : 'Unavailable',
    total ? `${total.p10.toFixed(1)}–${total.p90.toFixed(1)}` : 'Unavailable',
    total ? `${total.mean_ci95_low.toFixed(1)}–${total.mean_ci95_high.toFixed(1)}` : 'Unavailable',
  ];
  values.forEach((value, index) => {
    const cell = document.createElement(index === 0 ? 'th' : 'td');
    if (index === 0) cell.scope = 'row';
    cell.textContent = String(value);
    row.append(cell);
  });
  body.append(row);
  table.append(head, body);
}

export function initializeExpert(config) {
  renderProvenance(config);
  const mount = document.getElementById('expert-controls');
  const form = document.createElement('form');
  form.className = 'expert-control-form';
  const strategy = document.createElement('select');
  strategy.setAttribute('aria-label', 'Expert boarding strategy');
  for (const item of config.strategies) {
    const option = document.createElement('option');
    option.value = item.id;
    option.textContent = item.name;
    option.dataset.access = item.recommendedAccess;
    strategy.append(option);
  }
  const runs = document.createElement('input');
  runs.type = 'number';
  runs.min = '1';
  runs.max = '30';
  runs.value = '6';
  runs.setAttribute('aria-label', 'Expert repeated runs');
  const runFlight = document.createElement('button');
  runFlight.type = 'button';
  runFlight.className = 'button button-primary';
  runFlight.textContent = 'Run detailed flight';
  const runRepeated = document.createElement('button');
  runRepeated.type = 'button';
  runRepeated.className = 'button button-quiet';
  runRepeated.textContent = 'Run uncertainty sample';
  const status = document.createElement('span');
  status.className = 'expert-status';
  status.setAttribute('aria-live', 'polite');
  form.append(strategy, runs, runFlight, runRepeated, status);
  mount.replaceChildren(form);

  runFlight.addEventListener('click', async () => {
    status.textContent = 'Running detailed flight…';
    try {
      const result = await requestJson('/api/run', {
        scenario: {
          access: {mode: strategy.selectedOptions[0].dataset.access},
          boarding: {strategy: strategy.value},
        },
        seed: 20260813,
      });
      renderFlight(result);
      status.textContent = result.status === 'valid' ? 'Detailed flight ready' : 'Partial timed-out result shown';
    } catch (error) {
      status.textContent = error.message;
    }
  });
  runRepeated.addEventListener('click', async () => {
    status.textContent = 'Running uncertainty sample…';
    try {
      const data = await requestJson('/api/monte-carlo', {
        scenario: {
          access: {mode: strategy.selectedOptions[0].dataset.access},
          boarding: {strategy: strategy.value},
        },
        runs: Number(runs.value),
        baseSeed: 20260813,
      });
      renderMonteCarlo(data, strategy.selectedOptions[0].textContent);
      status.textContent = 'Uncertainty sample ready';
    } catch (error) {
      status.textContent = error.message;
    }
  });
}
