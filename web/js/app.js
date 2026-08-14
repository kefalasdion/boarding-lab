import {requestJson} from './api.js';
import {initializeExpert} from './expert.js';
import {frustrationVisual} from './frustration-scale.js';
import {phaseBurden} from './phase-burden.js';
import {createRaceCanvas} from './race-canvas.js';
import {renderResults} from './results.js';
import {downloadShareImage, resultUrl, summaryText} from './share.js';
import {createTimeline} from './timeline.js';

const STRATEGY_LABELS = {
  random_front: 'Random',
  back_to_front_zones: 'Back-to-front',
  strict_steffen: 'Strict Steffen',
};
const ROW_IDS = {
  random_front: 'lane-random-live',
  back_to_front_zones: 'lane-back-to-front-live',
  strict_steffen: 'lane-strict-steffen-live',
};

const byId = (id) => document.getElementById(id);

function applyCaptureMode() {
  const parameters = new URLSearchParams(window.location.search);
  if (parameters.get('capture') !== '1') return {active: false, autoplay: false, speed: null};
  document.body.classList.add('capture');
  document.body.dataset.captureStage = 'race';
  const speed = Number(parameters.get('speed'));
  return {
    active: true,
    autoplay: parameters.get('autoplay') === '1',
    speed: Number.isFinite(speed) && speed > 0 ? speed : null,
  };
}

const captureSettings = applyCaptureMode();
const reducedMotion = captureSettings.active
  ? false
  : window.matchMedia('(prefers-reduced-motion: reduce)').matches;
let comparison = null;
let timeline = null;
let renderer = null;
let animationFrame = 0;
let previousTimestamp = 0;
let selectedPassenger = null;

function clockLabel(value) {
  if (!Number.isFinite(value)) return 'Unavailable';
  const seconds = Math.max(0, Math.round(value));
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}

function numberLabel(value, digits = 2) {
  return Number.isFinite(value) ? value.toFixed(digits) : 'Unavailable';
}

function latestAt(items, time, timeKey = 'time_seconds') {
  let selected = items?.[0] ?? null;
  for (const item of items ?? []) {
    const itemTime = Array.isArray(item) ? item[0] : item[timeKey];
    if (itemTime > time) break;
    selected = item;
  }
  return selected;
}

function passengerState(frame, passengerId) {
  if (!frame) return null;
  const likely = frame[3][passengerId];
  if (likely?.[0] === passengerId) return likely;
  return frame[3].find((state) => state[0] === passengerId) ?? null;
}

function liveFrameAt(result, time) {
  if (time <= result.metrics.timings_seconds.preparation) {
    return latestAt(result.replay.gate.frames, time);
  }
  return latestAt(result.replay.frustration_frames, time);
}

function livePassengerValues(result, frame, passengerId, time) {
  const state = passengerState(frame, passengerId);
  if (!state) return {frustration: 0, burden: 0};
  const gatePhase = time <= result.metrics.timings_seconds.preparation;
  return {
    frustration: state[gatePhase ? 3 : 1],
    burden: state[gatePhase ? 4 : 2],
  };
}

function scenarioPayload() {
  return {
    flightContext: {
      delayMinutes: Number(byId('delay-minutes').value),
      priorGateWaitMinutes: Number(byId('prior-gate-wait').value),
    },
    population: {
      familyPassengerShare: Number(byId('family-share').value) / 100,
      handLuggageShare: Number(byId('bag-share').value) / 100,
    },
  };
}

function eventTimesFor(data) {
  const values = [0];
  for (const strategyId of data.strategy_order) {
    const result = data.strategies[strategyId];
    values.push(
      result.metrics.timings_seconds.preparation,
      result.phases.part3_embarkation.aircraft.first_entry_time_seconds,
      result.phases.part3_embarkation.aircraft.last_seat_time_seconds,
      ...result.replay.frustration_frames.map((frame) => frame[0]),
    );
  }
  return values.filter(Number.isFinite);
}

function phaseAndCounts(result, time) {
  const preparationEnd = result.metrics.timings_seconds.preparation;
  const aircraft = result.phases.part3_embarkation.aircraft;
  const preparationSample = latestAt(result.phases.part2_preparation.progress, time);
  const aircraftSample = latestAt(aircraft.progress, time);
  const passengerCount = result.metrics.passenger_count;
  if (time < preparationEnd) {
    return {
      phase: 'Preparing at gate',
      prepared: preparationSample?.prepared_count ?? 0,
      entered: 0,
      seated: 0,
    };
  }
  if (time < (aircraft.first_entry_time_seconds ?? Infinity)) {
    return {phase: 'Moving to aircraft', prepared: passengerCount, entered: 0, seated: 0};
  }
  if (time < (aircraft.last_seat_time_seconds ?? Infinity)) {
    return {
      phase: 'Boarding aircraft',
      prepared: passengerCount,
      entered: aircraftSample?.entered_count ?? 0,
      seated: aircraftSample?.seated_count ?? 0,
    };
  }
  return {phase: result.status === 'valid' ? 'Complete' : 'Timed out', prepared: passengerCount, entered: aircraftSample?.entered_count ?? 0, seated: result.metrics.seated_count};
}

