import {frustrationVisual} from './frustration-scale.js';

const LANE_COUNT = 3;

function framePair(frames, time) {
  if (!frames.length) return [null, null, 0];
  let low = 0;
  let high = frames.length - 1;
  while (low < high) {
    const middle = Math.ceil((low + high) / 2);
    if (frames[middle][0] <= time) low = middle;
    else high = middle - 1;
  }
  const first = frames[low];
  const second = frames[Math.min(low + 1, frames.length - 1)];
  const span = second[0] - first[0];
  return [first, second, span > 0 ? Math.min(1, Math.max(0, (time - first[0]) / span)) : 0];
}

function mix(first, second, amount) {
  return first + (second - first) * amount;
}

function passengerState(frame, passengerId) {
  if (!frame) return null;
  const likely = frame[3][passengerId];
  if (likely?.[0] === passengerId) return likely;
  return frame[3].find((state) => state[0] === passengerId) ?? null;
}

function prepareLane(result) {
  const replay = result.replay;
  const eventsByPassenger = new Map();
  for (const event of replay.aircraft_events) {
    const passengerId = event[2];
    if (!eventsByPassenger.has(passengerId)) eventsByPassenger.set(passengerId, []);
    eventsByPassenger.get(passengerId).push(event);
  }
  const slots = new Map(replay.gate.slots.map((slot) => [slot[0], slot]));
  return {
    result,
    replay,
    ids: Object.keys(replay.passenger_tracks).map(Number).sort((a, b) => a - b),
    eventsByPassenger,
    slots,
    preparationEnd: result.metrics.timings_seconds.preparation,
    entryCode: replay.event_codebook.aircraft_entered,
    moveCode: replay.event_codebook.aisle_moved,
    seatedCode: replay.event_codebook.seated,
    threshold: result.metrics.passenger_experience.threshold,
  };
}

