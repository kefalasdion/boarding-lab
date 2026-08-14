const LEVELS = [
  {maximum: 0.20, color: '#2e8b73', label: 'Calm'},
  {maximum: 0.40, color: '#75a968', label: 'Low'},
  {maximum: 0.60, color: '#d2a646', label: 'Raised'},
  {maximum: 0.75, color: '#d66a48', label: 'Elevated'},
  {maximum: Infinity, color: '#bd315e', label: 'High'},
];

export function frustrationVisual(value, threshold = 0.75) {
  const bounded = Math.min(1, Math.max(0, Number(value) || 0));
  const level = LEVELS.find((candidate) => bounded < candidate.maximum) ?? LEVELS.at(-1);
  return {
    color: level.color,
    label: level.label,
    aboveThreshold: bounded >= threshold,
  };
}