function updateLiveRow(strategyId, result, time) {
  const row = byId(ROW_IDS[strategyId]);
  const cells = row.children;
  const counts = phaseAndCounts(result, time);
  const frame = liveFrameAt(result, time);
  const experience = result.metrics.passenger_experience;
  cells[1].textContent = counts.phase;
  cells[2].textContent = `${counts.prepared}/${result.metrics.passenger_count}`;
  cells[3].textContent = `${counts.entered}/${result.metrics.passenger_count}`;
  cells[4].textContent = `${counts.seated}/${result.metrics.passenger_count}`;
  cells[5].textContent = frame ? `${Math.round(frame[1] * 100)}/100 · ${numberLabel(frame[2])} F·min` : 'Unavailable';
  cells[6].textContent = clockLabel(result.metrics.timings_seconds.preparation);
  cells[7].textContent = clockLabel(result.phases.part3_embarkation.aircraft.first_entry_time_seconds);
  cells[8].textContent = clockLabel(result.phases.part3_embarkation.aircraft.last_seat_time_seconds);
  cells[9].textContent = `${numberLabel(experience.preparation_frustration_burden_f_minutes?.mean)} F·min`;
  cells[10].textContent = `${numberLabel(experience.embarkation_frustration_burden_f_minutes?.mean)} F·min`;
  cells[11].textContent = `${numberLabel(experience.total_frustration_burden_f_minutes?.mean)} F·min`;
}

function updateInspector(time) {
  if (!selectedPassenger || !comparison) return;
  const strategyId = comparison.strategy_order[selectedPassenger.laneIndex];
  const result = comparison.strategies[strategyId];
  const passenger = result.passengers.find((item) => item.id === selectedPassenger.passengerId);
  const frame = liveFrameAt(result, time);
  const values = livePassengerValues(result, frame, selectedPassenger.passengerId, time);
  const visual = frustrationVisual(values.frustration, result.metrics.passenger_experience.threshold);
  const inspector = byId('passenger-inspector');
  inspector.replaceChildren();
  const index = document.createElement('span');
  index.className = 'inspector-index';
  index.textContent = `${STRATEGY_LABELS[strategyId]} · Passenger ${passenger.id + 1}`;
  const title = document.createElement('strong');
  title.textContent = `Seat ${passenger.row}${passenger.seat}${passenger.family_id ? ` · group ${passenger.family_id}` : ''}`;
  const detail = document.createElement('p');
  detail.textContent = `${phaseAndCounts(result, time).phase} · ${visual.label} ${Math.round(values.frustration * 100)}/100 · ${numberLabel(values.burden)} accumulated F·min`;
  inspector.append(index, title, detail);
}

function burdenLabel(value) {
  return Number.isFinite(value) ? value.toFixed(2) : '—';
}

function updateLaneBurden(strategyId, result, time) {
  const preparation = byId(`lane-preparation-${strategyId}`);
  const boarding = byId(`lane-boarding-${strategyId}`);
  if (!preparation || !boarding) return;
  const frame = liveFrameAt(result, time);
  const split = phaseBurden({
    time,
    runningBurden: frame ? frame[2] : null,
    preparationEndsAt: result.metrics.timings_seconds.preparation,
    preparationCheckpoint:
      result.metrics.passenger_experience.preparation_frustration_burden_f_minutes?.mean,
  });
  preparation.textContent = burdenLabel(split.preparation);
  boarding.textContent = burdenLabel(split.boarding);
}

function renderAt(time) {
  byId('master-clock').textContent = clockLabel(time);
  byId('timeline-scrubber').value = String(Math.round(time));
  renderer?.draw(time);
  if (comparison) {
    for (const strategyId of comparison.strategy_order) {
      updateLiveRow(strategyId, comparison.strategies[strategyId], time);
      updateLaneBurden(strategyId, comparison.strategies[strategyId], time);
    }
  }
  updateInspector(time);
  const playing = timeline?.playing() ?? false;
  byId('play-toggle').setAttribute('aria-pressed', String(playing));
  byId('play-toggle').lastChild.textContent = playing ? ' Pause' : ' Play';
}

function tick(timestamp) {
  if (!timeline?.playing()) return;
  if (!previousTimestamp) previousTimestamp = timestamp;
  timeline.advance((timestamp - previousTimestamp) / 1000);
  previousTimestamp = timestamp;
  renderAt(timeline.time());
  if (timeline.playing()) animationFrame = requestAnimationFrame(tick);
}

function beginAnimation() {
  cancelAnimationFrame(animationFrame);
  previousTimestamp = 0;
  if (reducedMotion) {
    timeline.advance(0);
    renderAt(timeline.time());
    return;
  }
  animationFrame = requestAnimationFrame(tick);
}

