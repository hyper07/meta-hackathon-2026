// The app's one connection to the server, shared by every screen: the WebSocket, the microphone stream,
// and what the agents last said. The protocol is the web page's (app/static/app.js): binary frames of
// 4 s of 16 kHz PCM up, JSON events down.
import {
  createAudioPlayer,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioStream,
  type AudioStreamBuffer,
} from 'expo-audio';
import * as Location from 'expo-location';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Vibration } from 'react-native';

import { feel } from './feel';
import { Chunker, int16Bytes, level as loudness, resampleInt16, toMono, TARGET_RATE } from './pcm';
import { loadServerUrl, saveServerUrl, wsUrl } from './server';

export type Msg = { type: string; [key: string]: any };
export type Line = Msg & { key: string };

export type CheckIn = { reason: string; timeout: number; urgent: boolean; startedAt: number };
export type Toast = { id: number; kind: 'ok' | 'bad' | 'info'; title: string; text: string };

const COMMANDS: Record<string, string> = {
  start: '“Watch me”', stop: '“Stop watching”', ok: '“I\u2019m OK”', not_ok: '“I\u2019m not OK”', sos: 'SOS phrase', duress: 'Duress phrase',
};
const AFTER: Record<string, string> = {
  start: 'Recording is locked to your voice.', stop: 'Stopped.', ok: 'Glad you\u2019re OK.',
  not_ok: 'Alerting your people.', sos: 'Alerting your people now.',
};

const PROMPTS = {
  'are-you-ok': require('../../assets/voice/are-you-ok.wav'),
  alerting: require('../../assets/voice/alerting.wav'),
};

type WatchMe = {
  serverUrl: string;
  setServerUrl: (url: string) => Promise<void>;
  connected: boolean;
  state: 'standby' | 'watching';
  mode: 'watch' | 'notice';
  profile: Msg;
  services: Record<string, string>;
  voice: Msg | null;
  lines: Line[];
  banner: string;
  alert: Msg | null;
  checkin: CheckIn | null;
  offline: boolean;
  pending: number;
  listening: boolean;
  level: number;
  lastReview: Msg | null;
  toast: Toast | null;
  /** When another voice was last refused, so the voice lock can shake. */
  refusedAt: number;
  setProfile: (p: Msg) => void;
  startListening: () => Promise<void>;
  stopListening: () => Promise<void>;
  record: (seconds: number) => Promise<Int16Array>;
  startCapture: () => Promise<void>;
  stopCapture: () => Promise<Int16Array>;
  send: (message: Msg) => void;
  setMode: (mode: 'watch' | 'notice') => void;
  answerCheckin: (ok: boolean, pin?: string) => void;
  dismissBanner: () => void;
};

const Ctx = createContext<WatchMe | null>(null);

export function useWatchMe(): WatchMe {
  const value = useContext(Ctx);
  if (!value) throw new Error('useWatchMe outside WatchMeProvider');
  return value;
}

type Consumer = { kind: 'listen' } | { kind: 'capture'; chunker: Chunker; until?: number; done?: (s: Int16Array) => void };

