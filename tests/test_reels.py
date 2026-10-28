from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from social_studio.edit import reels
from social_studio.edit.reels import ReelSpec, RenderError, build_command, probe, render, wrap


class FakeFont:
    """Every character is 10 px wide."""

    def getlength(self, s: str) -> float:
        return 10 * len(s)


def test_wrap_breaks_on_words():
    assert wrap("one two three four", FakeFont(), 90) == ["one two", "three", "four"]
    assert wrap("", FakeFont(), 90) == []


def test_wrap_breaks_a_word_that_is_too_wide():
    lines = wrap("a supercalifragilistic b", FakeFont(), 100)
    assert all(len(x) * 10 <= 100 for x in lines) and "".join(lines).replace(" ", "") == "asupercalifragilisticb"


def test_clean_strips_emojis():
    assert reels.clean("POV:  walk \U0001F415 now \U0001F602") == "POV: walk now"


def test_resolve_font(tmp_path):
    f = tmp_path / "x.ttf"
    f.write_bytes(b"")
    assert reels.resolve_font(str(f)) == str(f)
    assert reels.resolve_font(str(tmp_path / "nope.ttf")) in (None, *reels.FONT_CANDIDATES)


def spec(tmp_path, **kw):
    return ReelSpec(clip=tmp_path / "c.mp4", out=tmp_path / "o.mp4", **kw)


def cmd(tmp_path, *, has_audio=False, w=1280, h=720, length=10.0, card=True, **kw):
    return build_command(spec(tmp_path, **kw), info={"width": w, "height": h, "has_audio": has_audio}, length=length,
                         text_png=tmp_path / "t.png", card_png=tmp_path / "e.png" if card else None)


def graph(c: list[str]) -> str:
    return c[c.index("-filter_complex") + 1]


def test_end_card_enable_expression(tmp_path):
    g = graph(cmd(tmp_path, length=10.0))
    assert "enable='gte(t,8.500)'" in g
    assert "enable=" not in graph(cmd(tmp_path, card=False))


def test_silence_when_no_audio_source(tmp_path):
    c = cmd(tmp_path, has_audio=False)
    assert any(a.startswith("anullsrc") for a in c) and "amix" not in graph(c)
    # a clip with audio, kept, needs no silence
    assert not any(a.startswith("anullsrc") for a in cmd(tmp_path, has_audio=True))
    # a clip with audio, muted by the spec, falls back to silence
    assert any(a.startswith("anullsrc") for a in cmd(tmp_path, has_audio=True, keep_clip_audio=False))


def test_music_loops_and_volume_depends_on_voiceover(tmp_path):
    c = cmd(tmp_path, has_audio=True, music=tmp_path / "m.mp3")
    assert c[c.index("-stream_loop") + 1] == "-1" and c[c.index("-stream_loop") + 2] == "-i"
    assert "volume=0.35" in graph(c) and "normalize=0" in graph(c) and "duration=first" in graph(c)
    c = cmd(tmp_path, has_audio=True, music=tmp_path / "m.mp3", voiceover=tmp_path / "v.wav")
    g = graph(c)
    assert "volume=0.12" in g and "volume=0.6" in g and "amix=inputs=3" in g


def test_layout_depends_on_aspect(tmp_path):
    assert "boxblur" in graph(cmd(tmp_path, w=1280, h=720))
    portrait = graph(cmd(tmp_path, w=720, h=1280))
    assert "boxblur" not in portrait and "crop=1080:1920" in portrait


def test_output_settings_and_no_shell_strings(tmp_path):
    c = cmd(tmp_path)
    for a in ("libx264", "yuv420p", "aac", "+faststart", "-crf"):
        assert a in c
    assert c[-1] == str(tmp_path / "o.mp4") and all(isinstance(a, str) for a in c)


