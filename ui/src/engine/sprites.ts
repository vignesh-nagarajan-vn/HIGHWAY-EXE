/* Original pixel art, defined as character matrices and drawn to canvas at integer scale.
   Palette keys: . transparent, k outline, w white, c cyan, m magenta, a acid, y amber,
   v violet, g dark glass, r red, d dark body, s steel, b black, o orange, p pink-skin */

export const PAL: Record<string, string> = {
  k: "#07021a", w: "#f4f1ff", c: "#05d9e8", m: "#ff2a6d", a: "#39ff14", y: "#f9c80e", v: "#b967ff",
  g: "#2a3a7a", r: "#ff3b3b", d: "#2b1a66", s: "#8b84bf", b: "#000000", o: "#ff8a1f", p: "#f2b38a",
  n: "#5b3bd1", h: "#1a0d45", l: "#ffe9a8",
};

export type Sprite = string[];

export const TRUCK: Sprite = [
  "..........kkkkkkkkkkkkkkkk",
  "..kkkkk...kddddddddddddddk",
  ".kcccgk...kdyyyyyyddkkkkdk",
  ".kcgggk...kdykkkkyddkwwkdk",
  "kkcgggkkkkkdykwkkyddkkwkdk",
  "kcccccccckkdykkkwyddkwwkdk",
  "kcmmmmmcckkdyyyyyyddkkkkdk",
  "kcccccccckkddddddddddddddk",
  "kkkkkkkkkkkkkkkkkkkkkkkkkk",
  ".kbsbk.......kbsbk.kbsbk..",
  "..kbk.........kbk...kbk...",
];

export const TRAILER: Sprite = [
  "kkkkkkkkkkkkkkkk",
  "kddddddddddddddk",
  "kdcccccccccccddk",
  "kdcddddddddddcdk",
  "kdcccccccccccddk",
  "kddddddddddddddk",
  "kddddddddddddddk",
  "kddddddddddddddk",
  "kkkkkkkkkkkkkkkk",
  "..kbsbk..kbsbk..",
  "...kbk....kbk...",
];

export const HAZARD_CAR: Sprite = [
  "....kkkkkkkk......",
  "...kggggggggk.....",
  "..kgcgggggcggk....",
  "kkkkkkkkkkkkkkkkk.",
  "kykbykbykbykbykyk.",
  "kbykbykbykbykbyrrk",
  "kkkkkkkkkkkkkkkkkk",
  "..kbsbk.....kbsbk.",
  "...kbk.......kbk..",
];

export const GHOST_CAR: Sprite = [
  "....kkkkkkkk......",
  "...kvvvvvvvvk.....",
  "..kvwvvvvvvwvk....",
  "kkvvvvvvvvvvvvvvk.",
  "kvvvvvwwwwvvvvvvvk",
  "kvvvvwvvvvwvvvvvvk",
  "kvvvvvvvwwvvvvvvvk",
  "kkvvvvvvvvvvvvvvkk",
  "..kvk.kvk..kvk.kvk",
];

export const BLIMP: Sprite = [
  "......kkkkkkkkkkkk......",
  "...kkkwwwwwwwwwwwwkkk...",
  ".kkwwwwmmmmmmmmmmwwwwkk.",
  "kwwwwwwmwwmwmmmwwwwwwwkk",
  "kwwwwwwmmmmwmwmwwwwwwwkkk",
  ".kkwwwwmwwmwmmmwwwwwwkk.k",
  "...kkkwwwwwwwwwwwwkkk..kk",
  "......kkkkkkkkkkkk.......",
  "..........kssk...........",
  "..........kkkk...........",
];

