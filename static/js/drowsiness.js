/**
 * AVALON MOTORS — AI Drowsiness Detection Engine
 * Uses MediaPipe Face Mesh to compute Eye Aspect Ratio (EAR) in real time.
 * Triggers graduated alerts, logs to Django backend, and handles GPS.
 */

'use strict';

// ─── Configuration ─────────────────────────────────────────────────
const CONFIG = {
  EAR_THRESHOLD:        0.25,   // Below this = eye closed
  EAR_CONSEC_FRAMES:    15,     // Frames before alarm
  EAR_ALERT_FRAMES:     20,     // Higher severity
  EAR_CRITICAL_FRAMES:  30,     // Critical severity
  ALARM_MAX_VOLUME:     1.0,
  ALARM_RAMP_RATE:      0.05,   // Volume ramp per frame
  FPS_SAMPLE_INTERVAL:  1000,   // ms
  GPS_UPDATE_INTERVAL:  10000,  // ms
  LOG_COOLDOWN_MS:      4000,   // Min ms between backend logs
};

// MediaPipe landmark indices for eyes
const LEFT_EYE  = [362, 385, 387, 263, 373, 380];
const RIGHT_EYE = [33,  160, 158, 133, 153, 144];

// ─── State ─────────────────────────────────────────────────────────
let state = {
  sessionId:       null,
  isRunning:       false,
  closedFrames:    0,
  sessionAlerts:   0,
  safetyScore:     100,
  lastEAR:         0,
  alarmVolume:     0,
  alarmActive:     false,
  lastLogTime:     0,
  lastGPSTime:     0,
  lat:             null,
  lng:             null,
  fpsCounter:      0,
  fpsLastTime:     Date.now(),
  currentFPS:      0,
  sessionStart:    null,
  faceMesh:        null,
  camera:          null,
  audioCtx:        null,
  alarmOsc:        null,
  alarmGain:       null,
};

// ─── DOM References ────────────────────────────────────────────────
const els = {
  video:          () => document.getElementById('videoFeed'),
  canvas:         () => document.getElementById('canvasOverlay'),
  startBtn:       () => document.getElementById('startCameraBtn'),
  stopBtn:        () => document.getElementById('stopCameraBtn'),
  endBtn:         () => document.getElementById('endSessionBtn'),
  hudFps:         () => document.getElementById('hudFps'),
  hudEar:         () => document.getElementById('hudEar'),
  earDisplay:     () => document.getElementById('earDisplay'),
  earBar:         () => document.getElementById('earBar'),
  frameCount:     () => document.getElementById('frameCount'),
  frameBar:       () => document.getElementById('frameBar'),
  sessionAlerts:  () => document.getElementById('sessionAlerts'),
  safetyScore:    () => document.getElementById('safetyScore'),
  safetyBar:      () => document.getElementById('safetyBar'),
  gpsDisplay:     () => document.getElementById('gpsDisplay'),
  alertLog:       () => document.getElementById('alertLog'),
  alertOverlay:   () => document.getElementById('alertOverlay'),
  alertBanner:    () => document.getElementById('alertBannerText'),
  alarmBar:       () => document.getElementById('alarmBar'),
  videoWrapper:   () => document.getElementById('videoWrapper'),
  leftEye:        () => document.getElementById('leftEye'),
  rightEye:       () => document.getElementById('rightEye'),
  timer:          () => document.getElementById('sessionTimer'),
};

// ─── Session Init ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const dataEl = document.getElementById('sessionData');
  state.sessionId = dataEl ? dataEl.dataset.sessionId : null;
  state.sessionStart = Date.now();

  // Session timer
  setInterval(updateTimer, 1000);

  // GPS tracking
  startGPS();
  setInterval(() => {
    if (state.lat && state.lng && state.sessionId) sendLocation();
  }, CONFIG.GPS_UPDATE_INTERVAL);

  // Button listeners
  const startBtn = els.startBtn();
  const endBtn   = els.endBtn();
  if (startBtn) startBtn.addEventListener('click', initCamera);
  if (endBtn)   endBtn.addEventListener('click', endSession);
});