def test_overlay_pngs(tmp_path):
    font = reels.resolve_font()
    t = reels.overlay_png(tmp_path / "t.png", text="POV: you whispered the word walk from 3 rooms away",
                          credit="Video: Test / Pexels", font=font)
    e = reels.end_card_png(tmp_path / "e.png", text="Follow @x", font=font)
    for p in (t, e):
        im = Image.open(p)
        assert im.size == (1080, 1920) and im.mode == "RGBA"
    assert Image.open(t).getchannel("A").getbbox() is not None
    assert Image.open(e).getpixel((0, 0))[3] == 0 and Image.open(e).getpixel((10, 960))[3] > 0


# --- real renders --------------------------------------------------------------------------------------------------

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                                  reason="ffmpeg not installed")


def ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], check=True)


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    d = tmp_path_factory.mktemp("media")
    ff("-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30", "-f", "lavfi", "-i", "sine=frequency=440",
       "-t", "4", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", str(d / "wide.mp4"))
    ff("-f", "lavfi", "-i", "testsrc=size=720x1280:rate=30", "-t", "4", "-c:v", "libx264", "-preset", "ultrafast",
       "-pix_fmt", "yuv420p", str(d / "tall.mp4"))
    ff("-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30", "-t", "2", "-c:v", "libx264", "-preset", "ultrafast",
       "-pix_fmt", "yuv420p", str(d / "short.mp4"))
    ff("-f", "lavfi", "-i", "sine=frequency=300:duration=2", str(d / "voice.wav"))
    ff("-f", "lavfi", "-i", "sine=frequency=600:duration=1", str(d / "music.wav"))
    return d


def streams(path: Path) -> tuple[dict, dict, float]:
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format",
                          str(path)], capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    v = next(s for s in data["streams"] if s["codec_type"] == "video")
    a = next(s for s in data["streams"] if s["codec_type"] == "audio")
    return v, a, float(data["format"]["duration"])


def check_reel(path: Path, seconds: float) -> None:
    v, a, dur = streams(path)
    assert (v["width"], v["height"], v["codec_name"], v["pix_fmt"]) == (1080, 1920, "h264", "yuv420p")
    assert a["codec_name"] == "aac" and int(a["sample_rate"]) == 44100 and a["channels"] == 2
    assert abs(dur - seconds) < 0.3


@needs_ffmpeg
def test_probe(media):
    assert probe(media / "wide.mp4")["has_audio"] is True
    info = probe(media / "tall.mp4")
    assert (info["width"], info["height"], info["has_audio"]) == (720, 1280, False)
    assert abs(info["duration"] - 4) < 0.2


@needs_ffmpeg
def test_render_landscape_with_text_and_credit(media, tmp_path):
    out = render(ReelSpec(clip=media / "wide.mp4", out=tmp_path / "sub" / "a.mp4", text="POV: walk \U0001F415",
                          credit="Video: Test / Pexels"), handle="dog")
    assert out.is_file()
    check_reel(out, 4)


@needs_ffmpeg
def test_render_portrait_silent_with_voiceover_and_music(media, tmp_path):
    out = render(ReelSpec(clip=media / "tall.mp4", out=tmp_path / "b.mp4", voiceover=media / "voice.wav",
                          music=media / "music.wav", start=0.5, duration=3.2, end_card=None), handle="dog")
    check_reel(out, 3.2)


@needs_ffmpeg
def test_render_too_short_raises(media, tmp_path):
    with pytest.raises(RenderError, match="minimum"):
        render(ReelSpec(clip=media / "short.mp4", out=tmp_path / "c.mp4"), handle="dog")
    with pytest.raises(RenderError):
        render(ReelSpec(clip=media / "wide.mp4", out=tmp_path / "c.mp4", start=2.0), handle="dog")
    assert not (tmp_path / "c.mp4").exists()


@needs_ffmpeg
def test_render_reports_ffmpeg_errors(media, tmp_path):
    with pytest.raises(RenderError, match="not found"):
        render(ReelSpec(clip=tmp_path / "missing.mp4", out=tmp_path / "d.mp4"), handle="dog")
    with pytest.raises(RenderError, match="ffmpeg"):
        render(ReelSpec(clip=media / "wide.mp4", out=tmp_path / "no" / "e.mp4"), handle="dog", ffmpeg="ffmpeg-nope")