export const FACTORY_RIG: Sprite = [
  "...kk.....kk..............",
  "...kdk....kdk.............",
  "...kdk....kdk.....kkkkk...",
  "..kkdkkkkkkdkkkkkkkrrrk...",
  "..kdddddddddddddddkrkrk...",
  "..kdgdgdgdddkkkkdddkrrk...",
  "..kdddddddddkrkkdddkkk....",
  "..kdgdgdgdddkkrkddddk.....",
  "..kdddddddddkkkkddddk.....",
  "kkkkkkkkkkkkkkkkkkkkkkkkkk",
  "kssssssssssssssssssssssssk",
  "kkkkkkkkkkkkkkkkkkkkkkkkkk",
  ".kbsbk.kbsbk.....kbsbk....",
  "..kbk...kbk.......kbk.....",
];

/* 16x16 crew portraits */
export const PORTRAITS: Record<string, Sprite> = {
  DISPATCH: [
    "....kkkkkkkk....",
    "...kddddddddk...",
    "..kddddddddddk..",
    "..kdkkkkkkkkdk..",
    "kkkkccccccccckkk",
    "kskkcwccccwcckks",
    "kskkccccccccckks",
    "kk.kppppppppk.kk",
    "kk.kppkppkppk.kk",
    "kmk.kppppppk.kmk",
    ".km.kppkkppk.mk.",
    "..kk.kppppk.kk..",
    "....kkkkkkkk....",
    "..kcccccccccck..",
    ".kccmccccccmcck.",
    ".kcccccccccccck.",
  ],
  FORGE: [
    "....kkkkkkkk....",
    "...kyyyyyyyyk...",
    "..kyyyyyyyyyyk..",
    ".kkkkkkkkkkkkkk.",
    ".kyyyyyyyyyyyyk.",
    "..kbbbbbbbbbbk..",
    "..kbobbbbbbobk..",
    "..kbbbbbbbbbbk..",
    "..kppppppppppk..",
    "..kppkppppkppk..",
    "...kppppppppk...",
    "....kpkkkkpk....",
    ".....kkkkkk.....",
    "..kssssssssssk..",
    ".ksyssssssssysk.",
    ".kssssssssssssk.",
  ],
  AEGIS: [
    "......kkkk......",
    "....kkmmmmkk....",
    "...kmmmwwmmmk...",
    "..kmmmmmmmmmmk..",
    "..kmkkkkkkkkmk..",
    "..kkaaaaaaaakk..",
    "..kkakaaaakakk..",
    "..kmaaaaaaaamk..",
    "..kmppppppppmk..",
    "...kppkkkkppk...",
    "...kppppppppk...",
    "....kkppppkk....",
    "......kkkk......",
    "..kmmmmmmmmmmk..",
    ".kmmwmmmmmmwmmk.",
    ".kmmmmmmmmmmmmk.",
  ],
  RELAY: [
    ".......ka.......",
    ".......kk.......",
    "....kkkkkkkk....",
    "...kaaaaaaaak...",
    "..kaaaaaaaaaak..",
    "..kakkkkkkkkak..",
    "..kkppppppppkk..",
    "..kppwkppwkppk..",
    "..kppkkppkkppk..",
    "..kppppppppppk..",
    "...kppkkkkppk...",
    "....kppppppk....",
    ".....kkkkkk.....",
    "..kaaaaaaaaaak..",
    ".kaakaaaaaakaak.",
    ".kaaaaaaaaaaaak.",
  ],
};

export function drawSprite(ctx: CanvasRenderingContext2D, s: Sprite, x: number, y: number, scale: number,
                           alpha = 1, flip = false): void {
  ctx.save();
  ctx.globalAlpha = alpha;
  const w = s[0].length;
  for (let r = 0; r < s.length; r++) {
    const row = s[r];
    for (let c = 0; c < row.length; c++) {
      const ch = row[c];
      if (ch === "." || ch === " ") continue;
      ctx.fillStyle = PAL[ch] ?? "#ff00ff";
      const cx = flip ? w - 1 - c : c;
      ctx.fillRect(Math.round(x + cx * scale), Math.round(y + r * scale), scale, scale);
    }
  }
  ctx.restore();
}

export function spriteSize(s: Sprite, scale: number) {
  return { w: s[0].length * scale, h: s.length * scale };
}

/** Deterministic pseudo-random (for skylines and stars). */
export function rng(seed: number) {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}
