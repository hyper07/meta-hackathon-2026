// Watch Me: the phone page. Streams 4-second chunks of 16 kHz audio to the server,
// shows what the agents decided, and answers "Are you OK?".
"use strict";

const CHUNK_SECONDS = 4;
const TARGET_RATE = 16000;
const $ = (id) => document.getElementById(id);

let ws = null, wsBackoff = 500;
// Public demo: the server gives this visit a token; every API call carries it.
let visitToken = "";
const plainFetch = window.fetch.bind(window);
window.fetch = (url, opts = {}) => {
  if (visitToken && String(url).startsWith("/api/")) opts = { ...opts, headers: { ...(opts.headers || {}), "X-Visit": visitToken } };
  return plainFetch(url, opts);
};
let mic = null;              // the standby/watching stream
let profile = {};
let state = "standby";
let wakeLock = null;
let countdownTimer = null;
let lastLocationSent = 0;
let pinAction = null;
let mode = "watch";          // watch (emergency) | notice (school, work)

// ── microphone ────────────────────────────────────────────────────────────

const WORKLET = `
class Tap extends AudioWorkletProcessor {
  process(inputs) { const ch = inputs[0][0]; if (ch) this.port.postMessage(ch.slice(0)); return true; }
}
registerProcessor("tap", Tap);`;

class Mic {
  constructor(onChunk, seconds) { this.onChunk = onChunk; this.seconds = seconds; this.buf = []; this.len = 0; }
  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: false, autoGainControl: true, channelCount: 1 },
    });
    // Ask for a 16 kHz context so the browser does the resampling with a proper filter. The manual
    // downsample below (a plain average) aliases party noise and cost Whisper the odd "Watch me".
    const AC = window.AudioContext || window.webkitAudioContext;
    try { this.ctx = new AC({ sampleRate: TARGET_RATE }); } catch { this.ctx = new AC(); }
    const url = URL.createObjectURL(new Blob([WORKLET], { type: "application/javascript" }));
    await this.ctx.audioWorklet.addModule(url);
    this.source = this.ctx.createMediaStreamSource(this.stream);
    this.node = new AudioWorkletNode(this.ctx, "tap");
    this.node.port.onmessage = (e) => this.push(e.data);
    this.source.connect(this.node);
    const want = this.seconds * this.ctx.sampleRate;
    this.want = want;
  }
  push(frame) {
    if (this.onLevel) { let s = 0; for (const v of frame) s += v * v; this.onLevel(Math.sqrt(s / frame.length)); }
    this.buf.push(frame); this.len += frame.length;
    if (this.len >= this.want) {
      const all = new Float32Array(this.len);
      let o = 0; for (const f of this.buf) { all.set(f, o); o += f.length; }
      this.buf = []; this.len = 0;
      this.onChunk(toPcm16(downsample(all, this.ctx.sampleRate, TARGET_RATE)));
    }
  }
  take() {   // what's buffered so far, for a recording the owner ends with a tap
    const all = new Float32Array(this.len);
    let o = 0; for (const f of this.buf) { all.set(f, o); o += f.length; }
    this.buf = []; this.len = 0;
    return toPcm16(downsample(all, this.ctx.sampleRate, TARGET_RATE));
  }
  async stop() {
    try { this.source.disconnect(); this.node.disconnect(); } catch {}
    this.stream?.getTracks().forEach((t) => t.stop());
    await this.ctx?.close();
  }
}

