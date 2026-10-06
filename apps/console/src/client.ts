import { reactive } from "vue";
import { App as NativeApp } from "@capacitor/app";
import { Capacitor } from "@capacitor/core";
import { SPEC, validate, type CommandType } from "../../../contracts/protocol";
import { LeaseGuard } from "./lease";
export type Status = {
  software_version?: string;
  parameter_version?: string;
  hardware_profile?: string;
  physical_release?: boolean;
  device_id: string;
  session_id: string;
  device_ms: number;
  frame_id: number;
  source: string;
  state: string;
  enabled: boolean;
  fault: string | null;
  owner: string | null;
  lease_remaining_ms: number;
  v_m_s: number;
  yaw_rad_s: number;
  target_v_m_s: number;
  head: {
    yaw_rad: number;
    pitch_rad: number;
    feedback: string;
    inhibited: boolean;
  };
  expression: string;
  camera: {
    mode: string;
    upload_allowed: boolean;
    selected_target: string | null;
    observation: null | {
      target_id: string;
      uncertain: boolean;
      confidence: number;
      frame_id: number;
      boxes: number[][];
    };
    age_ms: number | null;
  };
  active: string | null;
  volume: number;
  wake: { status: string; phrase: string };
  events: Record<string, unknown>[];
  measurements: Record<string, number | null>;
};
type Result = {
  command_id: string;
  status: string;
  reason: string;
  type: string;
  data?: unknown;
};
type Identity = { token: string; client_id: string; permissions: string[] };
export const ui = reactive({
  base:
    location.protocol === "https:" && location.hostname !== "localhost"
      ? location.origin
      : "http://127.0.0.1:8765",
  connected: false,
  status: null as Status | null,
  identity: null as Identity | null,
  received: 0,
  now: 0,
  results: [] as Result[],
  notice: "",
  voiceText: "",
  voiceSource: "MOCK",
  playbackRms: 0,
  voiceMetrics: {} as Record<string, unknown>,
  costs: {} as Record<string, unknown>,
  statistics: {} as Record<string, unknown>,
});
let ws: WebSocket | null = null,
  seq = 0,
  timer: ReturnType<typeof setInterval> | null = null,
  driveTimer: ReturnType<typeof setInterval> | null = null;
let lastTransport = 0,
  previousArrival = 0,
  drops = 0,
  timeouts = 0;
const latencies: number[] = [],
  jitters: number[] = [],
  sent = new Map<string, number>();
function summarize(v: number[]) {
  const a = [...v].sort((x, y) => x - y);
  return {
    n: a.length,
    p50_ms: a[Math.floor((a.length - 1) * 0.5)] ?? null,
    p95_ms: a[Math.floor((a.length - 1) * 0.95)] ?? null,
    p99_ms: a[Math.floor((a.length - 1) * 0.99)] ?? null,
    max_ms: a.at(-1) ?? null,
  };
}
function stats() {
  ui.statistics = {
    source: "HOST_BROWSER",
    rtt: summarize(latencies),
    telemetry_jitter: summarize(jitters),
    transport_dropped: drops,
    command_timeouts: timeouts,
    hardware_compute_max: "NOT_TESTED",
  };
}
const waiting = new Map<string, (r: Result) => void>();
let audioContext: AudioContext | null = null,
  playing: AudioBufferSourceNode | null = null,
  playbackTimer: ReturnType<typeof setInterval> | null = null;