// ─── Timer ─────────────────────────────────────────────────────────
function updateTimer() {
  const elapsed = Math.floor((Date.now() - state.sessionStart) / 1000);
  const h = String(Math.floor(elapsed / 3600)).padStart(2, '0');
  const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0');
  const s = String(elapsed % 60).padStart(2, '0');
  const t = els.timer();
  if (t) t.textContent = `${h}:${m}:${s}`;
}

// ─── Camera & MediaPipe Init ───────────────────────────────────────
async function initCamera() {
  const video  = els.video();
  const canvas = els.canvas();
  if (!video) return;

  els.startBtn().style.display = 'none';

  // Setup MediaPipe Face Mesh
  state.faceMesh = new FaceMesh({
    locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`
  });

  state.faceMesh.setOptions({
    maxNumFaces: 1,
    refineLandmarks: true,
    minDetectionConfidence: 0.5,
    minTrackingConfidence: 0.5,
  });

  state.faceMesh.onResults(onFaceMeshResults);

  // Start camera
  state.camera = new Camera(video, {
    onFrame: async () => {
      if (state.faceMesh && video.readyState >= 2) {
        await state.faceMesh.send({ image: video });
      }
    },
    width: 640,
    height: 480,
  });

  try {
    await state.camera.start();
    state.isRunning = true;

    // Match canvas size to video
    video.addEventListener('loadedmetadata', () => {
      canvas.width  = video.videoWidth;
      canvas.height = video.videoHeight;
    });

    addLogEntry('Camera started — AI monitoring active', 'info');
  } catch (err) {
    console.error('Camera error:', err);
    addLogEntry('Camera access denied. Please allow camera permissions.', 'critical');
    els.startBtn().style.display = '';
  }
}

// ─── EAR Computation ──────────────────────────────────────────────
function computeEAR(landmarks, indices, w, h) {
  const pts = indices.map(i => ({
    x: landmarks[i].x * w,
    y: landmarks[i].y * h,
  }));
  // EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
  const A = dist(pts[1], pts[5]);
  const B = dist(pts[2], pts[4]);
  const C = dist(pts[0], pts[3]);
  return (A + B) / (2.0 * C);
}

function dist(a, b) {
  return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2);
}

// ─── Face Mesh Results Handler ─────────────────────────────────────
function onFaceMeshResults(results) {
  const canvas = els.canvas();
  const video  = els.video();
  if (!canvas || !video) return;

  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // FPS
  state.fpsCounter++;
  const now = Date.now();
  if (now - state.fpsLastTime >= CONFIG.FPS_SAMPLE_INTERVAL) {
    state.currentFPS = state.fpsCounter;
    state.fpsCounter = 0;
    state.fpsLastTime = now;
    const fpsel = els.hudFps();
    if (fpsel) fpsel.textContent = `${state.currentFPS} FPS`;
  }

  if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) {
    // No face detected
    state.closedFrames = 0;
    updateEyeIndicators(true, true);
    dismissAlert();
    return;
  }

  const landmarks = results.multiFaceLandmarks[0];
  const W = canvas.width;
  const H = canvas.height;

  // Draw landmarks
  drawFaceMesh(ctx, landmarks, W, H);

  // Calculate EAR
  const earL = computeEAR(landmarks, LEFT_EYE, W, H);
  const earR = computeEAR(landmarks, RIGHT_EYE, W, H);
  const ear  = (earL + earR) / 2;
  state.lastEAR = ear;

  // Update UI
  updateEarUI(ear);

  const eyesClosed = ear < CONFIG.EAR_THRESHOLD;
  updateEyeIndicators(!eyesClosed, !eyesClosed);

  if (eyesClosed) {
    state.closedFrames++;
    handleClosedEyes();
  } else {
    if (state.closedFrames > 0) {
      dismissAlert();
    }
    state.closedFrames = 0;
  }

  updateFrameUI();
}

// ─── Eye Closure Logic ─────────────────────────────────────────────
function handleClosedEyes() {
  const fc = state.closedFrames;

  if (fc >= CONFIG.EAR_CRITICAL_FRAMES) {
    triggerAlert('critical', 'CRITICAL — DRIVER ASLEEP');
  } else if (fc >= CONFIG.EAR_ALERT_FRAMES) {
    triggerAlert('high', '⚠ SEVERE FATIGUE DETECTED');
  } else if (fc >= CONFIG.EAR_CONSEC_FRAMES) {
    triggerAlert('medium', '⚠ DROWSINESS DETECTED');
  }

  // Ramp alarm volume
  if (fc >= CONFIG.EAR_CONSEC_FRAMES) {
    state.alarmVolume = Math.min(CONFIG.ALARM_MAX_VOLUME,
      state.alarmVolume + CONFIG.ALARM_RAMP_RATE);
    playAlarm(state.alarmVolume);
  }
}

function dismissAlert() {
  state.closedFrames = 0;
  state.alarmVolume = 0;
  stopAlarm();

  const overlay = els.alertOverlay();
  const alarmBar = els.alarmBar();
  const wrapper  = els.videoWrapper();
  if (overlay)  overlay.classList.remove('show');
  if (alarmBar) alarmBar.classList.remove('show');
  if (wrapper)  { wrapper.classList.remove('danger-border', 'warning-border'); }
}

// ─── Alert Trigger ─────────────────────────────────────────────────
function triggerAlert(severity, message) {
  const overlay   = els.alertOverlay();
  const banner    = els.alertBanner();
  const alarmBar  = els.alarmBar();
  const wrapper   = els.videoWrapper();

  if (overlay) overlay.classList.add('show');
  if (banner)  banner.textContent = message;
  if (alarmBar) alarmBar.classList.add('show');

  if (wrapper) {
    if (severity === 'critical') {
      wrapper.classList.add('danger-border');
      wrapper.classList.remove('warning-border');
    } else {
      wrapper.classList.add('warning-border');
    }
  }

  // Log to backend with cooldown
  const now = Date.now();
  if (now - state.lastLogTime > CONFIG.LOG_COOLDOWN_MS) {
    state.lastLogTime = now;
    logAlertToBackend(severity);
    addLogEntry(`${message} (EAR: ${state.lastEAR.toFixed(3)})`, severity);
  }
}

// ─── Backend API Calls ─────────────────────────────────────────────
async function logAlertToBackend(severity) {
  if (!state.sessionId) return;

  const payload = {
    session_id:  state.sessionId,
    alert_type:  severity === 'critical' ? 'fatigue' : 'drowsiness',
    severity:    severity,
    duration:    (state.closedFrames / 30).toFixed(2),
    ear:         state.lastEAR.toFixed(4),
    lat:         state.lat,
    lng:         state.lng,
    description: `Eye closure detected for ${state.closedFrames} frames (EAR=${state.lastEAR.toFixed(3)})`,
  };

  try {
    const res = await fetch('/api/alert/log/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.safety_score !== undefined) updateSafetyScore(data.safety_score);
    state.sessionAlerts++;
    const el = els.sessionAlerts();
    if (el) el.textContent = state.sessionAlerts;
  } catch (e) {
    console.warn('Alert log failed:', e);
  }
}

async function endSession() {
  if (!state.sessionId) { window.location.href = '/driver/dashboard/'; return; }
  if (!confirm('End this monitoring session?')) return;

  stopCamera();

  try {
    await fetch('/api/session/end/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({ session_id: state.sessionId, lat: state.lat, lng: state.lng }),
    });
  } catch (e) {}

  window.location.href = '/driver/history/';
}

async function sendLocation() {
  if (!state.sessionId || !state.lat) return;
  try {
    await fetch('/api/location/update/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({ session_id: state.sessionId, lat: state.lat, lng: state.lng }),
    });
  } catch (e) {}
}

// ─── GPS ──────────────────────────────────────────────────────────
function startGPS() {
  if (!navigator.geolocation) {
    const gpsEl = els.gpsDisplay();
    if (gpsEl) gpsEl.textContent = 'GPS not available';
    return;
  }
  navigator.geolocation.watchPosition(
    pos => {
      state.lat = pos.coords.latitude;
      state.lng = pos.coords.longitude;
      const gpsEl = els.gpsDisplay();
      if (gpsEl) gpsEl.textContent = `${state.lat.toFixed(5)}, ${state.lng.toFixed(5)}`;
    },
    err => {
      const gpsEl = els.gpsDisplay();
      if (gpsEl) gpsEl.textContent = 'GPS unavailable';
    },
    { enableHighAccuracy: true, maximumAge: 5000 }
  );
}

// ─── Audio Alarm (Web Audio API) ──────────────────────────────────
function playAlarm(volume) {
  if (!state.audioCtx) {
    state.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (state.audioCtx.state === 'suspended') {
    state.audioCtx.resume();
  }

  if (!state.alarmOsc) {
    state.alarmOsc  = state.audioCtx.createOscillator();
    state.alarmGain = state.audioCtx.createGain();

    state.alarmOsc.type = 'square';
    state.alarmOsc.frequency.setValueAtTime(880, state.audioCtx.currentTime);
    // Pulsing pitch
    state.alarmOsc.frequency.setValueAtTime(1100, state.audioCtx.currentTime + 0.15);
    state.alarmOsc.frequency.setValueAtTime(880, state.audioCtx.currentTime + 0.3);

    state.alarmGain.gain.setValueAtTime(0, state.audioCtx.currentTime);
    state.alarmOsc.connect(state.alarmGain);
    state.alarmGain.connect(state.audioCtx.destination);
    state.alarmOsc.start();
    state.alarmActive = true;
  }

  if (state.alarmGain) {
    state.alarmGain.gain.setTargetAtTime(volume, state.audioCtx.currentTime, 0.1);
  }
}

function stopAlarm() {
  if (state.alarmOsc) {
    try {
      state.alarmGain.gain.setTargetAtTime(0, state.audioCtx.currentTime, 0.1);
      setTimeout(() => {
        try { state.alarmOsc.stop(); } catch(e){}
        state.alarmOsc = null;
        state.alarmGain = null;
        state.alarmActive = false;
      }, 300);
    } catch(e) {}
  }
}

// ─── Canvas Face Mesh Drawing ─────────────────────────────────────
function drawFaceMesh(ctx, landmarks, W, H) {
  const eyesClosed = state.lastEAR < CONFIG.EAR_THRESHOLD;
  const color = eyesClosed ? 'rgba(255,34,68,0.8)' : 'rgba(0,212,255,0.7)';
  const glow  = eyesClosed ? '#ff2244' : '#00d4ff';

  // Draw eye contours
  drawEyeContour(ctx, landmarks, LEFT_EYE,  W, H, color, glow);
  drawEyeContour(ctx, landmarks, RIGHT_EYE, W, H, color, glow);

  // EAR text on canvas
  ctx.save();
  ctx.font = '14px "Share Tech Mono"';
  ctx.fillStyle = color;
  ctx.shadowColor = glow;
  ctx.shadowBlur = 8;
  ctx.fillText(`EAR: ${state.lastEAR.toFixed(3)}`, 12, H - 16);
  ctx.restore();
}

function drawEyeContour(ctx, lm, indices, W, H, color, glow) {
  const pts = indices.map(i => [lm[i].x * W, lm[i].y * H]);
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
  ctx.closePath();
  ctx.strokeStyle = color;
  ctx.shadowColor = glow;
  ctx.shadowBlur = 10;
  ctx.lineWidth = 1.5;
  ctx.stroke();
  // Fill semi-transparent
  ctx.fillStyle = state.lastEAR < CONFIG.EAR_THRESHOLD ? 'rgba(255,34,68,0.1)' : 'rgba(0,212,255,0.05)';
  ctx.fill();
  ctx.restore();
}

// ─── UI Updates ───────────────────────────────────────────────────
function updateEarUI(ear) {
  const earDisplay = els.earDisplay();
  const earBar     = els.earBar();
  const hudEar     = els.hudEar();

  if (earDisplay) earDisplay.textContent = ear.toFixed(3);
  if (hudEar)     hudEar.textContent = `EAR: ${ear.toFixed(3)}`;

  const pct = Math.min(100, (ear / 0.4) * 100);
  if (earBar) {
    earBar.style.width = `${pct}%`;
    earBar.style.background = ear < 0.20 ? 'var(--red-alert)' : ear < CONFIG.EAR_THRESHOLD ? 'var(--orange-warn)' : 'var(--cyan)';
  }
}

function updateFrameUI() {
  const fc  = state.closedFrames;
  const max = CONFIG.EAR_CRITICAL_FRAMES;
  const el  = els.frameCount();
  const bar = els.frameBar();
  if (el)  el.textContent = `${fc} / ${CONFIG.EAR_CONSEC_FRAMES}`;
  if (bar) {
    const pct = Math.min(100, (fc / max) * 100);
    bar.style.width = `${pct}%`;
    bar.style.background = fc >= CONFIG.EAR_CRITICAL_FRAMES ? 'var(--red-alert)'
                         : fc >= CONFIG.EAR_ALERT_FRAMES    ? 'var(--orange-warn)'
                         : fc >= CONFIG.EAR_CONSEC_FRAMES   ? 'var(--yellow-warn)'
                         : 'var(--accent)';
  }
}

function updateEyeIndicators(leftOpen, rightOpen) {
  const leftEl  = els.leftEye();
  const rightEl = els.rightEye();
  if (leftEl)  { leftEl.className  = `eye-indicator ${leftOpen  ? 'open' : 'closed'}`; }
  if (rightEl) { rightEl.className = `eye-indicator ${rightOpen ? 'open' : 'closed'}`; }
}

function updateSafetyScore(score) {
  state.safetyScore = score;
  const el  = els.safetyScore();
  const bar = els.safetyBar();
  if (el)  el.textContent = Math.round(score);
  if (bar) {
    bar.style.width = `${score}%`;
    bar.style.background = score > 70 ? 'var(--accent)' : score > 40 ? 'var(--orange-warn)' : 'var(--red-alert)';
    el.style.color = score > 70 ? 'var(--accent)' : score > 40 ? 'var(--orange-warn)' : 'var(--red-alert)';
  }
}

function addLogEntry(message, level = 'info') {
  const log = els.alertLog();
  if (!log) return;

  // Clear placeholder
  const empty = log.querySelector('[style*="padding:1rem"]');
  if (empty) empty.remove();

  const now  = new Date();
  const time = now.toTimeString().slice(0, 8);
  const item = document.createElement('div');
  item.className = `alert-log-item ${level}`;
  item.innerHTML = `<span style="font-family:'Share Tech Mono';color:var(--text-muted);font-size:0.72rem;">${time}</span> — <span style="font-weight:600;">${message}</span>`;
  log.insertBefore(item, log.firstChild);

  // Keep max 20 entries
  while (log.children.length > 20) log.removeChild(log.lastChild);
}

// ─── Camera Stop ──────────────────────────────────────────────────
function stopCamera() {
  state.isRunning = false;
  if (state.camera) { try { state.camera.stop(); } catch(e) {} state.camera = null; }
  if (state.faceMesh) { try { state.faceMesh.close(); } catch(e) {} state.faceMesh = null; }
  stopAlarm();
  dismissAlert();
}

// ─── CSRF Helper ─────────────────────────────────────────────────
function getCsrf() {
  const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
  return cookie ? cookie.split('=')[1].trim() : '';
}
