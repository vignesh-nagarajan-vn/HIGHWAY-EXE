"""Narrate each scene in video/script.json with edge-tts and record the clip lengths.

Writes video/out/audio/NN_<id>.mp3 and video/out/durations.json.
"""
import asyncio
import json
import re
import subprocess
from pathlib import Path

import edge_tts
import imageio_ffmpeg

HERE = Path(__file__).parent
OUT = HERE / "out" / "audio"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def duration(path: Path) -> float:
    err = subprocess.run([FFMPEG, "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


async def main() -> None:
    script = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, sc in enumerate(script["scenes"], 1):
        path = OUT / f"{i:02d}_{sc['id']}.mp3"
        await edge_tts.Communicate(sc["text"], script["voice"], rate=script["rate"]).save(str(path))
        rows.append({"id": sc["id"], "file": str(path), "seconds": round(duration(path), 3)})
        print(f"{sc['id']:>9}  {rows[-1]['seconds']:.2f}s")
    (HERE / "out" / "durations.json").write_text(json.dumps(rows, indent=2))
    print(f"total narration {sum(r['seconds'] for r in rows):.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