let playbackEpoch = 0;
export const lease = new LeaseGuard(() => {
  haltDrive();
  void send("STOP_MOTION", {}).catch(() => {});
});
export function stale() {
  return !ui.status || performance.now() - ui.received > 250;
}
export async function api(path: string, body?: unknown) {
  const res = await fetch(ui.base + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      ...(ui.identity ? { Authorization: "Bearer " + ui.identity.token } : {}),
      "Content-Type": "application/json",
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!res.ok) throw Error((await res.text()).slice(0, 150));
  return res.json();
}
export async function pair(code: string) {
  const url = new URL(ui.base);
  if (
    url.protocol !== "https:" &&
    !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)
  )
    throw Error("非本机连接必须使用 HTTPS/WSS");
  ui.identity = await api("/api/pair", { code });
  connect();
}
export function connect() {
  if (!ui.identity) return;
  lease.active = false;
  haltDrive();
  lastTransport = 0;
  previousArrival = 0;
  if (ws) ws.close();
  const next = new WebSocket(ui.base.replace(/^http/, "ws") + "/ws");
  ws = next;
  next.onopen = () => next.send(JSON.stringify({ token: ui.identity!.token }));
  next.onmessage = async (e) => {
    if (ws !== next) return;
    const m = JSON.parse(e.data);
    if (m.type === "telemetry") {
      const now = performance.now();
      if (previousArrival) {
        jitters.push(Math.abs(now - previousArrival - 100));
        if (jitters.length > 256) jitters.shift();
      }
      previousArrival = now;
      if (lastTransport && m.transport_seq > lastTransport + 1)
        drops += m.transport_seq - lastTransport - 1;
      lastTransport = m.transport_seq;
      stats();
      if (ui.status && ui.status.session_id !== m.data.session_id) {
        lease.active = false;
        haltDrive();
        seq = 0;
        waiting.clear();
      }
      ui.status = m.data;
      ui.received = performance.now();
      ui.connected = true;
      for (const event of m.data.events) {
        if (event.kind === "command")
          ui.results = ui.results.map((r) =>
            r.command_id === event.command_id ? { ...r, ...event } : r,
          );
      }
    }
    if (m.type === "result") {
      const r = m.data as Result;
      const start = sent.get(r.command_id);
      if (start !== undefined) {
        latencies.push(performance.now() - start);
        if (latencies.length > 256) latencies.shift();
        sent.delete(r.command_id);
        stats();
      }
      if (r.type !== "HEARTBEAT") ui.results = [r, ...ui.results].slice(0, 40);
      if (r.type === "MEMORY_DELETE" && r.status === "COMPLETED")
        ui.results = ui.results.map((item) =>
          item.type.startsWith("MEMORY_") ? { ...item, data: undefined } : item,
        );
      waiting.get(r.command_id)?.(r);
      waiting.delete(r.command_id);
      if (r.status === "REJECTED" || r.status === "EXPIRED")
        ui.notice = r.reason;
    }
    if (m.type === "voice_audio") {
      ui.voiceText = m.text;
      ui.voiceSource = m.source;
      ui.voiceMetrics = m.metrics;
      await playAudio(m);
    }
    if (m.type === "voice_interrupt") {
      stopAudio();
      for (const id of m.command_ids ?? [])
        next.send(JSON.stringify({ type: "interrupt_ack", command_id: id }));
    }
    if (m.type === "voice_metrics") ui.voiceMetrics = m.data;
  };
  next.onclose = () => {
    if (ws !== next) return;
    ui.connected = false;
    lease.active = false;
    haltDrive();
    stopAudio();
    ui.notice = "连接断开：停止续租；重连后需要重新取得控制权";
  };
  next.onerror = () => {
    ui.notice = "连接失败，请检查服务地址与一次性配对";
  };
  if (timer) clearInterval(timer);
  timer = setInterval(() => {
    ui.now = performance.now();
    if (
      lease.heartbeat(
        !document.hidden && document.hasFocus(),
        ui.connected,
        !stale(),
      )
    )
      void send("HEARTBEAT", {}).catch(() => {});
  }, 100);
}
export function send(
  type: CommandType,
  params: Record<string, unknown>,
): Promise<Result> {
  if (!ui.status || !ui.identity || !ws || ws.readyState !== WebSocket.OPEN)
    return Promise.reject(Error("尚未连接"));
  if (
    ui.status.source !== "SIMULATED" &&
    !["READ_STATUS", "STOP_MOTION", "FAULT_STOP"].includes(type)
  )
    return Promise.reject(Error("实机接口尚未核验：操作锁定"));
  const rule = SPEC.commands[type],
    id = crypto.randomUUID();
  const c = validate({
    protocol: SPEC.protocol,
    device_id: ui.status.device_id,
    session_id: ui.status.session_id,
    command_id: id,
    client_id: ui.identity.client_id,
    source: Capacitor.isNativePlatform() ? "mobile" : "console",
    permissions: [rule.permission],
    type,
    params,
    sequence: ++seq,
    sent_at_ms: Math.floor(performance.now()),
    basis_device_ms: ui.status.device_ms,
    valid_for_ms: Math.min(
      rule.ttl_max_ms,
      rule.permission === "control" ? 300 : 10000,
    ),
  });
  return new Promise((resolve, reject) => {
    waiting.set(id, resolve);
    sent.set(id, performance.now());
    setTimeout(() => {
      if (waiting.delete(id)) {
        sent.delete(id);
        timeouts++;
        stats();
        reject(Error("命令结果超时"));
      }
    }, 3000);
    ws!.send(JSON.stringify(c));
  });
}
export async function command(
  type: CommandType,
  params: Record<string, unknown> = {},
) {
  try {
    const r = await send(type, params);
    ui.notice = r.status + (r.reason ? " · " + r.reason : "");
    return r;
  } catch (e) {
    ui.notice = String(e);
    return null;
  }
}
export async function claim() {
  const r = await command("CLAIM_CONTROL", { supervised: true });
  if (r?.status === "COMPLETED") lease.claim();
}
export function haltDrive() {
  if (driveTimer) clearInterval(driveTimer);
  driveTimer = null;
}
export function release() {
  lease.release();
  stopAudio();
}
export function startDrive(v: number, w: number) {
  if (!lease.active || stale()) {
    ui.notice = "请先取得控制权并等待新鲜状态";
    return;
  }
  haltDrive();
  const step = () => {
    if (!lease.active || stale()) {
      release();
      return;
    }
    void command("SET_VELOCITY", { v_m_s: v, yaw_rad_s: w });
  };
  step();
  driveTimer = setInterval(step, 100);
}
export async function prepareAudio() {
  audioContext ??= new AudioContext();
  await audioContext.resume();
}
export function stopAudio() {
  playbackEpoch++;
  if (playing) {
    playing.onended = null;
    playing.stop();
    playing = null;
  }
  if (playbackTimer) clearInterval(playbackTimer);
  playbackTimer = null;
  ui.playbackRms = 0;
}
async function playAudio(m: { command_id: string; audio_base64: string }) {
  stopAudio();
  const epoch = playbackEpoch;
  try {
    await prepareAudio();
    const bytes = Uint8Array.from(atob(m.audio_base64), (c) => c.charCodeAt(0));
    const buffer = await audioContext!.decodeAudioData(bytes.buffer);
    if (epoch !== playbackEpoch) return;
    const source = audioContext!.createBufferSource();
    const gain = audioContext!.createGain();
    gain.gain.value = ui.status?.volume ?? 0.55;
    const analyser = audioContext!.createAnalyser();
    analyser.fftSize = 512;
    source.buffer = buffer;
    source.connect(gain).connect(analyser).connect(audioContext!.destination);
    playing = source;
    const started = audioContext!.currentTime;
    const report = (ended: boolean) =>
      ws?.readyState === WebSocket.OPEN &&
      ws.send(
        JSON.stringify({
          type: "playback",
          command_id: m.command_id,
          ended,
          position_ms: Math.round((audioContext!.currentTime - started) * 1000),
        }),
      );
    source.onended = () => {
      report(true);
      playing = null;
      if (playbackTimer) clearInterval(playbackTimer);
      ui.playbackRms = 0;
    };
    source.start();
    report(false);
    const values = new Float32Array(analyser.fftSize);
    playbackTimer = setInterval(() => {
      analyser.getFloatTimeDomainData(values);
      ui.playbackRms = Math.sqrt(
        values.reduce((a, x) => a + x * x, 0) / values.length,
      );
    }, 25);
  } catch (e) {
    ui.notice = "播放失败或权限拒绝：" + String(e);
  }
}
export function installLifecycle() {
  window.addEventListener("moriNativeInactive", release);
  window.addEventListener("blur", release);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) release();
  });
  window.addEventListener("pagehide", release);
  if (Capacitor.isNativePlatform())
    void NativeApp.addListener("appStateChange", (s) => {
      if (!s.isActive) release();
    });
}
