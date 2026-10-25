/** MORI eyes-only mapping. Projection/liveliness: bloub MIT, see LICENSE.bloub.
 * No body, SVG masks, mouths or implicit motor state. Deterministic input clock. */
import {
  eyePoses,
  liveliness,
  blinkScale,
  EYE_W,
  EYE_H,
} from "./reference-face";
export const moods = [
  "idle",
  "listening",
  "thinking",
  "speaking",
  "happy",
  "confused",
  "sleep_visual",
  "error",
] as const;
export type Mood = (typeof moods)[number];
export type Eye = {
  x: number;
  y: number;
  a: number;
  b: number;
  c: number;
  d: number;
  w: number;
  h: number;
};
export type Frame = [Eye, Eye];
const poses: Record<Mood, [number, number, number, number, number]> = {
  idle: [0, 0, 0, 1, 1],
  listening: [0, 5, 0, 1, 1.15],
  thinking: [12, 8, -5, 0.92, 0.8],
  speaking: [0, 2, 0, 1, 1],
  happy: [0, 4, 0, 1.05, 0.55],
  confused: [-9, 2, 10, 1, 0.85],
  sleep_visual: [0, 0, 0, 1, 0.06],
  error: [0, 0, 0, 1, 0.45],
};
function target(m: Mood, t: number, rms: number): Frame {
  const [yaw, pitch, roll, w, h] = poses[m],
    life = liveliness(t, {
      wander: m === "sleep_visual" ? 0 : 0.35,
      blink: false,
      float: false,
    });
  const k = blinkScale(
    liveliness(t % 905, {
      wander: 0,
      blink: m !== "sleep_visual",
      float: false,
    }).lid,
  );
  return eyePoses(
    {
      yaw: yaw + life.dYaw,
      pitch: pitch + life.dPitch,
      roll: roll + life.dRoll,
    },
    1,
  ).map((p) => ({
    x: p.x,
    y: p.y,
    a: p.a,
    b: p.b * k,
    c: p.c,
    d: p.d * k,
    w: EYE_W * w,
    h:
      EYE_H *
      h *
      (m === "speaking" ? 1 + Math.min(1, Math.max(0, rms)) * 0.15 : 1),
  })) as Frame;
}
export interface EyeSkin {
  id: string;
  sample: (m: Mood, t: number, rms: number) => Frame;
}
export const referenceSkin: EyeSkin = {
  id: "bloub-reference-mori-mapping",
  sample: target,
};
export class Eyes {
  constructor(readonly skin: EyeSkin = referenceSkin) {}
  state: Mood = "idle";
  private from: Frame | null = null;
  private start = 0;
  setState(next: Mood, seconds: number, rms = 0) {
    if (!moods.includes(next) || !Number.isFinite(seconds) || seconds < 0)
      throw Error("eyes input");
    if (next === this.state) return;
    this.from = this.sample(seconds, rms);
    this.state = next;
    this.start = seconds;
  }
  sample(seconds: number, rms = 0): Frame {
    if (!Number.isFinite(seconds) || seconds < 0 || !Number.isFinite(rms))
      throw Error("eyes input");
    const out = this.skin.sample(this.state, seconds, rms);
    const x = Math.max(0, Math.min(1, (seconds - this.start) / 0.35)),
      k = 1 - (1 - x) ** 3;
    if (!this.from || k === 1) return out;
    return out.map((e, i) =>
      Object.fromEntries(
        Object.keys(e).map((key) => {
          const p = key as keyof Eye;
          return [key, this.from![i]![p] + (e[p] - this.from![i]![p]) * k];
        }),
      ),
    ) as Frame;
  }
}
export function drawEyes(canvas: HTMLCanvasElement, frame: Frame) {
  const ctx = canvas.getContext("2d")!;
  const n = Math.min(canvas.width, canvas.height),
    r = n * 0.46;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.save();
  ctx.beginPath();
  ctx.arc(canvas.width / 2, canvas.height / 2, r, 0, Math.PI * 2);
  ctx.clip();
  ctx.fillStyle = "#f7f7f2";
  for (const e of frame) {
    ctx.save();
    ctx.translate(canvas.width / 2 + e.x * r, canvas.height / 2 + e.y * r);
    ctx.transform(e.a, e.b, e.c, e.d, 0, 0);
    ctx.beginPath();
    ctx.roundRect(
      (-e.w * r) / 2,
      (-e.h * r) / 2,
      e.w * r,
      e.h * r,
      (Math.min(e.w, e.h) * r) / 2,
    );
    ctx.fill();
    ctx.restore();
  }
  ctx.restore();
}
