const PARAMETER_MAP = [
  ['seed', 'seed'],
  ['delayMinutes', 'delay'],
  ['priorGateWaitMinutes', 'gateWait'],
  ['familyShare', 'family'],
  ['bags', 'bags'],
];

export function resultUrl(base, values) {
  const url = new URL(base);
  url.search = '';
  for (const [property, parameter] of PARAMETER_MAP) {
    const value = values[property];
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(parameter, String(value));
  }
  return url.toString();
}

export function summaryText({winnerLabel, totalTime, seed}) {
  const conclusion = winnerLabel
    ? `${winnerLabel} completed the full gate-to-seat journey first in ${totalTime}.`
    : 'No overall winner was declared because at least one strategy did not complete.';
  return `Boarding Lab — ${conclusion} Seed ${seed}. Passenger frustration is model-predicted and provisional.`;
}

export function drawShareImage(canvas, comparison) {
  canvas.width = 1200;
  canvas.height = 627;
  const context = canvas.getContext('2d');
  context.fillStyle = '#f2efe8';
  context.fillRect(0, 0, 1200, 627);
  context.fillStyle = '#10233f';
  context.fillRect(0, 0, 1200, 78);
  context.font = '700 22px Inter, sans-serif';
  context.fillStyle = '#ffffff';
  context.fillText('BOARDING LAB', 58, 49);
  context.font = '16px Inter, sans-serif';
  context.fillStyle = '#c8d2df';
  context.fillText('By Dennis Kefalas', 940, 49);
  context.font = '48px Georgia, serif';
  context.fillStyle = '#10233f';
  context.fillText('From preparation to the last seat', 58, 154);
  const totals = comparison.strategy_order.map((id) => comparison.strategies[id].metrics.timings_seconds.total_t0_to_last_seat ?? 0);
  const maximum = Math.max(...totals, 1);
  comparison.strategy_order.forEach((strategyId, index) => {
    const result = comparison.strategies[strategyId];
    const y = 220 + index * 92;
    const total = result.metrics.timings_seconds.total_t0_to_last_seat;
    context.font = '700 18px Inter, sans-serif';
    context.fillStyle = '#10233f';
    context.fillText(result.strategy.name.split(' · ')[0], 58, y);
    context.fillStyle = '#176fd1';
    context.fillRect(300, y - 22, Number.isFinite(total) ? 650 * total / maximum : 4, 30);
    context.font = '700 18px ui-monospace, monospace';
    context.fillStyle = '#10233f';
    context.fillText(Number.isFinite(total) ? `${Math.floor(total / 60)}:${String(Math.round(total) % 60).padStart(2, '0')}` : 'Incomplete', 980, y);
  });
  context.font = '17px Inter, sans-serif';
  context.fillStyle = '#43536a';
  context.fillText('The comparison includes the time needed to form each boarding order.', 58, 530);
  context.font = '14px Inter, sans-serif';
  context.fillText(`Seed ${comparison.seed} · ${comparison.model_version} · frustration is model-predicted and provisional`, 58, 574);
}

export function downloadShareImage(canvas, comparison) {
  drawShareImage(canvas, comparison);
  canvas.toBlob((blob) => {
    if (!blob) return;
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `boarding-lab-seed-${comparison.seed}.png`;
    link.click();
    URL.revokeObjectURL(link.href);
  }, 'image/png');
}
