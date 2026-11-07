/* Tiny 8-bit blips with WebAudio. Muted unless the operator turns sound on. */
let ctx: AudioContext | null = null;

export function blip(kind: "packet" | "stamp" | "alert" | "arrive", on: boolean): void {
  if (!on) return;
  try {
    ctx = ctx ?? new AudioContext();
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    const f = { packet: 880, stamp: 330, alert: 180, arrive: 520 }[kind];
    o.type = kind === "alert" ? "sawtooth" : "square";
    o.frequency.setValueAtTime(f, ctx.currentTime);
    if (kind === "stamp") o.frequency.exponentialRampToValueAtTime(660, ctx.currentTime + 0.12);
    g.gain.setValueAtTime(0.04, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + (kind === "packet" ? 0.05 : 0.2));
    o.connect(g).connect(ctx.destination);
    o.start();
    o.stop(ctx.currentTime + 0.22);
  } catch {
    /* audio unavailable */
  }
}
