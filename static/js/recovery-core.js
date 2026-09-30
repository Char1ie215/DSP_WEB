'use strict';

(() => {
  const data = window.DSP_RECOVERY_DATA;
  const add = (a, b) => [a[0] + b[0], a[1] + b[1]];
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1]];
  const mul = (a, k) => [a[0] * k, a[1] * k];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1];
  const norm = a => Math.hypot(...a);
  const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
  const mat = (A, x) => [dot(A[0], x), dot(A[1], x)];

  // Paper Eq. (9), with a fixed positive-definite metric during recovery.
  function projectCLF(offset, value, precision, radius) {
    const gradient = mat(precision, offset);
    const distance = Math.sqrt(Math.max(dot(offset, gradient), 0));
    const squaredGradient = dot(gradient, gradient);
    if (distance <= radius || squaredGradient <= 1e-12) return value;
    const required = data.contraction * distance * (distance - radius);
    const violation = dot(gradient, value) + required;
    return violation > 0 ? sub(value, mul(gradient, violation / squaredGradient)) : value;
  }

  // Planar restriction of the research executor's Gaussian affine mixture.
  function field(preset, phase, point) {
    const entry = preset.fields[phase];
    const offset = sub(point, preset.path[phase]);
    if (!entry.mixture) return mul(offset, -entry.gain);
    const {centers, precisions, velocities, matrices} = entry.mixture;
    const offsets = centers.map(c => sub(point, c));
    const logs = offsets.map((o, i) => -.5 * dot(o, mat(precisions[i], o)));
    const top = Math.max(...logs);
    const weights = logs.map(v => Math.exp(Math.max(v - top, -80)));
    const total = weights.reduce((a, b) => a + b, 0);
    let value = [0, 0];
    weights.forEach((w, i) => {
      value = add(value, mul(add(velocities[i], mat(matrices[i], offsets[i])), w / total));
    });
    return projectCLF(offset, value, entry.clfPrecision, entry.clfRadius);
  }

  function innovation(actual, expected) {
    const squared = dot(expected, expected);
    const progress = squared <= 1e-12 ? 0 : clamp(dot(actual, expected) / squared, 0, data.lambdaMax);
    return norm(sub(actual, mul(expected, progress)));
  }

  // Only the current command segment is eligible, never the whole future path.
  function supportRatio(preset, phase, point) {
    const end = Math.min(phase + 1, preset.path.length - 1);
    const a = preset.path[phase], delta = sub(preset.path[end], a);
    const u = clamp(dot(sub(point, a), delta) / Math.max(dot(delta, delta), 1e-12), 0, 1);
    const radius = preset.radii[phase] * (1-u) + preset.radii[end] * u;
    return norm(sub(point, add(a, mul(delta, u)))) / radius;
  }

  class Demo {
    constructor() { this.reset(); }
    reset() {
      this.presetIndex = 0; this.query = 1; this.phase = 0; this.fraction = 0;
      this.shift = [0, 0]; this.position = [...this.preset.path[0]];
      this.state = 'predicting'; this.timer = 0; this.paused = false; this.dragging = false;
      this.anchor = null; this.lockedPhase = null; this.anchorOffset = null;
      this.expected = [0, 0]; this.lastNativePosition = [...this.position];
      this.acceptedPosition = [...this.position]; this.acceptedPhase = this.phase;
      this.trail = []; this.stable = 0; this.recoveryTime = 0; this.lastError = null;
    }
    get preset() { return data.presets[this.presetIndex]; }
    get maxPhase() { return this.preset.path.length - 1; }
    world(p) { return add(p, this.shift); }
    beginDrag() {
      if (!['executing', 'complete', 'recovering'].includes(this.state)) return false;
      this.dragging = true;
      return true;
    }
    drag(point) {
      if (!this.dragging) return;
      this.position = [...point];
      this.observePosition();
    }
    observePosition() {
      if (!['executing', 'complete'].includes(this.state) || !this.preset.reliable) return;
      const inside = supportRatio(this.preset, this.phase, sub(this.position, this.shift)) <= 1;
      if (inside) {
        this.acceptedPosition = [...this.position]; this.acceptedPhase = this.phase;
        return;
      }
      const unexpected = innovation(sub(this.position, this.lastNativePosition), this.expected) > data.innovationThreshold;
      if (unexpected) {
        this.anchor = [...this.acceptedPosition]; this.lockedPhase = this.acceptedPhase;
        this.anchorOffset = sub(this.anchor, this.world(this.preset.path[this.lockedPhase]));
        this.state = 'recovering'; this.stable = 0; this.recoveryTime = 0;
        this.trail = [[...this.position]];
      }
    }
    endDrag() { this.dragging = false; }
    velocity(point) {
      const local = sub(sub(point, this.shift), this.anchorOffset);
      return field(this.preset, this.lockedPhase, local);
    }
    perturb() {
      if (!this.beginDrag()) return;
      this.drag(add(this.position, [0, -.095])); this.endDrag();
    }
    step(dt) {
      if (this.paused) return;
      if (['predicting', 'selecting', 'replanning'].includes(this.state)) {
        this.timer += dt;
        const duration = this.state === 'selecting' ? .65 : 1.1;
        if (this.timer < duration) return;
        this.timer = 0;
        if (this.state === 'replanning') {
          this.phase = this.lockedPhase;
          this.presetIndex = (this.presetIndex + 1) % data.presets.length;
          this.query += 1;
          this.shift = sub(this.position, this.preset.path[this.phase]);
          this.fraction = 0; this.anchor = null; this.lockedPhase = null;
          this.anchorOffset = null; this.trail = [];
          this.acceptedPosition = [...this.position]; this.acceptedPhase = this.phase;
          this.lastNativePosition = [...this.position]; this.expected = [0, 0];
          this.state = 'predicting';
        } else this.state = this.state === 'predicting' ? 'selecting' : (this.phase === this.maxPhase ? 'complete' : 'executing');
        return;
      }
      if (this.state === 'executing') {
        this.lastNativePosition = [...this.position];
        const fraction = Math.min(1, this.fraction + dt / .34);
        const segment = sub(this.preset.path[this.phase + 1], this.preset.path[this.phase]);
        this.expected = mul(segment, fraction - this.fraction);
        this.position = add(this.position, this.expected);
        this.fraction = fraction;
        if (fraction >= 1 - 1e-10) {
          this.phase += 1; this.fraction = 0;
          if (this.phase >= this.maxPhase) this.state = 'complete';
        }
        this.observePosition();
      } else if (this.state === 'recovering') {
        // A held pointer imposes the displaced position, but only recovery
        // freezes the native command sequence. Normal commands continue on hold.
        if (this.dragging) return;
        const v = this.velocity(this.position);
        // Direction-preserving saturation and the same kinematic integration gain
        // used by the repository's position-only intervention illustration.
        const scale = Math.min(1, data.maxStep / Math.max(norm(v), 1e-12));
        this.position = add(this.position, mul(v, scale * data.integrationGain * dt * 60));
        this.recoveryTime += dt;
        this.trail.push([...this.position]);
        if (this.trail.length > 900) this.trail.shift();
        const error = norm(sub(this.position, this.anchor));
        this.lastError = error;
        this.stable = error <= data.reentryRadius ? this.stable + 1 : 0;
        if (this.stable >= data.stableSteps) { this.state = 'replanning'; this.timer = 0; }
        else if (this.recoveryTime > 30) this.state = 'recovery-timeout';
      }
    }
    snapshot() {
      return {state:this.state, phase:this.phase, position:[...this.position],
        anchor:this.anchor && [...this.anchor], lockedPhase:this.lockedPhase, query:this.query,
        acceptedPosition:[...this.acceptedPosition], acceptedPhase:this.acceptedPhase,
        paused:this.paused, dragging:this.dragging, lastError:this.lastError};
    }
  }
  window.DSPRecovery = {Demo, field, projectCLF, innovation, supportRatio, add, sub, mul, norm};
})();