export function WatchMeProvider({ children }: { children: ReactNode }) {
  const [serverUrl, setUrl] = useState('');
  const [connected, setConnected] = useState(false);
  const [state, setState] = useState<'standby' | 'watching'>('standby');
  const [mode, setModeState] = useState<'watch' | 'notice'>('watch');
  const [profile, setProfile] = useState<Msg>({ type: 'profile' });
  const [services, setServices] = useState<Record<string, string>>({});
  const [voice, setVoice] = useState<Msg | null>(null);
  const [lines, setLines] = useState<Line[]>([]);
  const [banner, setBanner] = useState('');
  const [alert, setAlert] = useState<Msg | null>(null);
  const [checkin, setCheckin] = useState<CheckIn | null>(null);
  const [offline, setOffline] = useState(false);
  const [pending, setPending] = useState(0);
  const [listening, setListening] = useState(false);
  const [level, setLevel] = useState(0);
  const [lastReview, setLastReview] = useState<Msg | null>(null);
  const [toast, setToast] = useState<Toast | null>(null);
  const [refusedAt, setRefusedAt] = useState(0);

  const ws = useRef<WebSocket | null>(null);
  const consumer = useRef<Consumer | null>(null);
  const chunker = useRef(new Chunker());
  const lastLevelAt = useRef(0);
  const locationSub = useRef<Location.LocationSubscription | null>(null);
  const keyCounter = useRef(0);

  // ── speaking ──────────────────────────────────────────────────────────────
  const say = useCallback((name: keyof typeof PROMPTS) => {
    try {
      const player = createAudioPlayer(PROMPTS[name]);
      player.play();
      setTimeout(() => player.release(), 8000);
    } catch {
      // A prompt that can't play must never break the check-in itself.
    }
  }, []);

  // ── incoming events ───────────────────────────────────────────────────────
  const showToast = useCallback((kind: Toast['kind'], title: string, text: string) => {
    keyCounter.current += 1;
    setToast({ id: keyCounter.current, kind, title, text });
  }, []);

  /** A voice command the gatekeeper accepted or refused: a buzz you can feel, and a toast you can read. */
  const onVoice = useCallback((m: Msg) => {
    setVoice(m);
    if (!m.command || !m.outcome || m.outcome === 'ignored') return;
    const what = COMMANDS[m.command] ?? m.command;
    const pct = Math.round((m.match ?? 0) * 100);
    if (m.outcome === 'accepted') {
      feel.verified();
      showToast('ok', `${what}: verified as you (${pct}%)`, AFTER[m.command] ?? '');
    } else {
      feel.refused();
      setRefusedAt(Date.now());
      const need = m.command === 'start' ? 70 : 90;
      showToast('bad', `${what} refused`, `Not your voice (${pct}%, needs ${need}%). ${m.command === 'start' ? 'Not started.' : 'Still recording.'}`);
    }
  }, [showToast]);

  const addLine = useCallback((m: Msg) => {
    keyCounter.current += 1;
    const line = { ...m, key: m.seg ? `seg-${m.seg}` : `ev-${keyCounter.current}` };
    setLines((prev) => [line, ...prev].slice(0, 80));
  }, []);

  const handle = useCallback((m: Msg) => {
    switch (m.type) {
      case 'hello':
        setProfile(m.profile ?? {});
        setServices(m.services ?? {});
        setState(m.state);
        if (m.mode) setModeState(m.mode);
        setOffline(!!m.offline || (m.pending ?? 0) > 0);
        setPending(m.pending ?? 0);
        break;
      case 'state':
        setState(m.state);
        if (m.mode) setModeState(m.mode);
        if (m.notice) setBanner(m.notice);
        if (m.state === 'watching') { setLines([]); setAlert(null); }
        break;
      case 'mode': setModeState(m.mode); break;
      case 'notice': setBanner(m.text); break;
      case 'voice': if (m.match != null) onVoice(m); break;
      case 'segment': addLine(m); break;
      case 'update':
        setLines((prev) => prev.map((l) => (l.key === `seg-${m.seg}` ? { ...l, ...m, key: l.key } : l)));
        break;
      case 'decision': case 'noted': addLine(m); break;
      case 'checkin':
        setCheckin({ reason: m.reason ?? '', timeout: m.timeout ?? 30, urgent: !!m.urgent, startedAt: Date.now() });
        feel.attention();
        Vibration.vibrate([0, 400, 200, 400, 200, 400]);
        say('are-you-ok');
        break;
      case 'checkin_result':
        setCheckin(null);
        setBanner(m.ok ? 'Thanks. Still watching.' : 'Alerting your people now.');
        break;
      case 'alert':
        setCheckin(null);
        setAlert(m);
        feel.refused();
        say('alerting');
        break;
      case 'offline':
        setOffline(true); setPending(m.pending ?? 0);
        if (m.text) setBanner(m.text);
        break;
      case 'online':
        setOffline((m.pending ?? 0) > 0); setPending(m.pending ?? 0);
        showToast('ok', 'Back online', `${m.done} moment${m.done === 1 ? '' : 's'} analyzed and added to your record.`);
        break;
      case 'notice_review': setLastReview(m.record); showToast('info', 'Your review is ready', 'Open the Notice tab.'); break;
    }
  }, [addLine, say, onVoice, showToast]);

  // ── the socket ────────────────────────────────────────────────────────────
  useEffect(() => { loadServerUrl().then(setUrl); }, []);

  useEffect(() => {
    if (!serverUrl) return;
    let closed = false;
    let backoff = 500;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const open = () => {
      const socket = new WebSocket(wsUrl(serverUrl));
      socket.binaryType = 'arraybuffer';
      socket.onopen = () => { backoff = 500; setConnected(true); };
      socket.onmessage = (e) => { if (typeof e.data === 'string') handle(JSON.parse(e.data)); };
      socket.onclose = () => {
        setConnected(false);
        if (!closed) { timer = setTimeout(open, backoff); backoff = Math.min(backoff * 2, 8000); }
      };
      socket.onerror = () => socket.close();
      ws.current = socket;
    };
    open();
    return () => { closed = true; clearTimeout(timer); ws.current?.close(); ws.current = null; };
  }, [serverUrl, handle]);

  const send = useCallback((message: Msg) => {
    if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(JSON.stringify(message));
  }, []);

  // ── the microphone ────────────────────────────────────────────────────────
  const onBuffer = useCallback((buffer: AudioStreamBuffer) => {
    const raw = toMono(new Int16Array(buffer.data), buffer.channels);
    const samples = resampleInt16(raw, buffer.sampleRate, TARGET_RATE);
    const now = Date.now();
    if (now - lastLevelAt.current > 120) { lastLevelAt.current = now; setLevel(loudness(samples)); }
    const c = consumer.current;
    if (!c) return;
    if (c.kind === 'listen') {
      for (const chunk of chunker.current.push(samples)) {
        if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(int16Bytes(chunk));
      }
    } else {
      c.chunker.push(samples);
      if (c.until && now >= c.until && c.done) {
        const done = c.done;
        consumer.current = null;
        done(c.chunker.flush());
      }
    }
  }, []);

  // useAudioStream keeps the first options it's given, so route through a ref that always holds the latest.
  const onBufferRef = useRef(onBuffer);
  useEffect(() => { onBufferRef.current = onBuffer; }, [onBuffer]);
  const { stream } = useAudioStream({
    sampleRate: TARGET_RATE, channels: 1, encoding: 'int16',
    onBuffer: (b) => onBufferRef.current(b),
  });

  const ensureMic = useCallback(async () => {
    const { granted } = await requestRecordingPermissionsAsync();
    if (!granted) throw new Error('Microphone access is off. Turn it on in Settings to use Watch Me.');
    // playAndRecord, kept alive in the background and under the silent switch, so "Are you OK?" is heard.
    await setAudioModeAsync({
      allowsRecording: true, allowsBackgroundRecording: true, playsInSilentMode: true, shouldPlayInBackground: true,
    });
    if (!stream.isStreaming) await stream.start();
  }, [stream]);

  const releaseMicIfIdle = useCallback(() => {
    if (!consumer.current && stream.isStreaming) stream.stop();
  }, [stream]);

  const startListening = useCallback(async () => {
    await ensureMic();
    chunker.current = new Chunker();
    consumer.current = { kind: 'listen' };
    setListening(true);
    // Location goes with an alert, if she allows it; foreground only.
    try {
      const { granted } = await Location.requestForegroundPermissionsAsync();
      if (granted && !locationSub.current) {
        locationSub.current = await Location.watchPositionAsync(
          { accuracy: Location.Accuracy.Balanced, timeInterval: 30000, distanceInterval: 25 },
          (p) => send({ type: 'location', lat: p.coords.latitude, lon: p.coords.longitude, accuracy: p.coords.accuracy }),
        );
      }
    } catch {
      // Watch Me works without location; the alert just won't carry a map link.
    }
  }, [ensureMic, send]);

  const stopListening = useCallback(async () => {
    consumer.current = null;
    setListening(false);
    locationSub.current?.remove();
    locationSub.current = null;
    releaseMicIfIdle();
  }, [releaseMicIfIdle]);

  /** A fixed-length recording, for enrollment. Pauses listening while it runs. */
  const record = useCallback(async (seconds: number) => {
    await ensureMic();
    return new Promise<Int16Array>((resolve) => {
      consumer.current = { kind: 'capture', chunker: new Chunker(), until: Date.now() + seconds * 1000,
                           done: (s) => { resolve(s); releaseMicIfIdle(); } };
    });
  }, [ensureMic, releaseMicIfIdle]);

  /** An open-ended recording the owner ends with a tap, for a spoken Notice account. */
  const startCapture = useCallback(async () => {
    await ensureMic();
    consumer.current = { kind: 'capture', chunker: new Chunker() };
  }, [ensureMic]);

  const stopCapture = useCallback(async () => {
    const c = consumer.current;
    consumer.current = null;
    releaseMicIfIdle();
    return c && c.kind === 'capture' ? c.chunker.flush() : new Int16Array(0);
  }, [releaseMicIfIdle]);

  const value = useMemo<WatchMe>(() => ({
    serverUrl,
    setServerUrl: async (url) => setUrl(await saveServerUrl(url)),
    connected, state, mode, profile, services, voice, lines, banner, alert, checkin, offline, pending,
    listening, level, lastReview, toast, refusedAt, setProfile,
    startListening, stopListening, record, startCapture, stopCapture, send,
    setMode: (m) => send({ type: 'mode', mode: m }),
    answerCheckin: (ok, pin) => send({ type: 'checkin_answer', ok, pin }),
    dismissBanner: () => setBanner(''),
  }), [serverUrl, connected, state, mode, profile, services, voice, lines, banner, alert, checkin, offline, pending,
       listening, level, lastReview, toast, refusedAt, startListening, stopListening, record, startCapture, stopCapture, send]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
