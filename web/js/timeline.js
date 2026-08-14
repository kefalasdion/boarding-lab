function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

export function createTimeline({duration, speed = 1, reducedMotion = false, eventTimes = []}) {
  if (!Number.isFinite(duration) || duration < 0) throw new TypeError('duration must be a non-negative number');
  let current = 0;
  let rate = speed;
  let isPlaying = false;
  const events = [...new Set([0, ...eventTimes, duration]
    .filter(Number.isFinite)
    .map((time) => clamp(time, 0, duration)))]
    .sort((a, b) => a - b);

  const snapForward = (value) => events.find((time) => time >= value) ?? duration;

  return {
    play() {
      if (current >= duration) current = 0;
      isPlaying = duration > 0;
    },
    pause() { isPlaying = false; },
    seek(time) {
      const target = clamp(Number(time) || 0, 0, duration);
      current = reducedMotion ? snapForward(target) : target;
      if (current >= duration) isPlaying = false;
      return current;
    },
    setSpeed(nextSpeed) {
      const value = Number(nextSpeed);
      if (!Number.isFinite(value) || value <= 0) throw new TypeError('speed must be positive');
      rate = value;
    },
    advance(deltaSeconds) {
      if (!isPlaying) return current;
      if (reducedMotion) {
        current = events.find((time) => time > current) ?? duration;
        isPlaying = false;
        return current;
      }
      current = clamp(current + Math.max(0, Number(deltaSeconds) || 0) * rate, 0, duration);
      if (current >= duration) isPlaying = false;
      return current;
    },
    time: () => current,
    playing: () => isPlaying,
    speed: () => rate,
    duration: () => duration,
  };
}
