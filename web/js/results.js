import {frustrationVisual} from './frustration-scale.js';

const LABELS = {
  random_front: 'Random',
  back_to_front_zones: 'Back-to-front',
  strict_steffen: 'Strict Steffen',
};

function clockLabel(value) {
  if (!Number.isFinite(value)) return 'Unavailable';
  const seconds = Math.max(0, Math.round(value));
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}

function decimal(value, suffix = '') {
  return Number.isFinite(value) ? `${value.toFixed(2)}${suffix}` : 'Unavailable';
}

export function conclusionFor(comparison) {
  const order = comparison.strategy_order ?? Object.keys(comparison.strategies ?? {});
  const allValid = order.length > 0 && order.every((id) => comparison.strategies[id]?.status === 'valid');
  const winner = allValid && order.includes(comparison.winner) ? comparison.winner : null;
  if (!winner) {
    return {
      winner: null,
      headline: 'No overall winner can be declared.',
      summary: 'At least one method did not complete. Finished phases remain visible, but missing outcomes are not replaced with zero.',
    };
  }
  return {
    winner,
    headline: `${LABELS[winner] ?? winner} completes the whole journey first.`,
    summary: 'This conclusion includes gate preparation, access and cabin boarding on the shared T=0 clock.',
  };
}

function measureRows() {
  return [
    ['Preparation finished at', (result) => clockLabel(result.metrics.timings_seconds.preparation)],
    ['Boarding started at', (result) => clockLabel(result.phases.part3_embarkation.aircraft.first_entry_time_seconds)],
    ['Boarding finished at', (result) => clockLabel(result.phases.part3_embarkation.aircraft.last_seat_time_seconds)],
    ['Preparation duration', (result) => clockLabel(result.metrics.timings_seconds.preparation)],
    ['Access until last door arrival', (result) => clockLabel(result.metrics.timings_seconds.access_until_last_door_arrival)],
    ['Cabin boarding duration', (result) => clockLabel(result.metrics.timings_seconds.cabin_boarding)],
    ['Total · T=0 to last seat', (result) => clockLabel(result.metrics.timings_seconds.total_t0_to_last_seat)],
    ['Preparation corrections', (result) => String(result.metrics.correction_events)],
    ['Companion separations', (result) => String(result.metrics.companion_overrides)],
    ['Frustration accumulated during preparation', (result) => decimal(result.metrics.passenger_experience.preparation_frustration_burden_f_minutes?.mean, ' F·min')],
    ['Frustration accumulated during embarkation', (result) => decimal(result.metrics.passenger_experience.embarkation_frustration_burden_f_minutes?.mean, ' F·min')],
    ['Total frustration burden', (result) => decimal(result.metrics.passenger_experience.total_frustration_burden_f_minutes?.mean, ' F·min')],
    ['Peak frustration', (result) => decimal(result.metrics.passenger_experience.peak_frustration?.mean)],
    ['Passengers above peak threshold', (result) => decimal(result.metrics.passenger_experience.share_peak_above_threshold * 100, '%')],
  ];
}

function resultCards(comparison, container) {
  container.replaceChildren();
  for (const strategyId of comparison.strategy_order) {
    const result = comparison.strategies[strategyId];
    const card = document.createElement('article');
    card.className = 'result-strategy';
    if (strategyId === comparison.winner && result.status === 'valid') card.classList.add('is-winner');
    const label = document.createElement('span');
    label.textContent = LABELS[strategyId];
    const time = document.createElement('strong');
    time.textContent = clockLabel(result.metrics.timings_seconds.total_t0_to_last_seat);
    const explanation = document.createElement('p');
    explanation.textContent = result.status === 'valid'
      ? `Preparation ${clockLabel(result.metrics.timings_seconds.preparation)} · total model-predicted burden ${decimal(result.metrics.passenger_experience.total_frustration_burden_f_minutes?.mean, ' F·min')}`
      : 'Incomplete · no finishing time inferred';
    card.append(label, time, explanation);
    container.append(card);
  }
}