function downsample(input, from, to) {
  if (from === to) return input;
  const ratio = from / to, out = new Float32Array(Math.floor(input.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const start = Math.floor(i * ratio), end = Math.min(input.length, Math.floor((i + 1) * ratio));
    let sum = 0; for (let j = start; j < end; j++) sum += input[j];
    out[i] = sum / Math.max(1, end - start);
  }
  return out;
}

function toPcm16(f32) {
  const out = new Int16Array(f32.length);
  for (let i = 0; i < f32.length; i++) out[i] = Math.max(-1, Math.min(1, f32[i])) * 0x7fff;
  return out.buffer;
}

function bufferToB64(buffer) {
  const bytes = new Uint8Array(buffer); let s = "";
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

function recordOnce(seconds, onLevel) {
  return new Promise((resolve, reject) => {
    const m = new Mic(async (pcm) => { await m.stop(); resolve(pcm); }, seconds);
    m.onLevel = onLevel;
    m.start().catch(reject);
  });
}

// ── voiceprint drawing ────────────────────────────────────────────────────
// A voiceprint is 512 numbers; the server sends a coarse 64-number signature of it.
// Each ring of the "fingerprint" is a circle bent by a few of those numbers, so the
// same voice always draws the same whorl, and a different voice draws a different one.

const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function drawPrint(canvas, sig, { color = cssVar("--print"), reveal = 1, alpha = 1, clear = true, wobble = 0 } = {}) {
  const ctx = canvas.getContext("2d"), W = canvas.width, cx = W / 2, cy = W / 2;
  if (clear) ctx.clearRect(0, 0, W, W);
  if (!sig?.length) return;
  const rings = 17, r0 = W * 0.045, gap = (W * 0.43 - r0) / rings, n = sig.length;
  ctx.save();
  ctx.lineWidth = Math.max(1.4, W / 120); ctx.lineCap = "round"; ctx.strokeStyle = color; ctx.globalAlpha = alpha;
  const shown = reveal * rings;
  for (let i = 0; i < Math.ceil(shown); i++) {
    const part = Math.min(1, shown - i), base = r0 + i * gap;
    ctx.beginPath();
    let pen = false;
    const steps = Math.round(220 * part);
    for (let s = 0; s <= steps; s++) {
      const th = (s / 220) * 2 * Math.PI - Math.PI / 2;
      let d = 0;
      for (let k = 1; k <= 5; k++) d += (sig[(i * 3 + k * 7) % n] * Math.cos(k * th + i * 0.35) + sig[(i * 5 + k * 11) % n] * Math.sin(k * th)) / (k + 1);
      const r = base + d * gap * 0.75 + (wobble ? Math.sin(th * 6 + wobble + i) * gap * 0.15 : 0);
      const x = cx + r * Math.cos(th) * 0.84, y = cy + r * Math.sin(th);
      if (sig[(i * 13 + Math.floor(s / 14)) % n] < -0.62) { pen = false; continue; }   // ridge breaks, like a real print
      pen ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      pen = true;
    }
    ctx.stroke();
  }
  ctx.restore();
}

function drawScan(canvas, t, level, progress = 0) {
  const ctx = canvas.getContext("2d"), W = canvas.width, c = W / 2;
  ctx.clearRect(0, 0, W, W);
  ctx.save();
  // faint ridges, so the empty print already looks like a fingerprint waiting to be filled
  ctx.strokeStyle = cssVar("--print-ghost"); ctx.lineWidth = W / 180; ctx.globalAlpha = 0.35;
  for (let i = 1; i <= 9; i++) { ctx.beginPath(); ctx.ellipse(c, c, (W * 0.36 * i) / 9 * 0.84, (W * 0.36 * i) / 9, 0, 0, 2 * Math.PI); ctx.stroke(); }
  ctx.globalAlpha = 1;
  if (progress > 0) {
    // her voice: a soft pulse with the loudness, and the time left as a ring
    ctx.fillStyle = cssVar("--print"); ctx.globalAlpha = 0.12;
    ctx.beginPath(); ctx.arc(c, c, W * 0.12 + Math.min(1, level * 9) * W * 0.26, 0, 2 * Math.PI); ctx.fill();
    ctx.globalAlpha = 0.25; ctx.strokeStyle = cssVar("--print-ghost"); ctx.lineWidth = W / 40;
    ctx.beginPath(); ctx.arc(c, c, W * 0.45, 0, 2 * Math.PI); ctx.stroke();
    ctx.globalAlpha = 1; ctx.strokeStyle = cssVar("--print"); ctx.lineCap = "round";
    ctx.beginPath(); ctx.arc(c, c, W * 0.45, -Math.PI / 2, -Math.PI / 2 + progress * 2 * Math.PI); ctx.stroke();
    const a = t * 3, g = ctx.createConicGradient ? ctx.createConicGradient(a, c, c) : null;
    if (g) { g.addColorStop(0, "rgba(8,102,255,.35)"); g.addColorStop(0.12, "rgba(8,102,255,0)"); g.addColorStop(1, "rgba(8,102,255,0)");
             ctx.fillStyle = g; ctx.beginPath(); ctx.arc(c, c, W * 0.4, 0, 2 * Math.PI); ctx.fill(); }
  }
  ctx.restore();
}

function animateReveal(canvas, sig, ms = 1600) {
  return new Promise((resolve) => {
    const t0 = performance.now();
    const step = (now) => {
      const p = Math.min(1, (now - t0) / ms);
      drawPrint(canvas, sig, { reveal: 1 - Math.pow(1 - p, 3) });
      p < 1 ? requestAnimationFrame(step) : resolve();
    };
    requestAnimationFrame(step);
  });
}

// ── voice lock panel ──────────────────────────────────────────────────────

const ARC = Math.PI * 80;           // length of the gauge's half circle
const GAUGE_FLOOR = 0;              // the server sends a 0-1 display match
const gaugePos = (s) => Math.max(0, Math.min(1, (s - GAUGE_FLOOR) / (1 - GAUGE_FLOOR)));
let thresholds = { start: 0.70, strict: 0.90 };

function placeTick(id, value) {
  const th = Math.PI * (1 - gaugePos(value)), x = 100 + Math.cos(th) * 80, y = 100 - Math.sin(th) * 80;
  const el = $(id), ix = 100 + Math.cos(th) * 64, iy = 100 - Math.sin(th) * 64, ox = 100 + Math.cos(th) * 96, oy = 100 - Math.sin(th) * 96;
  el.setAttribute("x1", ix); el.setAttribute("y1", iy); el.setAttribute("x2", ox); el.setAttribute("y2", oy);
  return { x, y };
}

function matchColor(s) {
  return s >= thresholds.strict ? cssVar("--match-ok") : s >= thresholds.start ? cssVar("--match-mid") : cssVar("--match-bad");
}

function setGauge(s) {
  const v = $("gValue");
  v.style.strokeDasharray = `${gaugePos(s) * ARC} 999`;
  v.style.stroke = matchColor(s);
  $("gPct").textContent = Math.round(s * 100) + "%";
}

function renderOwnerPrint() {
  const enrolled = !!profile.voice_signature;
  $("voiceLock").hidden = !(enrolled && mic);   // the lock matters once it's listening
  if (!enrolled) return;
  placeTick("gTickStart", thresholds.start); placeTick("gTickStrict", thresholds.strict);
  drawPrint($("vlOwner"), profile.voice_signature);
  $("vlOwnerId").textContent = profile.voice_id || "";
}

function onVoice(v) {
  if (v.match == null) return;
  $("voiceLock").hidden = false;
  const live = $("vlLive");
  drawPrint(live, profile.voice_signature, { color: cssVar("--print-ghost"), alpha: 0.5 });
  drawPrint(live, v.signature, { color: matchColor(v.match), clear: false });
  setGauge(v.match);
  const pct = Math.round(v.match * 100);
  $("vlWho").innerHTML = v.strict ? `<b>You</b> · verified` : v.owner ? `<b>Probably you</b> · ${pct}%` : `<b>Someone else</b> · ${pct}%`;
  if (v.command && v.outcome) commandToast(v, pct);
}

const COMMAND_NAMES = { start: "“Watch me”", stop: "“Stop watching”", ok: "“I'm OK”", not_ok: "“I'm not OK”", sos: "SOS phrase" };

function commandToast(v, pct) {
  const what = COMMAND_NAMES[v.command] || v.command;
  const lock = $("voiceLock");
  if (v.outcome === "accepted") {
    const after = { start: "Recording is locked to your voice.", stop: "Stopped.", ok: "Glad you're OK.", not_ok: "Alerting your contacts.", sos: "Alerting your contacts now." }[v.command] || "";
    toast("ok", `<span class="big-icon">✓</span><b>${what}</b>: verified as you (${pct}%). ${after}`);
    buzz([20, 40, 20]);
    lock.classList.remove("pulse-ok"); void lock.offsetWidth; lock.classList.add("pulse-ok");
  } else if (v.outcome === "refused") {
    const need = Math.round((v.command === "start" ? thresholds.start : thresholds.strict) * 100);
    const after = v.command === "start" ? "Not started." : v.command === "ok" ? "Still waiting for your answer." : "Still recording.";
    toast("bad", `<span class="big-icon">🔒</span><b>${what} refused</b>: not your voice (${pct}%, needs ${need}%). ${after}`);
    buzz([60, 50, 60]);
    lock.classList.remove("shake"); void lock.offsetWidth; lock.classList.add("shake");
  }
}

// Haptics on the web: a short vibration where the browser supports it (Android Chrome); iOS browsers ignore it.
const buzz = (pattern) => { try { navigator.vibrate?.(pattern); } catch {} };

function toast(kind, html) {
  const t = $("toast");
  t.className = "toast " + kind; t.innerHTML = html; t.hidden = false;
  void t.offsetWidth; t.classList.add("show");
  clearTimeout(t._t);
  t._t = setTimeout(() => { t.classList.remove("show"); setTimeout(() => (t.hidden = true), 400); }, 5000);
}

// ── connection ────────────────────────────────────────────────────────────

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.binaryType = "arraybuffer";
  ws.onopen = () => { wsBackoff = 500; };
  ws.onmessage = (e) => handle(JSON.parse(e.data));
  ws.onclose = () => { setTimeout(connect, wsBackoff); wsBackoff = Math.min(wsBackoff * 2, 8000); };
}

const sendJson = (o) => ws?.readyState === 1 && ws.send(JSON.stringify(o));
// A heartbeat, so the public demo knows this page is still open (and frees it soon after it closes).
setInterval(() => sendJson({ type: "ping" }), 15000);

function handle(m) {
  switch (m.type) {
    case "hello":
      profile = m.profile; renderServices(m.services);
      if (m.mode) mode = m.mode;
      setState(m.state);
      showOffline(m.offline || m.pending > 0, m.pending);
      if (m.thresholds) thresholds = m.thresholds;
      renderOwnerPrint(); break;
    case "voice": onVoice(m); break;
    case "mode": mode = m.mode; setState(state); break;
    case "offline": showOffline(true, m.pending); if (m.text) notice(m.text); break;
    case "online":
      showOffline(m.pending > 0, m.pending);
      toast("ok", `<span class="big-icon">✓</span><b>Back online.</b> ${m.done} moment${m.done === 1 ? "" : "s"} analyzed and added to your record.`);
      break;
    case "noted": addEvent($("live"), `Marked for your review${m.reason ? ": " + esc(m.reason) : ""}`, "noted", true); break;
    case "notice_review":
      toast("info", `<span class="big-icon">📝</span><b>Your review is ready</b> on the Notice tab.`);
      lastSessionReview = m.record; break;
    case "state":
      if (m.mode) mode = m.mode;
      setState(m.state); if (m.notice) notice(m.notice);
      if (m.state === "watching") { $("live").innerHTML = ""; $("alertCard").hidden = true; }
      break;
    case "notice": notice(m.text); break;
    case "demo": showDemo(m); break;
    case "busy": visitToken = ""; showDemo(null, m.text); break;
    case "level":
      $("orb").style.setProperty("--level", Math.max(0, Math.min(1, (m.dbfs + 55) / 40)).toFixed(2));
      $("recBadge").hidden = !m.recording; break;
    case "segment": addSegment($("live"), m, true); break;
    case "update": updateSegment(m); break;
    case "decision": addEvent($("live"), decisionText(m), "decision", true); break;
    case "checkin": showCheckin(m); break;
    case "checkin_result": hideCheckin(); notice(m.ok ? "Thanks. Still watching." : "Alerting your contacts now."); break;
    case "alert": showAlert(m); break;
    case "locate": locateNow(); break;
  }
}

// ── watch screen ──────────────────────────────────────────────────────────

const MODE_HINTS = {
  watch: "Asks “Are you OK?” and alerts your people if you can't answer.",
  notice: "For class or work. No check-ins, no alerts; a review when you stop.",
};

function setState(s) {
  state = s;
  const watching = s === "watching", noticing = watching && mode === "notice";
  const orbState = noticing ? "noticing" : watching ? "watching" : mic ? "listening" : "";
  $("orb").className = "orb " + orbState;
  $("stateDot").className = "dot " + orbState;
  $("statusLabel").textContent = noticing ? "Noticing" : watching ? "Watching" : mic ? "Ready" : "Off";
  $("statusHint").innerHTML = noticing
    ? 'Keeping notes quietly. Say <b>“stop watching”</b> for your review.'
    : watching ? 'Only your voice can say <b>“stop watching”</b>.'
    : mic ? 'Say <b>“Watch me”</b>' : 'Hold to start listening, then say <b>“Watch me”</b>';
  $("micButton").textContent = mic ? "Stop listening" : "Start listening";
  if (!mic) $("voiceLock").hidden = true; else if (profile.voice_signature) $("voiceLock").hidden = false;
  $("modeSwitch").hidden = $("modeHint").hidden = watching;
  document.querySelectorAll("#modeSwitch button").forEach((b) => {
    b.classList.toggle("active", b.dataset.mode === mode); b.setAttribute("aria-checked", b.dataset.mode === mode);
  });
  $("modeHint").textContent = MODE_HINTS[mode];
  $("micButton").hidden = watching;
  $("lockedChip").hidden = !(watching && profile.enrolled);
  $("pinStop").hidden = !watching;
  $("pinStart").hidden = watching;
  $("liveTitle").hidden = !watching;
}

async function toggleMic() {
  if (mic) {
    await mic.stop(); mic = null; wakeLock?.release(); wakeLock = null;
    setState(state); return;
  }
  try {
    mic = new Mic((pcm) => ws?.readyState === 1 && ws.send(pcm), CHUNK_SECONDS);
    await mic.start();
  } catch (e) { mic = null; notice("Microphone blocked: " + e.message + ". On a phone, the page must be opened over https."); return; }
  try { wakeLock = await navigator.wakeLock?.request("screen"); } catch {}
  watchLocation();
  setState(state);
}

function sendFix(p) {
  lastLocationSent = Date.now();
  sendJson({ type: "location", lat: p.coords.latitude, lon: p.coords.longitude, accuracy: p.coords.accuracy, time: p.timestamp });
}

function watchLocation() {
  navigator.geolocation?.watchPosition((p) => {
    if (Date.now() - lastLocationSent < 30000) return;
    sendFix(p);
  }, () => {}, { enableHighAccuracy: true, maximumAge: 30000 });
}

// The server asks for a fresh fix when it checks in or is about to alert.
function locateNow() {
  navigator.geolocation?.getCurrentPosition(sendFix, () => {}, { enableHighAccuracy: true, maximumAge: 10000, timeout: 8000 });
}

// While the model API is unreachable the phone keeps every chunk and queues the analysis; this bar says so.
function showOffline(on, pending) {
  $("offlineBar").hidden = !on;
  $("offlineCount").textContent = pending ? `${pending} moment${pending === 1 ? "" : "s"} waiting for a connection.` : "";
}

async function retryPending() {
  $("retryPending").disabled = true;
  try {
    const out = await (await fetch("/api/pending/retry", { method: "POST" })).json();
    showOffline(out.offline || out.pending > 0, out.pending);
    if (!out.done) notice(out.pending ? "Still no connection. It will keep trying." : "Nothing waiting.");
  } finally { $("retryPending").disabled = false; }
}

function showDemo(m, busy) {
  const b = $("demoBanner");
  if (m) {
    visitToken = m.visit;
    b.innerHTML = `<b>Public demo.</b> Alerts are a dry run: nobody is texted or called, and the contacts are examples. ` +
      `Nothing you say or type is kept after you leave. You have ${Math.round(m.seconds / 60)} minutes. ` +
      `<b>Try it:</b> Setup › record your voice (one line), then Watch › say <b>"Watch me"</b>. PIN for the fallback: ${esc(m.pin)}. ` +
      `<b>Review</b> and <b>Notice</b> already hold example history: three recorded sessions and a pattern of three from one professor.`;
    showWelcome();
  } else {
    b.textContent = busy;
  }
  b.hidden = false;
}

function notice(text) {
  const n = $("notice"); n.textContent = text; n.hidden = false;
  clearTimeout(n._t); n._t = setTimeout(() => (n.hidden = true), 8000);
}

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const clock = (t) => new Date(t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

function highlight(text, quotes) {
  let html = esc(text);
  for (const q of quotes || []) {
    if (!q) continue;
    const re = new RegExp(esc(q).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
    html = html.replace(re, (m) => `<mark>${m}</mark>`);
  }
  return html;
}

// The score pill appears only once a line is marked; the engine's name goes in the pill's tooltip.
const scorePill = (score, engine, level) => (level || "none") === "none" ? "" :
  `<span class="score" title="${esc(engine)}">${(score ?? 0).toFixed(2)}</span>`;

function segmentHtml(s) {
  const who = s.speaker === "owner" ? "You" : s.speaker === "other" ? "Someone else" : "Voice";
  return `<div class="bar"></div><div>
    <div class="meta"><span class="who ${s.speaker}">${who}</span><span>${clock(s.t)}</span>${s.loud ? "<span>loud</span>" : ""}
      ${scorePill(s.score, s.engine, s.level)}</div>
    <div class="text">${highlight(s.text, s.quotes)}</div>
    ${s.reason ? `<div class="reason">${esc(s.reason)}</div>` : ""}</div>`;
}

function addSegment(list, s, newestFirst) {
  const li = document.createElement("li");
  li.className = `seg ${s.level || "none"}`; li.id = "seg-" + s.seg; li.dataset.level = s.level || "none";
  li.innerHTML = segmentHtml(s);
  newestFirst ? list.prepend(li) : list.append(li);
}

function updateSegment(u) {
  const li = $("seg-" + u.seg); if (!li) return;
  li.className = `seg ${u.level}`; li.dataset.level = u.level;
  li.querySelector(".meta .score")?.remove();
  li.querySelector(".meta").insertAdjacentHTML("beforeend", scorePill(u.score, u.engine, u.level));
  li.querySelector(".text").innerHTML = highlight(li.querySelector(".text").textContent, u.quotes);
  const r = li.querySelector(".reason") || li.lastElementChild.appendChild(Object.assign(document.createElement("div"), { className: "reason" }));
  r.textContent = u.reason;
}

function addEvent(list, html, kind, newestFirst, t) {
  const li = document.createElement("li");
  li.className = "event " + kind; li.innerHTML = (t ? `${clock(t)} · ` : "") + html;
  newestFirst ? list.prepend(li) : list.append(li);
}

function decisionText(d) {
  const p = d.probabilities ? ` · ${Object.entries(d.probabilities).map(([k, v]) => `${k} ${(v * 100).toFixed(0)}%`).join(" · ")}` : "";
  const what = d.action === "ask" ? (d.urgent ? "urgent check-in" : "check-in") : d.action;
  return `Decider (${esc(d.engine)}${d.ms ? `, ${d.ms} ms` : ""}): <b>${esc(what)}</b>${esc(p)}<br>${esc(d.why)}`;
}

function showCheckin(m) {
  $("checkinWhy").textContent = m.reason || "";
  $("checkin").hidden = false;
  const total = Math.round(m.timeout);
  let left = total;
  const ring = $("countRing"), circumference = 2 * Math.PI * 54;
  const tick = () => { $("countdown").textContent = left; ring.style.strokeDashoffset = circumference * (1 - left / total); };
  ring.style.transition = "none"; tick(); void ring.offsetWidth; ring.style.transition = "";
  clearInterval(countdownTimer);
  countdownTimer = setInterval(() => { left = Math.max(0, left - 1); tick(); }, 1000);
  navigator.vibrate?.([400, 200, 400, 200, 400]);
  say("are-you-ok", "Are you OK? Say I'm OK.");
}

// The app's spoken prompts are recorded files (static/voice, a natural voice); the browser's own
// speech is only the fallback when a file can't play.
// Browsers only play sound after a tap on the page; Safari, only on an element that a tap has played
// once. unlockSound() runs inside a tap and keeps these elements, so later prompts can play by themselves.
const voices = {};
function say(name, fallbackText) {
  const a = voices[name] || new Audio(`/static/voice/${name}.wav`);
  a.currentTime = 0;
  a.play().catch(() => { try { speechSynthesis.speak(new SpeechSynthesisUtterance(fallbackText)); } catch {} });
}

function unlockSound() {
  for (const name of ["are-you-ok", "alerting"]) {
    if (voices[name]) continue;
    const a = new Audio(`/static/voice/${name}.wav`);
    a.muted = true;
    a.play().then(() => { a.pause(); a.currentTime = 0; a.muted = false; }).catch(() => { a.muted = false; });
    voices[name] = a;
  }
  try { speechSynthesis.speak(new SpeechSynthesisUtterance("")); } catch {}
}
// The owner's own app: the first tap anywhere unlocks sound.
document.addEventListener("pointerdown", unlockSound, { once: true });

// ── welcome: microphone and sound ────────────────────────────────────────

let welcomed = false;
async function micAllowed() {
  try { return (await navigator.permissions.query({ name: "microphone" })).state === "granted"; } catch { return false; }
}

function showWelcome() {
  if (welcomed) return;
  $("welcome").hidden = false;
}

async function welcomeGo() {
  const status = $("welcomeStatus"), go = $("welcomeGo");
  unlockSound();                                   // inside the tap: sound is allowed from now on
  status.hidden = false;
  $("wsSound").textContent = "🔊 Sound: on. You should hear the check-in now.";
  go.disabled = true;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach((t) => t.stop());   // only the permission; listening starts on Watch
    $("wsMic").textContent = "🎙️ Microphone: allowed ✓";
    say("are-you-ok", "Are you OK? Say I'm OK.");
    welcomed = true;
    setTimeout(() => { $("welcome").hidden = true; }, 3500);
  } catch (error) {
    $("wsMic").innerHTML = "🎙️ Microphone: <b>blocked</b>. Allow it for this site: tap the icon left of the address " +
      "(the lock or <b>aA</b>), set Microphone to Allow, then reload the page.";
    go.disabled = false; go.textContent = "Try again";
  }
}
$("welcomeGo").addEventListener("click", welcomeGo);
$("welcomeSkip").addEventListener("click", () => { welcomed = true; unlockSound(); $("welcome").hidden = true; });
// Ask on the first visit, or whenever the microphone isn't allowed yet. The public demo asks every visit.
micAllowed().then((ok) => { if (!ok) showWelcome(); });

function hideCheckin() { $("checkin").hidden = true; clearInterval(countdownTimer); }

// The alert text with its map link as a tappable pin.
function linkMap(text) {
  return esc(text).replace(/\n/g, "<br>").replace(/https:\/\/maps\.google\.com\/\?q=(-?[\d.]+),(-?[\d.]+)/g,
    (url, lat, lon) => `<a class="map-pin" href="${url}" target="_blank" rel="noopener">📍 ${(+lat).toFixed(5)}, ${(+lon).toFixed(5)}</a>`);
}

function showAlert(m) {
  hideCheckin();
  buzz([200, 100, 200]);
  say("alerting", "Alerting your people now.");
  const sent = (m.results || []).map((r) => `${esc(r.to)} · ${esc(r.channel)}: ${esc(r.result)}`).join("<br>") || "No contacts set up. Add them in Setup.";
  $("alertCard").innerHTML = `<h4>Alert sent to ${m.contacts} contact${m.contacts === 1 ? "" : "s"}${m.sent_to ? ` · ${esc(m.sent_to)}` : ""}</h4>
    <div class="small">${esc(m.why)}</div><p>${linkMap(m.message)}</p><div class="small">${sent}</div>`;
  $("alertCard").hidden = false;
}

// ── PIN pad ───────────────────────────────────────────────────────────────

function askPin(title, action) {
  pinAction = action; $("pinTitle").textContent = title; $("pinInput").value = ""; $("pinPad").hidden = false; $("pinInput").focus();
}

// ── review ────────────────────────────────────────────────────────────────

async function loadSessions() {
  $("sessionDetail").hidden = true; $("sessionList").hidden = false;
  const list = await (await fetch("/api/sessions")).json();
  if (!list.length) { $("sessionList").innerHTML = '<p class="small">No sessions yet. Say "Watch me" to start one.</p>'; return; }
  $("sessionList").innerHTML = "";
  for (const s of list) {
    const b = document.createElement("button");
    b.className = "session-row";
    const level = s.worst >= 0.7 ? "urgent" : s.worst >= 0.45 ? "concern" : s.worst >= 0.2 ? "watch" : "none";
    b.innerHTML = `<span><b>${new Date(s.started * 1000).toLocaleString()}</b><br><span class="small">${s.segments} moments · ${s.flagged} marked · ${s.alerts} alerts</span></span><span class="worst lv-${level}"></span>`;
    b.onclick = () => openSession(s.id);
    $("sessionList").append(b);
  }
}

async function openSession(id) {
  const s = await (await fetch(`/api/sessions/${id}`)).json();
  $("sessionList").hidden = true; $("sessionDetail").hidden = false;
  $("detailTitle").textContent = new Date((s.events[0]?.t || 0) * 1000).toLocaleString();
  $("chainBadge").className = "chain " + (s.chain.ok ? "ok" : "bad");
  $("chainBadge").textContent = s.chain.ok ? `✓ untouched · ${s.chain.lines} lines hash-chained` : `✗ altered at line ${s.chain.broken_at}`;
  $("summary").innerHTML = '<div class="actions"><button class="secondary" id="summarize">Summarise</button>'
    + '<button class="ai" id="sessionNoticeBtn">Was this harassment?</button></div>';
  $("sessionNotice").innerHTML = "";
  $("summarize").onclick = async () => {
    $("summary").textContent = "Summarising…";
    $("summary").textContent = (await (await fetch(`/api/sessions/${id}/summary`)).json()).summary;
  };
  $("sessionNoticeBtn").onclick = async () => {
    const who = prompt("Who was this? A name only you'll recognise (optional).") ?? "";
    $("sessionNotice").innerHTML = '<p class="small">Checking the transcript…</p>';
    const r = await fetch(`/api/notice/session/${id}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ who }) });
    const out = await r.json();
    if (!r.ok) { $("sessionNotice").innerHTML = `<p class="small">${esc(out.detail)}</p>`; return; }
    noticePage = out;
    $("sessionNotice").innerHTML = reviewHtml(out.record);
  };
  const rows = [...s.segments.map((x) => ({ ...x, _seg: true })), ...s.events].sort((a, b) => a.t - b.t);
  const list = $("detail"); list.innerHTML = "";
  for (const r of rows) {
    if (r._seg) { addSegment(list, r, false); continue; }
    addEvent(list, eventHtml(id, r), r.kind, false, r.t);
  }
  applyFilter();
}

function eventHtml(id, e) {
  switch (e.kind) {
    case "clip": return `Audio kept (${e.seconds} s, sha256 ${esc(e.sha256.slice(0, 12))}…)<audio controls preload="none" src="/api/sessions/${id}/clips/${encodeURIComponent(e.file)}"></audio>`;
    case "decision": return decisionText(e);
    case "alert": return `<b>Alert sent</b>: ${esc(e.detail)}<br>${linkMap(e.message)}`;
    case "location_update": return `<b>Location update sent</b><br>${linkMap(e.message)}`;
    default: return `<b>${esc(e.kind.replace(/_/g, " "))}</b>${e.detail ? ": " + esc(e.detail) : ""}`;
  }
}

function applyFilter() {
  const only = $("onlyMarked").checked;
  for (const li of $("detail").children) {
    li.hidden = only && li.classList.contains("seg") && li.dataset.level === "none";
  }
}

// ── notice ────────────────────────────────────────────────────────────────

let noticePage = null, sayMic = null, sayTimer = null, lastSessionReview = null;
const MATCH_HEAD = {
  none: "Nothing here matches the usual descriptions of harassment.",
  some: "Parts of this match what harassment policies describe.",
  clear: "This matches what harassment policies describe.",
};
const localStamp = (d = new Date()) => new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
const prettyDate = (w) => new Date(w.length > 10 ? w : w + "T00:00").toLocaleString([], { dateStyle: "medium", ...(w.length > 10 ? { timeStyle: "short" } : {}) });

function reviewHtml(rec) {
  const r = rec.review, types = noticePage?.types || {};
  const head = `<div class="small">${esc(prettyDate(rec.when))}${rec.who ? " · " + esc(rec.who) : ""}${rec.where ? " · " + esc(rec.where) : ""}</div>`;
  if (!r && rec.pending) return `<div class="card nt-result">${head}<div class="nt-head">Saved to your record.</div><p class="small">No connection right now. It will be checked automatically when you're back online.</p></div>`;
  if (!r) return `<div class="card nt-result">${head}<div class="nt-head">Saved to your record.</div><p class="small">Checking it needs Muse Spark, which isn't set up on this server.</p></div>`;
  if (r.error) return `<div class="card nt-result">${head}<div class="nt-head">Saved to your record.</div><p class="small">The check didn't finish (${esc(r.error)}). Try again later.</p></div>`;
  // One quote can match several types: show it once, with a label for each.
  const byQuote = new Map();
  for (const m of r.moments) {
    if (!byQuote.has(m.quote)) byQuote.set(m.quote, []);
    byQuote.get(m.quote).push(m);
  }
  const moments = [...byQuote].map(([quote, ms]) => {
    const ts = ms.map((m) => ({ ...(types[m.type] || { label: m.type }), why: m.why }));
    const groups = noticePage?.groups || {};
    const means = ts.map((t) => `<p><b>${esc(t.label)}</b>${t.group ? ` <span class="small">(${esc(groups[t.group] || "")})</span>` : ""}. ${esc(t.plain || "")}${t.source ? ` <a href="${esc(t.source.url)}" target="_blank" rel="noopener">${esc(t.source.name)}</a>` : ""}</p>`).join("");
    return `<div class="nt-moment">${ts.map((t) => `<span class="chip">${esc(t.label)}</span>`).join("")}<blockquote>“${esc(quote)}”</blockquote>
      ${ts.map((t) => `<div class="small">${esc(t.why)}</div>`).join("")}<details><summary>What this means</summary>${means}</details></div>`;
  }).join("");
  const res = r.match === "none" ? "" : [...(noticePage?.resources?.[rec.setting] || []), ...(noticePage?.resources?.any || [])];
  // A live session knows nothing about who or where: ask, so it counts toward the right pattern.
  const ask = rec.source === "session" && !rec.who && r.match !== "none" ? `<div class="nt-label" data-id="${esc(rec.id)}">
      <b>Who was this?</b> <span class="small">Add it so this counts toward the right pattern.</span>
      <div class="nt-grid"><label>Who<input data-k="who" placeholder="e.g. Prof. R"></label>
        <label>Setting<select data-k="setting"><option value="school">School</option><option value="work">Work</option><option value="online">Online</option><option value="other">Somewhere else</option></select></label>
        <label>Where<input data-k="where" placeholder="e.g. office hours"></label></div>
      <button class="secondary" type="button">Save</button></div>` : "";
  return `<div class="card nt-result ${r.match}">${head}<div class="nt-head">${MATCH_HEAD[r.match]}</div>${ask}
    ${r.summary ? `<p>${esc(r.summary)}</p>` : ""}${moments}
    ${res.length ? `<div class="nt-note"><b>If you want to do something about it</b> (only if you want to):<ul class="nt-res">${res.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>` : ""}
    <div class="nt-note">${esc(noticePage?.disclaimer || "")}</div></div>`;
}

function renderNotice() {
  const p = noticePage;
  $("ntPatterns").hidden = !p.patterns.length;
  $("ntPatterns").innerHTML = `<h3>Patterns</h3>` + p.patterns.map((x) => `<div class="nt-person">
      <span class="nt-count">${x.times}×</span><b>${esc(x.who)}</b>
      <span class="small">${x.first === x.last ? esc(prettyDate(x.first)) : `${esc(prettyDate(x.first))} – ${esc(prettyDate(x.last))}`}</span>
      <div>${x.types.map((t) => `<span class="chip">${esc(t.label)}${t.count > 1 ? " ×" + t.count : ""}</span>`).join("")}</div></div>`).join("")
    + (p.patterns.some((x) => x.repeated) ? `<p class="nt-note">${esc(p.frequency)}</p>` : "");
  $("ntHistory").innerHTML = p.records.length ? "" : '<p class="small">Nothing yet.</p>';
  for (const rec of [...p.records].reverse()) {
    const b = document.createElement("button");
    b.className = "nt-row";
    const m = rec.review?.match || "none";
    const labels = (rec.review?.moments || []).map((x) => p.types[x.type]?.label).filter((v, i, a) => v && a.indexOf(v) === i);
    b.innerHTML = `<span><b>${esc(prettyDate(rec.when))}</b>${rec.who ? " · " + esc(rec.who) : ""}<br>
      <span class="small">${rec.source === "session" ? "recorded session" : "your account"}${labels.length ? " · " + esc(labels.join(", ")) : ""}</span></span><span class="nt-dot ${m}"></span>`;
    b.onclick = () => { $("ntResult").innerHTML = reviewHtml(rec); $("ntResult").scrollIntoView({ behavior: "smooth" }); };
    $("ntHistory").append(b);
  }
  $("ntChain").textContent = p.records.length ? (p.chain.ok ? `✓ ${p.records.length} entries, unaltered (hash-chained)` : "✗ the record was altered") : "";
}

async function saveLabel(e) {
  const box = e.target.closest(".nt-label");
  if (!box || e.target.tagName !== "BUTTON") return;
  const body = {}; box.querySelectorAll("[data-k]").forEach((i) => (body[i.dataset.k] = i.value));
  const r = await fetch(`/api/notice/${box.dataset.id}/label`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const out = await r.json();
  if (!r.ok) { box.querySelector(".small").textContent = out.detail || "Couldn't save."; return; }
  noticePage = out; renderNotice();
  box.closest(".nt-result").outerHTML = reviewHtml(out.record);
}

async function loadNotice() {
  noticePage = await (await fetch("/api/notice")).json();
  if (!$("ntWhen").value) $("ntWhen").value = localStamp();
  renderNotice();
  if (lastSessionReview) { $("ntResult").innerHTML = reviewHtml(lastSessionReview); lastSessionReview = null; }
}

async function checkNotice(audio) {
  const body = { text: $("ntText").value, setting: $("ntSetting").value, who: $("ntWho").value, where: $("ntWhere").value,
                 when: $("ntWhen").value, audio };
  $("ntCheck").disabled = $("ntSay").disabled = true;
  $("ntMsg").textContent = audio ? "Transcribing and checking…" : "Checking…";
  try {
    const r = await fetch("/api/notice/debrief", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const out = await r.json();
    if (!r.ok) { $("ntMsg").textContent = out.detail; return; }
    noticePage = out; renderNotice();
    $("ntResult").innerHTML = reviewHtml(out.record);
    $("ntText").value = ""; $("ntMsg").textContent = "Saved to your record.";
    $("ntResult").scrollIntoView({ behavior: "smooth" });
  } finally { $("ntCheck").disabled = $("ntSay").disabled = false; }
}

async function toggleSay() {
  if (sayMic) {
    const pcm = sayMic.take(); await sayMic.stop(); sayMic = null; clearInterval(sayTimer);
    $("ntSay").innerHTML = '<svg viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg>Say it';
    await checkNotice(bufferToB64(pcm));
    return;
  }
  if (mic) { $("ntMsg").textContent = "Turn off listening on the Watch tab first."; return; }
  try { sayMic = new Mic(() => {}, 600); await sayMic.start(); }
  catch (e) { sayMic = null; $("ntMsg").textContent = "Microphone blocked: " + e.message; return; }
  const t0 = Date.now();
  const tick = () => { const s = Math.round((Date.now() - t0) / 1000); $("ntSay").textContent = `■ Done (${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")})`; };
  tick(); sayTimer = setInterval(tick, 1000);
  $("ntMsg").textContent = "Listening. Say what happened, then tap Done. The audio isn't kept, only the words.";
}

// ── setup ─────────────────────────────────────────────────────────────────

const RELATIONS = { "": "Relationship…", mom: "Mom", dad: "Dad", sister: "Sister", brother: "Brother", partner: "Partner",
                    friend: "Friend", roommate: "Roommate", other: "Other" };
const FAMILY = ["mom", "dad", "sister", "brother"];

function contactRow(c = {}) {
  const div = document.createElement("div");
  div.className = "contact";
  const options = Object.entries(RELATIONS).map(([k, v]) => `<option value="${k}" ${k === (c.relation || "") ? "selected" : ""}>${v}</option>`).join("");
  div.innerHTML = `<label>Name<input data-k="name" value="${esc(c.name)}"></label>
    <label>Relationship<select data-k="relation">${options}</select></label>
    <label>Phone <span class="muted">(+country code)</span><input data-k="phone" inputmode="tel" value="${esc(c.phone)}" placeholder="+12125551234"></label>
    <label>Email<input data-k="email" type="email" value="${esc(c.email)}"></label>
    <label class="switch-row"><span><b>Default</b> <span class="muted">· alerts go to this person</span></span><input data-k="default" type="checkbox" class="switch" ${c.default ? "checked" : ""}></label>
    <label class="switch-row"><span>Also call this number</span><input data-k="call" type="checkbox" class="switch" ${c.call === false ? "" : "checked"}></label>
    <button type="button" class="link remove">Remove</button>`;
  div.querySelector(".remove").onclick = () => { div.remove(); showAlertRoute(); };
  div.addEventListener("input", showAlertRoute);
  div.addEventListener("change", showAlertRoute);
  $("contacts").append(div);
  showAlertRoute();
}

function readContacts() {
  return [...document.querySelectorAll(".contact")].map((row) => {
    const c = {};
    row.querySelectorAll("[data-k]").forEach((i) => (c[i.dataset.k] = i.type === "checkbox" ? i.checked : i.value));
    return c;
  });
}

// The same rule as messenger.recipients on the server: defaults, else family, else everyone listed.
function showAlertRoute() {
  const list = readContacts().filter((c) => c.phone || c.email);
  const label = (c) => esc(c.name || c.phone || c.email) + (c.relation ? ` (${RELATIONS[c.relation]})` : "");
  const defaults = list.filter((c) => c.default), family = list.filter((c) => FAMILY.includes(c.relation));
  const [who, why] = defaults.length ? [defaults, "your default contacts"]
    : family.length ? [family, "no default set, so your family"]
    : [list, "no default or family set, so everyone listed"];
  $("alertRoute").innerHTML = list.length
    ? `<b>Alerts go to:</b> ${who.map(label).join(", ")} <span class="small">· ${why}</span>`
    : `<b>No one to alert yet.</b> <span class="small">Add at least one contact with a phone number or email.</span>`;
}

// Android Chrome lets a page open the phone's contact picker; iPhones don't, so the button stays hidden there.
function e164(raw) {
  const plus = raw.trim().startsWith("+"), digits = raw.replace(/\D/g, "");
  if (plus) return "+" + digits;
  if (digits.length === 10) return "+1" + digits;                  // a US number without the country code
  if (digits.length === 11 && digits.startsWith("1")) return "+" + digits;
  return raw.trim();
}

async function pickContacts() {
  try {
    const picked = await navigator.contacts.select(["name", "tel", "email"], { multiple: true });
    for (const p of picked) {
      const name = p.name?.[0] || "";
      const guess = Object.keys(RELATIONS).find((k) => k && new RegExp(`\\b(${k}|${k === "mom" ? "mother|mum" : k === "dad" ? "father" : k})\\b`, "i").test(name));
      const empty = [...document.querySelectorAll(".contact")].find((row) => ![...row.querySelectorAll("input:not([type=checkbox])")].some((i) => i.value));
      empty?.remove();
      contactRow({ name, phone: p.tel?.[0] ? e164(p.tel[0]) : "", email: p.email?.[0] || "", relation: guess || "" });
    }
  } catch (e) { $("profileMsg").textContent = "Couldn't open your contacts: " + e.message; }
}

function fillProfile() {
  const f = $("profileForm");
  for (const k of ["name", "sos_phrase", "duress_phrase"]) f.elements[k].value = profile[k] || "";
  $("contacts").innerHTML = "";
  (profile.contacts?.length ? profile.contacts : [{}]).forEach(contactRow);
  showEnrollState();
}

function showEnrollState() {
  $("voiceSaved").hidden = !profile.enrolled;
  $("stamp").hidden = !profile.enrolled;
  if (profile.enrolled) {
    drawPrint($("enrollPrint"), profile.voice_signature);
    $("voiceId").textContent = profile.voice_id; $("voiceWhen").textContent = profile.enrolled_at || "";
    $("voiceMsg").textContent = "";
    $("recSample").textContent = "Record again";
  } else {
    drawScan($("enrollPrint"), 0, 0, 0);
    $("voiceMsg").textContent = profile.needs_reenroll
      ? "Watch Me now uses a more accurate voice model. Please record your line again." : "";
    $("recSample").textContent = "Record my voice";
  }
}

async function saveProfile(e) {
  e.preventDefault();
  const f = $("profileForm");
  const contacts = readContacts();
  const body = { name: f.elements.name.value, pin: f.elements.pin.value, sos_phrase: f.elements.sos_phrase.value,
                 duress_phrase: f.elements.duress_phrase.value, contacts };
  const r = await fetch("/api/profile", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const out = await r.json();
  if (!r.ok) { $("profileMsg").textContent = out.detail; return; }
  profile = out; f.elements.pin.value = ""; $("profileMsg").textContent = "Saved.";
}

const ENROLL_SECONDS = 6;

// Record while the scanner animates with the live loudness and a ring fills with the time left.
async function recordWithScan(seconds) {
  let level = 0, running = true;
  const t0 = performance.now(), canvas = $("enrollPrint");
  const frame = (now) => {
    if (!running) return;
    const t = (now - t0) / 1000;
    drawScan(canvas, t, level, Math.min(1, t / seconds));
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
  try { return await recordOnce(seconds, (rms) => (level = level * 0.7 + rms * 0.3)); }
  finally { running = false; }
}

async function recordSample() {
  if (mic) { $("voiceMsg").textContent = "Turn off listening on the Watch tab first."; return; }
  profile.enrolled = false; showEnrollState();
  const card = document.querySelector(".enroll-card");
  $("recSample").disabled = true; $("recSample").textContent = "Listening…";
  $("voiceMsg").textContent = "Say the line now.";
  card.classList.add("recording");
  let sample;
  try { sample = bufferToB64(await recordWithScan(ENROLL_SECONDS)); }
  catch (e) { $("voiceMsg").textContent = "Microphone blocked: " + e.message; return; }
  finally { card.classList.remove("recording"); $("recSample").disabled = false; }

  $("recSample").textContent = "Saving…"; $("voiceMsg").textContent = "Making your voiceprint…";
  const r = await fetch("/api/enroll", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ samples: [sample] }) });
  const out = await r.json();
  if (!r.ok) { showEnrollState(); $("voiceMsg").textContent = out.detail; return; }
  profile = { ...profile, ...out };
  if (out.strict_threshold) thresholds = { start: out.threshold, strict: out.strict_threshold };
  await animateReveal($("enrollPrint"), out.voice_signature);
  showEnrollState();
  $("voiceMsg").textContent = out.advice || "";
  renderOwnerPrint();
  toast("ok", `<span class="big-icon">🔒</span><b>Voiceprint saved.</b> Only your voice can stop Watch Me now.`);
}

async function testVoice() {
  if (mic) { $("voiceMsg").textContent = "Turn off listening on the Watch tab first."; return; }
  $("voiceMsg").textContent = "Say anything for 3 seconds…";
  const pcm = await recordWithScan(3);
  const r = await fetch("/api/voice-check", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ sample: bufferToB64(pcm) }) });
  const out = await r.json();
  if (!r.ok) { $("voiceMsg").textContent = out.detail; showEnrollState(); return; }
  const canvas = $("enrollPrint");
  drawPrint(canvas, profile.voice_signature, { color: cssVar("--print-ghost"), alpha: 0.5 });
  drawPrint(canvas, out.signature, { color: matchColor(out.match), clear: false });
  const pct = Math.round(out.match * 100);
  $("voiceMsg").textContent = out.strict ? `Match ${pct}%: that's you. You can start and stop Watch Me.`
    : out.owner ? `Match ${pct}%: enough to start, not enough to stop (needs ${Math.round(out.strict_threshold * 100)}%). Speak a little closer.`
    : `Match ${pct}%: not recognised as you. This voice can't start or stop Watch Me.`;
  setTimeout(showEnrollState, 6000);
}

function renderServices(s) {
  const names = { muse_spark: "Analyst (live)", reviewer: "Notice reviewer", writer: "Alerts and summaries", decider: "Decider",
                  sms_and_calls: "SMS and calls", email: "Email", whisper: "Speech-to-text (live)", analyst_speech: "What the Analyst reads", debrief_speech: "Speech-to-text (your account)",
                  recording_rule: "Recording rule" };
  const short = (v) => String(v).replace(/^https?:\/\//, "");
  $("services").innerHTML = Object.entries(s).map(([k, v]) => `<dt>${names[k] || k}</dt><dd>${esc(short(v))}</dd>`).join("");
}

// ── wiring ────────────────────────────────────────────────────────────────

document.querySelectorAll(".tab").forEach((t) => (t.onclick = () => {
  document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x === t));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === "tab-" + t.dataset.tab));
  if (t.dataset.tab === "review") loadSessions();
  if (t.dataset.tab === "setup") fillProfile();
  if (t.dataset.tab === "notice") loadNotice();
}));
document.querySelectorAll("#modeSwitch button").forEach((b) => (b.onclick = () => sendJson({ type: "mode", mode: b.dataset.mode })));
$("ntCheck").onclick = () => checkNotice();
$("ntSay").onclick = toggleSay;
$("retryPending").onclick = retryPending;
$("ntResult").onclick = saveLabel;
$("sessionNotice").onclick = saveLabel;
$("micButton").onclick = toggleMic;
// "I'm OK" is voice only: a tap could come from whoever holds the phone. "Get help now" is the one button.

