"""Mux the recorded footage with the narration into video/out/highway_demo.mp4."""
import json
import subprocess
from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).parent
OUT = HERE / "out"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


FPS = 30


def sync_offset(raw: Path) -> float:
    """Seconds into raw.webm where the green sync flash ends (scene time 0)."""
    w, h = 16, 9
    data = subprocess.run([FFMPEG, "-i", str(raw), "-t", "30", "-vf", f"fps={FPS},scale={w}:{h}",
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    size = w * h * 3
    green = []
    for i in range(len(data) // size):
        px = data[i * size:(i + 1) * size]
        r, g, b = (sum(px[c::3]) / (w * h) for c in range(3))
        green.append(g > 200 and r < 60 and b < 60)
    ends = [i for i in range(1, len(green)) if green[i - 1] and not green[i]]
    if not ends:
        return None
    return ends[-1] / FPS + 1.0  # scene 0 starts 1 s after the last flash ends


def main() -> None:
    tl = json.loads((OUT / "timeline.json").read_text())
    durs = {d["id"]: d["file"] for d in json.loads((OUT / "durations.json").read_text())}
    total = tl["total"]
    offset = sync_offset(OUT / "raw.webm")
    if offset is None:  # screencast starts ~1.26 s after the context opens (measured)
        offset = tl["video_offset"] - 1.26
        print(f"sync flash not found; using wall-clock offset {offset:.3f}s")
    else:
        print(f"sync offset {offset:.3f}s (wall-clock guess was {tl['video_offset']}s)")

    cmd = [FFMPEG, "-y", "-ss", f"{offset:.3f}", "-i", str(OUT / "raw.webm")]
    parts, labels = [], []
    for i, sc in enumerate(tl["scenes"], 1):
        cmd += ["-i", durs[sc["id"]]]
        ms = int(sc["start"] * 1000) + 150
        parts.append(f"[{i}:a]adelay={ms}|{ms},aresample=48000[a{i}]")
        labels.append(f"[a{i}]")
    fade_out = max(0.0, total - 0.6)
    graph = ";".join(parts) + f";{''.join(labels)}amix=inputs={len(labels)}:normalize=0,apad[aout]" \
        + f";[0:v]fps=30,fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out:.2f}:d=0.6,format=yuv420p[vout]"
    cmd += ["-filter_complex", graph, "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-tune", "animation",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(OUT / "highway_demo.mp4")]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"wrote {OUT / 'highway_demo.mp4'} ({total:.1f}s)")


if __name__ == "__main__":
    main()
