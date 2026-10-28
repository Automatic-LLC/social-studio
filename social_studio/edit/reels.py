"""Render a 9:16 Reel from a stock clip with ffmpeg: meme text on top, credit at the bottom, optional voiceover and
music, and a short "Follow @handle" end card. Text is drawn with Pillow into transparent PNGs, so ffmpeg needs no
drawtext/fontconfig (which is awkward on Windows)."""
from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from social_studio.captions import EMOJI_RE

W, H = 1080, 1920
FONT_CANDIDATES = (
    "C:/Windows/Fonts/impact.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Impact.ttf",
)


class RenderError(Exception):
    pass


@dataclass
class ReelSpec:
    clip: Path
    out: Path
    text: str = ""                          # meme text, top of frame
    start: float = 0.0
    duration: float | None = None           # None = to the end of the clip
    voiceover: Path | None = None
    music: Path | None = None
    keep_clip_audio: bool = True
    end_card: str | None = "Follow @{handle}"
    credit: str | None = None               # small text at the bottom, e.g. "Video: Jane Doe / Pexels"


# --- probing -------------------------------------------------------------------------------------------------------

def probe(path: Path | str, ffprobe: str = "ffprobe") -> dict:
    """{'duration', 'width', 'height', 'has_audio'} of a media file."""
    cmd = [ffprobe, "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError as e:
        raise RenderError(f"ffprobe not found ({ffprobe})") from e
    if p.returncode != 0:
        raise RenderError(f"ffprobe failed for {path}: {p.stderr.strip()[-300:]}")
    data = json.loads(p.stdout or "{}")
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    w, h = int(video.get("width", 0)), int(video.get("height", 0))
    rotation = abs(int(float((video.get("tags") or {}).get("rotate", 0) or 0)))
    for side in video.get("side_data_list", []):
        if "rotation" in side:
            rotation = abs(int(float(side["rotation"])))
    if rotation % 180 == 90:
        w, h = h, w
    raw = (data.get("format") or {}).get("duration") or video.get("duration") or 0
    return {
        "duration": float(raw),
        "width": w,
        "height": h,
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
    }


# --- text overlays -------------------------------------------------------------------------------------------------

def resolve_font(preferred: str | None = None) -> str | None:
    """First font file that exists; None means Pillow's built-in font."""
    for f in (preferred, *FONT_CANDIDATES):
        if f and Path(f).is_file():
            return f
    return None


def _load(font: str | None, size: int):
    if font:
        try:
            return ImageFont.truetype(font, size)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size)
    except TypeError:  # Pillow < 10.1 has a fixed-size default font
        return ImageFont.load_default()


def clean(text: str) -> str:
    """Strip emojis (stock fonts have no glyphs for them) and collapse spaces."""
    return " ".join(EMOJI_RE.sub(" ", text).split())


def wrap(text: str, font, max_width: float) -> list[str]:
    """Greedy word wrap using font.getlength; a word wider than max_width is broken by characters."""
    lines: list[str] = []
    cur = ""
    for word in text.split():
        while font.getlength(word) > max_width and len(word) > 1:
            if cur:
                lines.append(cur)
                cur = ""
            n = len(word) - 1
            while n > 1 and font.getlength(word[:n]) > max_width:
                n -= 1
            lines.append(word[:n])
            word = word[n:]
        trial = f"{cur} {word}" if cur else word
        if cur and font.getlength(trial) > max_width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def _fit(text: str, font_path: str | None, max_width: int, start: int, floor: int, max_lines: int):
    """Largest font size (stepping down from start) whose wrapped text fits max_lines; (font, lines)."""
    size = start
    while True:
        font = _load(font_path, size)
        lines = wrap(text, font, max_width)
        if len(lines) <= max_lines or size <= floor:
            return font, lines
        size = max(floor, size - 4)


def overlay_png(path: Path, *, text: str, credit: str | None, font: str | None,
                size: tuple[int, int] = (W, H)) -> Path:
    """Transparent PNG with the meme text near the top and the credit at the bottom left."""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    text = clean(text)
    if text:
        f, lines = _fit(text, font, 920, 84, 44, 4)
        y = 230
        step = round(f.size * 1.18)
        for line in lines:
            d.text((size[0] / 2, y), line, font=f, fill="white", stroke_width=6, stroke_fill="black", anchor="mt")
            y += step
    if credit:
        # Above the bottom ~400 px, which Instagram covers with the caption and buttons.
        d.text((40, size[1] - 440), clean(credit), font=_load(font, 34), fill="white", stroke_width=2,
               stroke_fill="black", anchor="lt")
    img.save(path)
    return Path(path)


def end_card_png(path: Path, *, text: str, font: str | None, size: tuple[int, int] = (W, H)) -> Path:
    """Transparent PNG with the end-card text centred vertically on a translucent dark band."""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f, lines = _fit(clean(text), font, size[0] - 100, 96, 48, 2)
    step = round(f.size * 1.2)
    band = step * len(lines) + 120
    top = (size[1] - band) // 2
    d.rectangle((0, top, size[0], top + band), fill=(0, 0, 0, 170))
    y = size[1] / 2 - step * (len(lines) - 1) / 2
    for line in lines:
        d.text((size[0] / 2, y), line, font=f, fill="white", stroke_width=3, stroke_fill="black", anchor="mm")
        y += step
    img.save(path)
    return Path(path)


# --- ffmpeg --------------------------------------------------------------------------------------------------------

