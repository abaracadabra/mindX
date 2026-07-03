"""Tests for the soundcloud.tool pro-player helpers (config / widget / drop)."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("scmod", ROOT / "agents/wordpress_agent/soundcloud.py")
sc = importlib.util.module_from_spec(spec)
sys.modules["scmod"] = sc
spec.loader.exec_module(sc)


# ── player_config ─────────────────────────────────────────────────────────────
def test_config_zero_config_is_highlights():
    cfg = sc.player_config()
    assert cfg["album"] == "music4robots2dance2"
    assert "2216206346" in cfg["resource"]
    assert cfg["story"] == sc.ARTICLE_URL
    assert cfg["controls"] is True


def test_config_takit_album():
    cfg = sc.player_config("takit")
    assert "2249417369" in cfg["resource"]
    assert cfg["color"] == "9d7833"


def test_config_explicit_url_has_no_album_default():
    cfg = sc.player_config(url="https://soundcloud.com/mag-magnus/sets/takit-1")
    assert cfg["album"] is None
    assert cfg["resource"].endswith("/sets/takit-1")


def test_config_story_suppressible():
    cfg = sc.player_config(story="")
    assert cfg["story"] == ""


def test_config_flags_pass_through():
    cfg = sc.player_config(theme="light", sticky=True, lazy=True, controls=False)
    assert cfg["theme"] == "light"
    assert cfg["sticky"] and cfg["lazy"] and cfg["controls"] is False


# ── widget_player (enhanced wrapper HTML) ─────────────────────────────────────
def test_widget_player_has_data_attrs_and_iframe():
    html = sc.widget_player()
    assert 'class="m4r2d2-embed"' in html
    assert 'data-enhanced="1"' in html
    assert 'data-controls="true"' in html
    assert "w.soundcloud.com/player" in html
    assert "<iframe" in html  # not lazy → iframe present


def test_widget_player_lazy_omits_iframe():
    html = sc.widget_player(lazy=True)
    assert 'data-lazy="true"' in html
    assert "<iframe" not in html  # lazy → JS builds the facade
    assert "data-src=" in html


def test_widget_player_escapes():
    html = sc.widget_player(title='a"b<c')
    assert '"b<c' not in html  # quote/markup escaped
    assert "&" in html  # entity-encoded somewhere


# ── drop_snippet ───────────────────────────────────────────────────────────────
def test_drop_snippet_minimal():
    s = sc.drop_snippet("https://cdn.example.com/m4r2d2/assets")
    assert s.startswith("<script")
    assert s.endswith("></script>")
    assert "/m4r2d2-drop.js" in s
    assert 'data-album="music4robots2dance2"' in s
    assert "defer" in s


def test_drop_snippet_strips_trailing_slash():
    s = sc.drop_snippet("https://x.dev/a/", album="takit", sticky=False)
    assert "https://x.dev/a/m4r2d2-drop.js" in s
    assert 'data-album="takit"' in s
    assert 'data-sticky="false"' in s