// Press and hold the orb to start listening: a ring fills for 0.7 s; letting go early cancels.
function holdOrb() {
  const orb = $("orb");
  let timer = null;
  const can = () => !mic && state !== "watching";
  const start = (e) => {
    if (!can()) return;
    e.preventDefault();
    orb.classList.remove("held"); orb.classList.add("holding"); buzz(8);
    timer = setTimeout(() => { timer = null; orb.classList.replace("holding", "held"); buzz(30); toggleMic(); }, 700);
  };
  const cancel = () => { if (timer) { clearTimeout(timer); timer = null; } orb.classList.remove("holding"); };
  orb.addEventListener("pointerdown", start);
  orb.addEventListener("pointerup", cancel);
  orb.addEventListener("pointerleave", cancel);
  orb.addEventListener("pointercancel", cancel);
  orb.addEventListener("keydown", (e) => { if ((e.key === "Enter" || e.key === " ") && can()) { e.preventDefault(); toggleMic(); } });
}
holdOrb();
$("getHelp").onclick = () => sendJson({ type: "checkin_answer", ok: false });
$("pinStop").onclick = () => askPin("PIN to stop", (pin) => sendJson({ type: "stop_pin", pin }));
$("pinStart").onclick = () => askPin("PIN to start", (pin) => sendJson({ type: "start_pin", pin }));
$("pinOk").onclick = () => { $("pinPad").hidden = true; pinAction?.($("pinInput").value); };
$("pinCancel").onclick = () => ($("pinPad").hidden = true);
$("backToList").onclick = loadSessions;
$("onlyMarked").onchange = applyFilter;
$("profileForm").onsubmit = saveProfile;
$("addContact").onclick = () => contactRow();
$("pickContacts").hidden = !("contacts" in navigator && "ContactsManager" in window);
$("pickContacts").onclick = pickContacts;
$("recSample").onclick = recordSample;
$("testVoice").onclick = testVoice;
connect();