def build_command(spec: ReelSpec, *, info: dict, length: float, text_png: Path | None, card_png: Path | None,
                  end_card_seconds: float = 1.5, ffmpeg: str = "ffmpeg") -> list[str]:
    """The full ffmpeg argument list. `info` is probe() of the clip; `card_png` None means no end card."""
    L = f"{length:.3f}"
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
           "-ss", f"{spec.start:.3f}", "-t", L, "-i", str(spec.clip)]
    n = 1
    text_i = card_i = voice_i = music_i = lavfi_i = None
    if text_png:
        cmd += ["-loop", "1", "-framerate", "30", "-t", L, "-i", str(text_png)]
        text_i, n = n, n + 1
    if card_png:
        cmd += ["-loop", "1", "-framerate", "30", "-t", L, "-i", str(card_png)]
        card_i, n = n, n + 1
    if spec.voiceover:
        cmd += ["-i", str(spec.voiceover)]
        voice_i, n = n, n + 1
    if spec.music:
        cmd += ["-stream_loop", "-1", "-i", str(spec.music)]
        music_i, n = n, n + 1

    # Video: a source wider than 9:16 floats over a blurred, darkened copy of itself; otherwise fill and crop.
    if info["width"] * H > info["height"] * W:
        chain = [
            "[0:v]split=2[bg][fg]",
            f"[bg]scale={W // 4}:{H // 4}:force_original_aspect_ratio=increase,crop={W // 4}:{H // 4},"
            f"boxblur=6:2,scale={W}:{H},eq=brightness=-0.15[bgb]",
            f"[fg]scale={W}:-2[fgs]",
            "[bgb][fgs]overlay=(W-w)/2:(H-h)/2,fps=30,setsar=1[base]",
        ]
    else:
        chain = [f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,setsar=1[base]"]
    last = "base"
    if text_i is not None:
        chain.append(f"[{last}][{text_i}:v]overlay=0:0[vt]")
        last = "vt"
    if card_i is not None:
        chain.append(f"[{last}][{card_i}:v]overlay=0:0:enable='gte(t,{length - end_card_seconds:.3f})'[ve]")
        last = "ve"
    chain.append(f"[{last}]format=yuv420p[v]")

    # Audio: every source to 44.1 kHz stereo; the first is padded/trimmed to the length and leads amix.
    fmt = "aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo"
    use_clip = bool(info.get("has_audio")) and spec.keep_clip_audio
    srcs: list[str] = []
    if use_clip:
        vol = 0.6 if voice_i is not None else 1.0
        srcs.append(f"[0:a]{fmt},volume={vol}")
    if voice_i is not None:
        srcs.append(f"[{voice_i}:a]{fmt}")
    if music_i is not None:
        srcs.append(f"[{music_i}:a]{fmt},volume={0.12 if voice_i is not None else 0.35}")
    if not srcs:
        cmd += ["-f", "lavfi", "-t", L, "-i", "anullsrc=r=44100:cl=stereo"]
        srcs.append(f"[{n}:a]{fmt}")
    labelled = []
    for k, s in enumerate(srcs):
        tail = f",apad=whole_dur={L},atrim=0:{L}" if k == 0 else f",atrim=0:{L}"
        labelled.append(f"{s}{tail},asetpts=PTS-STARTPTS[a{k}]")
    chain += labelled
    if len(srcs) == 1:
        chain.append("[a0]anull[a]")
    else:
        ins = "".join(f"[a{k}]" for k in range(len(srcs)))
        chain.append(f"{ins}amix=inputs={len(srcs)}:duration=first:normalize=0:dropout_transition=0[a]")

    cmd += ["-filter_complex", ";".join(chain), "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
            "-movflags", "+faststart", "-t", L, str(spec.out)]
    return cmd


def render(spec: ReelSpec, *, handle: str, font: str | None = None, ffmpeg: str = "ffmpeg",
           ffprobe: str = "ffprobe", max_seconds: float = 90.0, min_seconds: float = 3.0,
           end_card_seconds: float = 1.5) -> Path:
    """Render the Reel to spec.out and return that path. Raises RenderError on bad input or ffmpeg failure."""
    for label, p in (("clip", spec.clip), ("voiceover", spec.voiceover), ("music", spec.music)):
        if p is not None and not Path(p).is_file():
            raise RenderError(f"{label} file not found: {p}")
    info = probe(spec.clip, ffprobe)
    length = info["duration"] - spec.start
    if spec.duration is not None:
        length = min(length, spec.duration)
    length = min(length, max_seconds)
    if length < min_seconds:
        raise RenderError(f"Reel would be {max(length, 0):.1f}s, under the {min_seconds:g}s minimum")
    font = resolve_font(font)
    out = Path(spec.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reel_") as tmp:
        tmp_dir = Path(tmp)
        text_png = card_png = None
        if clean(spec.text) or spec.credit:
            text_png = overlay_png(tmp_dir / "text.png", text=spec.text, credit=spec.credit, font=font)
        if spec.end_card:
            card_png = end_card_png(tmp_dir / "card.png", text=spec.end_card.format(handle=handle), font=font)
        cmd = build_command(spec, info=info, length=length, text_png=text_png, card_png=card_png,
                            end_card_seconds=end_card_seconds, ffmpeg=ffmpeg)
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        except FileNotFoundError as e:
            raise RenderError(f"ffmpeg not found ({ffmpeg})") from e
    if p.returncode != 0:
        out.unlink(missing_ok=True)
        tail = "\n".join(p.stderr.strip().splitlines()[-15:])
        raise RenderError(f"ffmpeg failed ({p.returncode}):\n{tail}")
    return out
