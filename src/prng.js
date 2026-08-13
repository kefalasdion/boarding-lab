export class RNG {
  constructor(seed = 1) { this.state = seed >>> 0 || 1; this._spare = null; }
  next() {
    let t = this.state += 0x6D2B79F5;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  normal(mean = 0, sd = 1) {
    if (this._spare !== null) { const z = this._spare; this._spare = null; return mean + sd * z; }
    const u = Math.max(1e-12, this.next());
    const v = Math.max(1e-12, this.next());
    const mag = Math.sqrt(-2 * Math.log(u));
    const z0 = mag * Math.cos(2 * Math.PI * v);
    this._spare = mag * Math.sin(2 * Math.PI * v);
    return mean + sd * z0;
  }
  exponential(mean) { return -Math.log(Math.max(1e-12, 1 - this.next())) * mean; }
  weibull(shape, scale) { return scale * Math.pow(-Math.log(Math.max(1e-12, 1 - this.next())), 1 / shape); }
  triangular(min, mode, max) {
    const u = this.next(); const c = (mode - min) / (max - min);
    return u < c ? min + Math.sqrt(u * (max - min) * (mode - min)) : max - Math.sqrt((1 - u) * (max - min) * (max - mode));
  }
  int(min, maxInclusive) { return min + Math.floor(this.next() * (maxInclusive - min + 1)); }
  bool(p = 0.5) { return this.next() < p; }
  shuffle(array) {
    for (let i = array.length - 1; i > 0; i--) {
      const j = Math.floor(this.next() * (i + 1));
      [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
  }
  fork(offset) { return new RNG((this.state + 0x9E3779B9 + offset) >>> 0); }
}