export function createRaceCanvas(canvas, {onSelect = () => {}} = {}) {
  const context = canvas.getContext('2d', {alpha: false});
  let lanes = [];
  let width = 1;
  let height = 1;
  let count = 0;
  let selectedIndex = -1;
  let latestTime = 0;
  let positions = new Float32Array(0);
  let passengerRefs = [];

  function resize() {
    const rectangle = canvas.getBoundingClientRect();
    const pixelRatio = Math.min(2, window.devicePixelRatio || 1);
    width = Math.max(1, rectangle.width);
    height = Math.max(1, rectangle.height);
    const pixelWidth = Math.round(width * pixelRatio);
    const pixelHeight = Math.round(height * pixelRatio);
    if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
      canvas.width = pixelWidth;
      canvas.height = pixelHeight;
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    }
  }

  function gatePoint(lane, passengerId, time, laneTop, laneHeight) {
    const [first, second, amount] = framePair(lane.replay.gate.frames, time);
    const firstState = passengerState(first, passengerId);
    const secondState = passengerState(second, passengerId) ?? firstState;
    const layout = lane.replay.gate.layout;
    const xMetres = mix(firstState?.[1] ?? 0, secondState?.[1] ?? 0, amount);
    const yMetres = mix(firstState?.[2] ?? 0, secondState?.[2] ?? 0, amount);
    return [
      width * .13 + (xMetres / layout.width_m) * width * .29,
      laneTop + laneHeight * .13 + (yMetres / layout.height_m) * laneHeight * .74,
    ];
  }

  function aircraftPoint(lane, passengerId, time, start, laneTop, laneHeight) {
    const events = lane.eventsByPassenger.get(passengerId) ?? [];
    const entered = events.find((event) => event[1] === lane.entryCode);
    const seated = events.find((event) => event[1] === lane.seatedCode);
    if (!entered || time < entered[0]) {
      const endTime = entered?.[0] ?? lane.result.replay.ends_at_seconds;
      const progress = Math.min(1, Math.max(0, (time - lane.preparationEnd) / Math.max(1, endTime - lane.preparationEnd)));
      return [
        mix(start[0], width * .635, progress),
        mix(start[1], laneTop + laneHeight * .5, progress),
      ];
    }

    const track = lane.replay.passenger_tracks[String(passengerId)];
    if (seated && time >= seated[0]) {
      const seatOrder = 'ABCDEF'.indexOf(track[1]);
      const seatOffset = [-.26, -.17, -.09, .09, .17, .26][seatOrder] ?? 0;
      return [
        width * (.675 + (track[0] - 1) / 29 * .285),
        laneTop + laneHeight * (.5 + seatOffset),
      ];
    }

    let aisleCell = 0;
    for (const event of events) {
      if (event[0] > time) break;
      if (event[1] === lane.moveCode) aisleCell = event[5];
    }
    return [
      width * (.66 + Math.min(1, aisleCell / 60) * .30),
      laneTop + laneHeight * .5,
    ];
  }

  function frustrationAt(lane, passengerId, time) {
    const [first, second, amount] = framePair(lane.replay.frustration_frames, time);
    const firstState = passengerState(first, passengerId);
    const secondState = passengerState(second, passengerId) ?? firstState;
    return mix(firstState?.[1] ?? 0, secondState?.[1] ?? 0, amount);
  }

  function drawAircraft(laneTop, laneHeight) {
    const x = width * .65;
    const y = laneTop + laneHeight * .22;
    const aircraftWidth = width * .33;
    const aircraftHeight = laneHeight * .56;
    context.save();
    context.strokeStyle = '#536984';
    context.fillStyle = '#182f4c';
    context.lineWidth = 1;
    context.beginPath();
    context.roundRect(x, y, aircraftWidth, aircraftHeight, aircraftHeight / 2);
    context.fill();
    context.stroke();
    context.strokeStyle = '#405672';
    context.beginPath();
    context.moveTo(x + 12, laneTop + laneHeight * .5);
    context.lineTo(x + aircraftWidth - 12, laneTop + laneHeight * .5);
    context.stroke();
    context.restore();
  }

  function drawGateSlots(lane, laneTop, laneHeight) {
    const layout = lane.replay.gate.layout;
    context.fillStyle = '#314965';
    for (const slot of lane.replay.gate.slots) {
      const x = width * .13 + (slot[3] / layout.width_m) * width * .29;
      const y = laneTop + laneHeight * .13 + (slot[4] / layout.height_m) * laneHeight * .74;
      context.fillRect(x - .7, y - .7, 1.4, 1.4);
    }
  }

  function draw(time) {
    latestTime = time;
    resize();
    context.fillStyle = '#142a47';
    context.fillRect(0, 0, width, height);
    if (!lanes.length) return;
    const laneHeight = height / LANE_COUNT;
    let positionIndex = 0;

    for (let laneIndex = 0; laneIndex < lanes.length; laneIndex += 1) {
      const lane = lanes[laneIndex];
      const laneTop = laneIndex * laneHeight;
      if (laneIndex > 0) {
        context.strokeStyle = '#40536e';
        context.beginPath();
        context.moveTo(0, laneTop);
        context.lineTo(width, laneTop);
        context.stroke();
      }
      drawAircraft(laneTop, laneHeight);
      drawGateSlots(lane, laneTop, laneHeight);
      context.strokeStyle = '#40536e';
      context.setLineDash([4, 6]);
      context.beginPath();
      context.moveTo(width * .44, laneTop + laneHeight * .5);
      context.lineTo(width * .64, laneTop + laneHeight * .5);
      context.stroke();
      context.setLineDash([]);

      for (const passengerId of lane.ids) {
        const gate = gatePoint(lane, passengerId, Math.min(time, lane.preparationEnd), laneTop, laneHeight);
        const point = time <= lane.preparationEnd
          ? gate
          : aircraftPoint(lane, passengerId, time, gate, laneTop, laneHeight);
        const frustration = frustrationAt(lane, passengerId, time);
        const visual = frustrationVisual(frustration, lane.threshold);
        positions[positionIndex * 2] = point[0];
        positions[positionIndex * 2 + 1] = point[1];
        context.beginPath();
        context.fillStyle = visual.color;
        context.arc(point[0], point[1], positionIndex === selectedIndex ? 4.5 : 3.1, 0, Math.PI * 2);
        context.fill();
        if (visual.aboveThreshold || positionIndex === selectedIndex) {
          context.strokeStyle = positionIndex === selectedIndex ? '#ffffff' : '#ffd5df';
          context.lineWidth = positionIndex === selectedIndex ? 2 : 1;
          context.stroke();
        }
        positionIndex += 1;
      }
    }
  }

  function setComparison(comparison) {
    lanes = comparison.strategy_order.map((strategyId) => prepareLane(comparison.strategies[strategyId]));
    passengerRefs = lanes.flatMap((lane, laneIndex) => lane.ids.map((passengerId) => ({laneIndex, passengerId})));
    count = passengerRefs.length;
    positions = new Float32Array(count * 2);
    selectedIndex = -1;
    draw(0);
  }

  function selectAt(clientX, clientY) {
    const rectangle = canvas.getBoundingClientRect();
    const x = clientX - rectangle.left;
    const y = clientY - rectangle.top;
    let closest = -1;
    let closestDistance = 12 * 12;
    for (let index = 0; index < count; index += 1) {
      const dx = positions[index * 2] - x;
      const dy = positions[index * 2 + 1] - y;
      const distance = dx * dx + dy * dy;
      if (distance <= closestDistance) {
        closest = index;
        closestDistance = distance;
      }
    }
    if (closest >= 0) {
      selectedIndex = closest;
      draw(latestTime);
      onSelect(passengerRefs[closest]);
    }
  }

  const clickHandler = (event) => selectAt(event.clientX, event.clientY);
  canvas.addEventListener('click', clickHandler);
  const observer = new ResizeObserver(() => draw(latestTime));
  observer.observe(canvas);

  return {
    setComparison,
    draw,
    destroy() {
      observer.disconnect();
      canvas.removeEventListener('click', clickHandler);
    },
  };
}