function timingTable(comparison, table, summary = null) {
  const body = table.tBodies[0];
  body.replaceChildren();
  for (const [label, read] of measureRows()) {
    const row = document.createElement('tr');
    const heading = document.createElement('th');
    heading.scope = 'row';
    heading.textContent = label;
    if (label.includes('Frustration') || label.includes('frustration')) {
      const caveat = document.createElement('small');
      caveat.textContent = 'model-predicted · provisional';
      heading.append(caveat);
    }
    row.append(heading);
    for (const strategyId of comparison.strategy_order) {
      const cell = document.createElement('td');
      cell.textContent = read(comparison.strategies[strategyId]);
      row.append(cell);
    }
    body.append(row);
  }
  const uncertaintyRows = [
    ['P10–P90 total across repeated runs', (strategyId) => {
      const total = summary?.summaries?.[strategyId]?.total_seconds;
      return total ? `${clockLabel(total.p10)}–${clockLabel(total.p90)}` : 'Unavailable';
    }],
    ['95% mean interval', (strategyId) => {
      const total = summary?.summaries?.[strategyId]?.total_seconds;
      return total ? `${clockLabel(total.mean_ci95_low)}–${clockLabel(total.mean_ci95_high)}` : 'Unavailable';
    }],
    ['Valid / timed-out / invalid runs', (strategyId) => {
      const counts = summary?.strategy_run_counts?.[strategyId];
      return counts ? `${counts.valid} / ${counts.timed_out} / ${counts.invalid}` : 'Unavailable';
    }],
  ];
  for (const [label, read] of uncertaintyRows) {
    const row = document.createElement('tr');
    const heading = document.createElement('th');
    heading.scope = 'row';
    heading.textContent = label;
    row.append(heading);
    for (const strategyId of comparison.strategy_order) {
      const cell = document.createElement('td');
      cell.textContent = read(strategyId);
      row.append(cell);
    }
    body.append(row);
  }
}

function drawHeatmap(comparison, strategyId, metric) {
  const result = comparison.strategies[strategyId];
  const canvas = document.getElementById('heatmap');
  const context = canvas.getContext('2d');
  const pixelRatio = Math.min(2, window.devicePixelRatio || 1);
  const width = canvas.clientWidth || 980;
  const height = Math.max(230, width * .32);
  canvas.width = Math.round(width * pixelRatio);
  canvas.height = Math.round(height * pixelRatio);
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  context.fillStyle = '#fbfaf6';
  context.fillRect(0, 0, width, height);
  const bySeat = new Map(result.passengers.map((passenger) => [`${passenger.row}${passenger.seat}`, passenger]));
  const burdens = result.passengers.map((passenger) => passenger.frustration_burden);
  const maximumBurden = Math.max(...burdens, 1);
  const left = 50;
  const top = 34;
  const cellWidth = (width - left - 18) / 30;
  const cellHeight = (height - top - 26) / 6;
  context.font = '10px Inter, sans-serif';
  context.textAlign = 'center';
  for (let row = 1; row <= 30; row += 1) {
    context.fillStyle = '#657184';
    context.fillText(String(row), left + (row - .5) * cellWidth, 18);
    for (let seatIndex = 0; seatIndex < 6; seatIndex += 1) {
      const seat = 'ABCDEF'[seatIndex];
      const passenger = bySeat.get(`${row}${seat}`);
      const value = passenger
        ? (metric === 'burden' ? passenger.frustration_burden / maximumBurden : passenger.peak_frustration)
        : 0;
      context.fillStyle = passenger ? frustrationVisual(value).color : '#e3e0d8';
      const x = left + (row - 1) * cellWidth + 1;
      const y = top + seatIndex * cellHeight + 1;
      context.fillRect(x, y, Math.max(2, cellWidth - 2), Math.max(2, cellHeight - 2));
      if (row === 1) {
        context.fillStyle = '#657184';
        context.textAlign = 'right';
        context.fillText(seat, left - 9, y + cellHeight * .62);
        context.textAlign = 'center';
      }
    }
  }

  const fallback = document.getElementById('heatmap-table');
  const table = document.createElement('table');
  const caption = document.createElement('caption');
  caption.textContent = `${LABELS[strategyId]} passenger ${metric} values by seat`;
  table.append(caption);
  const body = document.createElement('tbody');
  for (const passenger of result.passengers) {
    const row = document.createElement('tr');
    for (const value of [`${passenger.row}${passenger.seat}`, metric === 'burden' ? passenger.frustration_burden : passenger.peak_frustration]) {
      const cell = document.createElement('td');
      cell.textContent = String(value);
      row.append(cell);
    }
    body.append(row);
  }
  table.append(body);
  fallback.replaceChildren(table);
}

export function renderResults(comparison, summary = null) {
  const conclusion = conclusionFor(comparison);
  document.getElementById('result-headline').textContent = conclusion.headline;
  document.getElementById('result-summary').textContent = conclusion.summary;
  resultCards(comparison, document.getElementById('result-comparison'));
  timingTable(comparison, document.getElementById('timing-table'), summary);
  const strategySelect = document.getElementById('heatmap-strategy');
  strategySelect.replaceChildren(...comparison.strategy_order.map((strategyId) => {
    const option = document.createElement('option');
    option.value = strategyId;
    option.textContent = LABELS[strategyId];
    return option;
  }));
  if (conclusion.winner) strategySelect.value = conclusion.winner;
  const redraw = () => drawHeatmap(comparison, strategySelect.value, document.getElementById('heatmap-metric').value);
  strategySelect.onchange = redraw;
  document.getElementById('heatmap-metric').onchange = redraw;
  redraw();
  return conclusion;
}
