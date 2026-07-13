/**
 * autocapture.test.js — pure-Node tests for the guided webcam capture
 * state machine. Run: node src/face_clone/autocapture.test.js
 */
import { strict as assert } from 'assert';
import { AutoCapture, yawOf, pitchOf } from './autocapture.js';

let passed = 0;
let failed = 0;
const test = (name, fn) => {
  try {
    fn();
    passed++;
    console.log(`✅ ${name}`);
  } catch (e) {
    failed++;
    console.error(`❌ ${name}: ${e.message}`);
  }
};

/** Synthetic MediaPipe-style matrix with a given yaw/pitch (radians). */
const mat = (yaw, pitch = 0) => {
  const m = new Array(16).fill(0);
  m[8] = Math.sin(yaw);
  m[10] = Math.cos(yaw);
  m[9] = Math.tan(pitch) * Math.cos(yaw);
  return m;
};

const feed = (ac, yaw, n, pitch = 0) => {
  let last;
  for (let i = 0; i < n; i++) last = ac.update(mat(yaw, pitch));
  return last;
};

test('yaw/pitch extraction', () => {
  assert.ok(Math.abs(yawOf(mat(0.4)) - 0.4) < 1e-9);
  assert.ok(Math.abs(pitchOf(mat(0, 0.2)) - 0.2) < 1e-6);
  assert.equal(yawOf(null), null);
});

test('guided sequence: front → left → right → done', () => {
  const ac = new AutoCapture({ holdFrames: 4 });
  let s = feed(ac, 0.02, 4);
  assert.equal(s.capture, 'front');
  s = feed(ac, 0.5, 4);
  assert.equal(s.capture, 'left', 'first side = left regardless of sign');
  s = feed(ac, -0.5, 4);
  assert.equal(s.capture, 'right');
  assert.ok(ac.done);
  assert.equal(ac.update(mat(0)).instruction, 'all three angles captured ✓');
});

test('mirrored convention: negative-first side still fills left', () => {
  const ac = new AutoCapture({ holdFrames: 3 });
  feed(ac, 0, 3);
  const s1 = feed(ac, -0.45, 3);
  assert.equal(s1.capture, 'left');
  const s2 = feed(ac, 0.45, 3);
  assert.equal(s2.capture, 'right');
});

test('hold resets on wobble — no mid-turn snaps', () => {
  const ac = new AutoCapture({ holdFrames: 5 });
  feed(ac, 0.02, 4); // 4 of 5 held
  let s = ac.update(mat(0.6)); // wobble out of front band
  assert.equal(s.capture, null);
  s = feed(ac, 0.02, 4);
  assert.equal(s.capture, null, 'hold restarted, 4 of 5 again');
  s = ac.update(mat(0.02));
  assert.equal(s.capture, 'front');
});

test('extreme pitch gates capture', () => {
  const ac = new AutoCapture({ holdFrames: 2 });
  const s = feed(ac, 0.0, 6, 0.6); // looking way up
  assert.equal(s.capture, null);
  assert.equal(ac.needed.length, 3);
});

test('no face → guidance, not crash', () => {
  const ac = new AutoCapture();
  const s = ac.update(null);
  assert.equal(s.yaw, null);
  assert.match(s.instruction, /no face/);
});

test('duplicate angles are not re-captured', () => {
  const ac = new AutoCapture({ holdFrames: 2 });
  feed(ac, 0, 2);
  feed(ac, 0.5, 2);
  const s = feed(ac, 0.5, 10); // stay left — nothing new to capture
  assert.equal(s.capture, null);
  assert.deepEqual(ac.needed, ['right']);
});

console.log(`\nautocapture: ${passed} passed, ${failed} failed`);
if (failed) process.exit(1);
