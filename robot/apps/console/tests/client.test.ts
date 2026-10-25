import { afterEach, beforeEach, expect, it, vi } from "vitest";
vi.mock("@capacitor/app", () => ({ App: { addListener: vi.fn() } }));
vi.mock("@capacitor/core", () => ({
  Capacitor: { isNativePlatform: () => false },
}));
class Socket {
  static OPEN = 1;
  static latest: Socket;
  readyState = 1;
  sent: any[] = [];
  onmessage?: (e: any) => void;
  onclose?: (e: any) => void;
  constructor() {
    Socket.latest = this;
  }
  send(data: string) {
    this.sent.push(JSON.parse(data));
  }
  close() {
    this.readyState = 3;
    this.onclose?.({ code: 1000 });
  }
  receive(type: string, data: any) {
    this.onmessage?.({ data: JSON.stringify({ type, data }) });
  }
}
const identity = {
  token: "test-credential-only",
  client_id: "client_test",
  permissions: ["control", "camera"],
};
const state = (session_id = "session_test") => ({
  device_id: "device_test",
  session_id,
  source: "SIMULATED",
  device_ms: 10,
  events: [],
  camera: { mode: "OFF", upload_allowed: false },
});
let storage: Map<string, string>;
beforeEach(() => {
  vi.resetModules();
  vi.useFakeTimers();
  storage = new Map();
  vi.stubGlobal("location", { protocol: "http:", hostname: "127.0.0.1" });
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => storage.get(k) ?? null,
    setItem: (k: string, v: string) => storage.set(k, v),
    removeItem: (k: string) => storage.delete(k),
  });
  vi.stubGlobal("WebSocket", Socket);
  vi.stubGlobal("document", {
    hidden: false,
    hasFocus: () => true,
    createElement: () => ({}),
  });
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, json: async () => identity })),
  );
});
afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
async function paired() {
  const client = await import("../src/client");
  await client.pair("local-code");
  Socket.latest.receive("telemetry", state());
  return client;
}
it("restores authentication after reload without restoring a control lease, and removes revoked credentials", async () => {
  await paired();
  vi.resetModules();
  const client = await import("../src/client");
  client.restorePairing();
  expect(client.ui.identity?.client_id).toBe(identity.client_id);
  expect(client.lease.active).toBe(false);
  await client.revokePairing();
  expect(fetch).toHaveBeenLastCalledWith(
    expect.stringContaining("/credentials/revoke"),
    expect.objectContaining({ method: "POST" }),
  );
  vi.resetModules();
  const fresh = await import("../src/client");
  fresh.restorePairing();
  expect(fresh.ui.identity).toBeNull();
});
it("rejects in-flight commands promptly on session change and disconnect", async () => {
  const c = await paired();
  const pending = expect(c.send("READ_STATUS", {})).rejects.toThrow("会话");
  Socket.latest.receive("telemetry", state("new_session"));
  await pending;
  const disconnected = expect(c.send("READ_STATUS", {})).rejects.toThrow(
    "断开",
  );
  Socket.latest.close();
  await disconnected;
});
it("heartbeat rejection drops the lease and cannot auto-reclaim it", async () => {
  const c = await paired();
  c.lease.claim();
  const pending = c.send("HEARTBEAT", {});
  const command = Socket.latest.sent.at(-1);
  Socket.latest.receive("result", {
    command_id: command.command_id,
    type: "HEARTBEAT",
    status: "REJECTED",
    reason: "NO_LEASE",
  });
  await pending;
  expect(c.lease.active).toBe(false);
  const count = Socket.latest.sent.length;
  await vi.advanceTimersByTimeAsync(500);
  expect(Socket.latest.sent.length).toBe(count);
});
it("does not send a stored token to a different gateway", async () => {
  const c = await paired();
  c.ui.base = "https://another.example";
  await c.api("/api/status");
  expect(fetch).toHaveBeenLastCalledWith(
    "https://another.example/api/status",
    expect.objectContaining({
      headers: { "Content-Type": "application/json" },
    }),
  );
});
it("resumes above the authenticated sequence floor after reconnecting", async () => {
  const c = await paired();
  Socket.latest.receive("telemetry", { ...state(), client_sequence: 47 });
  const pending = c.send("READ_STATUS", {});
  const command = Socket.latest.sent.at(-1);
  expect(command.sequence).toBe(48);
  Socket.latest.receive("result", {
    command_id: command.command_id,
    type: "READ_STATUS",
    status: "COMPLETED",
  });
  await pending;
});
it("isolates gateways under different paths and normalizes trailing slashes", async () => {
  const c = await import("../src/client");
  c.ui.base = "https://gateway.example/robot-a/";
  await c.pair("local-code");
  c.ui.base = "https://gateway.example/robot-b";
  await c.request("/api/status");
  expect(fetch).toHaveBeenLastCalledWith(
    "https://gateway.example/robot-b/api/status",
    expect.objectContaining({
      headers: { "Content-Type": "application/json" },
    }),
  );
  c.restorePairing();
  expect(c.ui.identity).toBeNull();
  c.ui.base = "https://gateway.example/robot-a";
  c.restorePairing();
  expect(c.ui.identity?.token).toBe(identity.token);
});
it("does not migrate ambiguous origin-only credentials to a gateway", async () => {
  storage.set(
    "mori.credential:https://gateway.example",
    JSON.stringify(identity),
  );
  const c = await import("../src/client");
  c.ui.base = "https://gateway.example";
  c.restorePairing();
  expect(c.ui.identity).toBeNull();
});
it("clears rejected saved credentials on policy close and does not restore them", async () => {
  const c = await paired();
  c.lease.claim();
  Socket.latest.onclose?.({ code: 1008 });
  expect(c.ui.identity).toBeNull();
  expect(c.lease.active).toBe(false);
  expect(c.ui.notice).toContain("重新配对");
  vi.resetModules();
  const fresh = await import("../src/client");
  fresh.restorePairing();
  expect(fresh.ui.identity).toBeNull();
});
it("retains valid pairing across a normal transport disconnect", async () => {
  const c = await paired();
  Socket.latest.close();
  expect(c.ui.identity?.token).toBe(identity.token);
  vi.resetModules();
  const fresh = await import("../src/client");
  fresh.restorePairing();
  expect(fresh.ui.identity?.token).toBe(identity.token);
  expect(fresh.lease.active).toBe(false);
});