function installComparison(data, summary = null) {
  comparison = data;
  byId('seed').value = String(data.seed);
  const duration = Math.max(...data.strategy_order.map((id) => data.strategies[id].replay.ends_at_seconds));
  timeline = createTimeline({duration, reducedMotion, eventTimes: eventTimesFor(data)});
  byId('timeline-scrubber').max = String(Math.ceil(duration));
  renderer ??= createRaceCanvas(byId('race-canvas'), {
    onSelect(selection) {
      selectedPassenger = selection;
      updateInspector(timeline.time());
    },
  });
  renderer.setComparison(data);
  renderResults(data, summary);
  byId('race-status').textContent = 'Ready · same passengers and one continuous clock';
  byId('model-version').textContent = data.model_version;
  renderAt(0);
  if (captureSettings.speed) {
    timeline.setSpeed(captureSettings.speed);
    byId('playback-speed').value = String(captureSettings.speed);
  }
  if (captureSettings.autoplay) {
    timeline.play();
    beginAnimation();
  }
}

function shareValues() {
  return {
    seed: Number(byId('seed').value),
    delayMinutes: Number(byId('delay-minutes').value),
    priorGateWaitMinutes: Number(byId('prior-gate-wait').value),
    familyShare: Number(byId('family-share').value),
    bags: Number(byId('bag-share').value),
  };
}

function applyQueryInputs() {
  const parameters = new URLSearchParams(window.location.search);
  const assignments = [
    ['seed', 'seed'],
    ['delay', 'delay-minutes'],
    ['gateWait', 'prior-gate-wait'],
    ['family', 'family-share'],
    ['bags', 'bag-share'],
  ];
  for (const [parameter, elementId] of assignments) {
    const value = parameters.get(parameter);
    if (value !== null && Number.isFinite(Number(value))) byId(elementId).value = value;
  }
}

async function loadComparison(scenario = {}, seed = 20260813) {
  byId('race-status').textContent = 'Running three fair, deterministic simulations…';
  byId('run-comparison').disabled = true;
  try {
    installComparison(await requestJson('/api/compare', {scenario, seed}));
  } catch (error) {
    byId('race-status').textContent = error.message;
  } finally {
    byId('run-comparison').disabled = false;
  }
}

async function loadDefaultComparison() {
  byId('race-status').textContent = 'Loading the representative 100-run comparison…';
  try {
    const artifact = await requestJson('/data/default-comparison.json');
    installComparison(artifact.representative, artifact.summary);
  } catch {
    await loadComparison(scenarioPayload(), Number(byId('seed').value));
  }
}

byId('play-toggle').addEventListener('click', () => {
  if (!timeline) return;
  if (timeline.playing()) {
    timeline.pause();
    cancelAnimationFrame(animationFrame);
    renderAt(timeline.time());
  } else {
    timeline.play();
    beginAnimation();
  }
});
byId('replay-button').addEventListener('click', () => {
  if (!timeline) return;
  timeline.pause();
  timeline.seek(0);
  renderAt(0);
});
byId('timeline-scrubber').addEventListener('input', (event) => {
  if (!timeline) return;
  timeline.pause();
  renderAt(timeline.seek(Number(event.target.value)));
});
byId('playback-speed').addEventListener('change', (event) => timeline?.setSpeed(Number(event.target.value)));
byId('scenario-form').addEventListener('submit', (event) => {
  event.preventDefault();
  loadComparison(scenarioPayload(), Number(byId('seed').value));
});
for (const [inputId, outputId, suffix] of [
  ['delay-minutes', 'delay-output', ' min'],
  ['prior-gate-wait', 'gate-wait-output', ' min'],
  ['family-share', 'family-output', '%'],
  ['bag-share', 'bag-output', '%'],
]) {
  byId(inputId).addEventListener('input', (event) => { byId(outputId).textContent = `${event.target.value}${suffix}`; });
}
document.addEventListener('visibilitychange', () => {
  if (document.hidden && timeline?.playing()) {
    timeline.pause();
    cancelAnimationFrame(animationFrame);
    renderAt(timeline.time());
  }
});

byId('copy-summary').addEventListener('click', async () => {
  if (!comparison) return;
  const winner = comparison.winner;
  const winnerResult = winner ? comparison.strategies[winner] : null;
  const text = summaryText({
    winnerLabel: winner ? STRATEGY_LABELS[winner] : null,
    totalTime: winnerResult ? clockLabel(winnerResult.metrics.timings_seconds.total_t0_to_last_seat) : null,
    seed: comparison.seed,
  });
  await navigator.clipboard.writeText(`${text}\n${resultUrl(window.location.href, shareValues())}`);
  byId('share-status').textContent = 'Summary copied';
});
byId('download-image').addEventListener('click', () => {
  if (!comparison) return;
  downloadShareImage(byId('share-canvas'), comparison);
  byId('share-status').textContent = 'Image downloaded';
});

applyQueryInputs();
for (const [inputId, outputId, suffix] of [
  ['delay-minutes', 'delay-output', ' min'],
  ['prior-gate-wait', 'gate-wait-output', ' min'],
  ['family-share', 'family-output', '%'],
  ['bag-share', 'bag-output', '%'],
]) byId(outputId).textContent = `${byId(inputId).value}${suffix}`;

requestJson('/api/config').then(initializeExpert).catch((error) => {
  byId('expert-controls').textContent = error.message;
});
loadDefaultComparison();
