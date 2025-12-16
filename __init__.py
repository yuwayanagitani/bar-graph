from __future__ import annotations

import os
import json

from datetime import datetime, timedelta
from typing import Any, List

from aqt import mw  # type: ignore
from aqt.qt import *  # type: ignore

try:
    from aqt import gui_hooks  # type: ignore
except Exception:
    gui_hooks = None  # type: ignore

_DIRTY = False  # review中に進んだ印

def _addon_id() -> str:
    # できるだけ確実に「今ロードされてるこのアドオンのID(フォルダ名)」を得る
    for mod in (__name__, __name__.split(".")[-1]):
        try:
            aid = mw.addonManager.addonFromModule(mod)
            if aid:
                return aid
        except Exception:
            pass
    # 開発中フォールバック（フォルダ名）
    return "bar_graph"


# -------------------- defaults / config helpers --------------------

def _addon_dir() -> str:
    # addonManagerに頼らず、実ファイルの場所を使う（最強）
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except Exception:
        return ""


def _config_path() -> str:
    d = _addon_dir()
    return os.path.join(d, "config.json") if d else ""


def _defaults() -> dict[str, Any]:
    return {
        "enabled": True,

        # Data / goal
        "goal_per_day": 200,          # 目標（1日あたりのレビュー回数/学習量の目安）
        "show_goal_line": True,       # 目標線を表示するか

        # Range
        "range_days": 30,            # 7 / 30 / 90 / 180 / 365 推奨

        # Layout
        "chart_height_px": 140,
        "chart_width_vw": 75,         # 例: 75 => 75vw
        "chart_min_width_px": 600,
        "chart_max_width_px": 1100,
        "tick_label_padding_left_px": 34,

        # Bars (auto-fit)
        "bar_gap_px": 4,
        "bar_min_px": 6,
        "bar_max_px": 28,

        # Style (colors) — soft / eye-friendly
        "container_border_rgba": "rgba(120,160,235,0.25)",
        "tick_rgba": "rgba(120,160,235,0.28)",
        "bar_rgba": "rgba(120,160,235,0.55)",

        # 今日（赤系・薄め）
        "today_bar_rgba": "rgba(235,120,120,0.80)",
        "today_outline_rgba": "rgba(200,90,90,0.55)",

        # ゴール線（青系のまま少し控えめ）
        "goal_line_rgba": "rgba(120,160,235,0.75)",
        "goal_label_opacity": 0.90,

        # ゴール達成（過去の中で少し濃い青：同系統で達成感）
        "goal_met_bar_rgba": "rgba(90,135,230,0.75)",
        "goal_met_outline_rgba": "rgba(70,110,200,0.45)",

        # 今日 + ゴール達成（赤を少し濃く：被らない）
        "today_goal_bar_rgba": "rgba(220,90,90,0.90)",
        "today_goal_outline_rgba": "rgba(180,70,70,0.65)",
    }


def _get_conf() -> dict[str, Any]:
    # まずファイルから読む（これが本命）
    try:
        p = _config_path()
        if p and os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                c = json.load(f)
            return c if isinstance(c, dict) else {}
    except Exception:
        pass

    # ついでにAnki標準からも読めたら読む
    try:
        aid = _addon_id()
        c = mw.addonManager.getConfig(aid)
        return c if isinstance(c, dict) else {}
    except Exception:
        return {}


def _write_conf(c: dict[str, Any]) -> None:
    # まず確実にファイルへ保存（これが本命）
    try:
        p = _config_path()
        d = _addon_dir()
        if p and d:
            os.makedirs(d, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(c, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    # ついでにAnki標準にも書けたら書く（効く環境では効く）
    try:
        aid = _addon_id()
        mw.addonManager.writeConfig(aid, c)
    except Exception:
        pass


def _get_config_merged() -> dict[str, Any]:
    d = _defaults()
    c = _get_conf()
    if isinstance(c, dict):
        d.update(c)
    return d


def _cfg(key: str, default: Any) -> Any:
    return _get_config_merged().get(key, default)


# -------------------- data aggregation (cached) --------------------

def _today_key() -> str:
    return datetime.now().date().isoformat()


def _compute_last_n_days_counts(days: int) -> List[int]:
    """直近N日（今日含む）のrevlog行数を日別に集計（DBでgroup byして軽量化）。"""
    if not mw.col:
        return [0] * max(1, days)

    days = int(days)
    if days < 1:
        days = 1

    today = datetime.now().date()
    start_day = today - timedelta(days=days - 1)

    start_dt = datetime.combine(start_day, datetime.min.time())
    end_dt = datetime.combine(today + timedelta(days=1), datetime.min.time())

    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000) - 1

    # day_key: Unix ms -> 日単位に丸めたキー（UTC基準のズレは「日別傾向」用途なら許容）
    # もし「ローカル日付」厳密が必要なら、オフセット補正を入れる（通常は不要）。
    rows = mw.col.db.all(
        """
        SELECT (id / 86400000) AS day_key, COUNT(*) AS cnt
        FROM revlog
        WHERE id BETWEEN ? AND ?
        GROUP BY day_key
        """,
        start_ms, end_ms,
    )

    counts = [0] * days
    start_key = start_ms // 86400000

    for day_key, cnt in rows:
        try:
            idx = int(day_key) - int(start_key)
        except Exception:
            continue
        if 0 <= idx < days:
            try:
                counts[idx] = int(cnt)
            except Exception:
                counts[idx] = 0

    return counts


def _get_cached_counts(force: bool = False) -> List[int]:
    if not bool(_cfg("enabled", True)):
        return [0] * int(_cfg("range_days", 30) or 30)

    days = int(_cfg("range_days", 30) or 30)
    if days < 1:
        days = 1

    c = _get_conf()
    cache_key = str(c.get("cache_key", ""))
    cache_counts = c.get("cache_counts")

    key_now = f"{_today_key()}:{days}"

    if (not force) and cache_key == key_now and isinstance(cache_counts, list) and len(cache_counts) == days:
        try:
            return [int(x) for x in cache_counts]
        except Exception:
            pass

    counts = _compute_last_n_days_counts(days)
    c["cache_key"] = key_now
    c["cache_counts"] = counts
    _write_conf(c)
    return counts


# -------------------- rendering (ultra-light) --------------------

def _render_bar_chart_html(counts: List[int]) -> str:
    conf = _get_config_merged()

    days = max(1, int(conf.get("range_days", 30) or 30))
    counts = (counts + [0] * days)[:days]
    maxv = max(counts) if counts else 0

    chart_h = int(conf.get("chart_height_px", 140))
    chart_width_vw = int(conf.get("chart_width_vw", 75))
    min_w = int(conf.get("chart_min_width_px", 600))
    max_w = int(conf.get("chart_max_width_px", 1100))
    pad_left = int(conf.get("tick_label_padding_left_px", 34))

    goal = int(conf.get("goal_per_day", 200) or 0)
    show_goal = bool(conf.get("show_goal_line", True))

    # 目標線がスケールからはみ出ないように、スケール上限を調整
    scale_max = max(1, maxv, goal if show_goal else 0)
    midv = int(round(scale_max / 2))

    total = sum(counts)
    title = f"Last {days} days: {total} reviews"

    today = datetime.now().date()
    start_day = today - timedelta(days=days - 1)

    def h(v: int) -> int:
        return max(1, int(chart_h * (v / scale_max))) if scale_max > 0 else 1

    bars = []
    for i, v in enumerate(counts):
        d = (start_day + timedelta(days=i)).isoformat()
        cls = "lm-bar"
        if goal > 0 and v >= goal:
            cls += " lm-goalmet"
        if i == (days - 1):
            cls += " lm-today"
        bars.append(
            f"<div class='{cls}' data-date='{d}' data-count='{v}' style='height:{h(v)}px;'></div>"
        )

    # goal line position
    goal_bottom_pct = 0.0
    if show_goal and scale_max > 0:
        goal_bottom_pct = max(0.0, min(100.0, (goal / scale_max) * 100.0))

    # colors
    dft = _defaults()
    container_border = str(conf.get("container_border_rgba", dft["container_border_rgba"]))
    tick_rgba = str(conf.get("tick_rgba", dft["tick_rgba"]))
    bar_rgba = str(conf.get("bar_rgba", dft["bar_rgba"]))
    today_bar = str(conf.get("today_bar_rgba", dft["today_bar_rgba"]))
    today_outline = str(conf.get("today_outline_rgba", dft["today_outline_rgba"]))
    goal_line = str(conf.get("goal_line_rgba", dft["goal_line_rgba"]))
    goal_label_opacity = float(conf.get("goal_label_opacity", dft["goal_label_opacity"]))
    goal_met_bar = str(conf.get("goal_met_bar_rgba", dft["goal_met_bar_rgba"]))
    goal_met_outline = str(conf.get("goal_met_outline_rgba", dft["goal_met_outline_rgba"]))
    today_goal_bar = str(conf.get("today_goal_bar_rgba", dft["today_goal_bar_rgba"]))
    today_goal_outline = str(conf.get("today_goal_outline_rgba", dft["today_goal_outline_rgba"]))

    # bar sizing
    bar_gap = int(conf.get("bar_gap_px", 4))
    bar_min = int(conf.get("bar_min_px", 6))
    bar_max = int(conf.get("bar_max_px", 28))

    return f"""
<div id="lm30-container">
  <div id="lm30-head">
    <div id="lm30-title">{title}</div>
    <div id="lm30-hover-val">—</div>
  </div>

  <div id="lm30-chartwrap" style="height:{chart_h}px;">
    <div class="lm30-tick lm30-t0"><span>0</span></div>
    <div class="lm30-tick lm30-t50"><span>{midv}</span></div>
    <div class="lm30-tick lm30-t100"><span>{scale_max}</span></div>

    {"<div class='lm30-goal' style='bottom:" + str(goal_bottom_pct) + "%;'><span>" + str(goal) + "</span></div>" if show_goal else ""}

    <div id="lm30-chart" style="height:{chart_h}px;">
      {''.join(bars)}
    </div>
  </div>
</div>

<style>
  #lm30-container {{
    margin: 14px auto;
    padding: 14px 16px;
    border: 1px solid {container_border};
    border-radius: 12px;
    max-width: 1200px;
  }}

  #lm30-head {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 10px;
  }}

  #lm30-title {{
    font-size: 14px;
    font-weight: 600;
    opacity: 0.95;
  }}

  #lm30-hover-val {{
    font-size: 12px;
    opacity: 0.7;
    white-space: nowrap;
    font-weight: 600;
  }}

  #lm30-chartwrap {{
    --lm30-chart-w: {chart_width_vw}vw;
    --lm30-bar-w: 14px;   /* JSで上書き */
    --lm30-gap: {bar_gap}px;

    position: relative;
    display: flex;
    justify-content: center;
  }}

  #lm30-chart {{
    width: var(--lm30-chart-w);
    max-width: {max_w}px;
    min-width: {min_w}px;

    display: flex;
    align-items: flex-end;
    justify-content: center;
    position: relative;
    overflow: hidden;

    padding-left: {pad_left}px;
  }}

  .lm30-tick {{
    position: absolute;
    left: 0;
    width: 100%;
    border-top: 1px dashed {tick_rgba};
    pointer-events: none;
  }}

  .lm30-tick span {{
    position: absolute;
    left: 0;
    top: -9px;
    font-size: 11px;
    opacity: 0.6;
  }}

  .lm30-t0   {{ bottom: 0; }}
  .lm30-t50  {{ bottom: 50%; }}
  .lm30-t100 {{ bottom: 100%; }}

  /* 目標線 */
  .lm30-goal {{
    position: absolute;
    left: 0;
    width: 100%;
    border-top: 2px solid {goal_line};
    pointer-events: none;
  }}
  .lm30-goal span {{
    position: absolute;
    left: 42px;
    top: -18px;
    font-size: 11px;
    font-weight: 600;
    opacity: {goal_label_opacity};
  }}

  .lm-bar {{
    display: block;
    width: var(--lm30-bar-w);
    margin-right: var(--lm30-gap);
    background: {bar_rgba};
    border-radius: 3px;
  }}

  #lm30-chart .lm-bar:last-child {{
    margin-right: 0;
  }}

  .lm-today {{
    background: {today_bar};
    outline: 1px solid {today_outline};
  }}

  /* ゴール以上のバー */
  .lm-goalmet {{
    background: {goal_met_bar};
    outline: 1px solid {goal_met_outline};
  }}

  /* 今日 + ゴール達成（最強状態） */
  .lm-today.lm-goalmet {{
    background: {today_goal_bar};
    outline: 2px solid {today_goal_outline};
  }}
</style>

<script>
(function() {{
  const root = document.getElementById("lm30-container");
  const out = document.getElementById("lm30-hover-val");
  if (!root || !out) return;

  root.addEventListener("mousemove", (e) => {{
    const t = e.target;
    if (!t || !t.classList || !t.classList.contains("lm-bar")) return;
    const c = t.getAttribute("data-count") || "";
    out.textContent = c; // 数字だけ
  }});

  root.addEventListener("mouseleave", () => {{
    out.textContent = "—";
  }});
}})();

(function() {{
  const wrap = document.getElementById("lm30-chartwrap");
  const chart = document.getElementById("lm30-chart");
  if (!wrap || !chart) return;

  function recompute() {{
    const w = chart.clientWidth;
    const n = {days};
    const gap = {bar_gap};
    const totalGap = gap * (n - 1);

    let bar = Math.floor((w - totalGap) / n);
    bar = Math.max({bar_min}, Math.min({bar_max}, bar));

    wrap.style.setProperty("--lm30-bar-w", bar + "px");
    wrap.style.setProperty("--lm30-gap", gap + "px");
  }}

  recompute();
  window.addEventListener("resize", recompute);
}})();
</script>
"""


# -------------------- hooks --------------------

def _mark_dirty(*args, **kwargs) -> None:
    global _DIRTY
    _DIRTY = True


def _reviewer_will_end() -> None:
    global _DIRTY
    if not _DIRTY:
        return
    _DIRTY = False
    _get_cached_counts(force=True)


def _on_webview_will_set_content(web_content, context) -> None:
    if not bool(_cfg("enabled", True)):
        return
    try:
        if context is None:
            return
        if context.__class__.__name__ != "DeckBrowser":
            return

        counts = _get_cached_counts()
        web_content.body += _render_bar_chart_html(counts)
    except Exception:
        return


def _install_hooks() -> None:
    if gui_hooks is not None:
        if hasattr(gui_hooks, "webview_will_set_content"):
            gui_hooks.webview_will_set_content.append(_on_webview_will_set_content)

        if hasattr(gui_hooks, "reviewer_did_answer_card"):
            gui_hooks.reviewer_did_answer_card.append(_mark_dirty)

        if hasattr(gui_hooks, "reviewer_will_end"):
            gui_hooks.reviewer_will_end.append(_reviewer_will_end)
        return

    try:
        from anki.hooks import addHook  # type: ignore
        addHook("webviewWillSetContent", lambda wc, ctx: _on_webview_will_set_content(wc, ctx))
        addHook("reviewerDidAnswerCard", lambda *a, **k: _mark_dirty(*a, **k))
        addHook("reviewerWillEnd", lambda: _reviewer_will_end())
    except Exception:
        pass


# -------------------- custom config GUI (no Tools button) --------------------

class ConfigDialog(QDialog):
    class RGBAPickerRow(QWidget):
        """
        RGBA picker row:
        - Pick… button (QColorDialog) for RGB
        - Alpha (%) spin for A
        - Preview swatch
        - Hidden QLineEdit that stores rgba(r,g,b,a) for backward-compatible save logic
        """
        def __init__(self, label: str, rgba_text: str, parent=None) -> None:
            super().__init__(parent)

            self._rgb = QColor(120, 160, 235)
            self._alpha_pct = 55

            lay = QHBoxLayout(self)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(8)

            self.pick_btn = QPushButton("Pick…")
            self.pick_btn.setFixedWidth(90)

            self.preview = QLabel()
            self.preview.setFixedSize(44, 20)
            self.preview.setFrameShape(QFrame.Shape.StyledPanel)

            self.alpha_spin = QSpinBox()
            self.alpha_spin.setRange(0, 100)
            self.alpha_spin.setFixedWidth(80)
            self.alpha_spin.setSuffix("%")

            self.hidden_le = QLineEdit()
            self.hidden_le.setVisible(False)

            lay.addWidget(self.pick_btn)
            lay.addWidget(self.preview)
            lay.addWidget(QLabel("Alpha"))
            lay.addWidget(self.alpha_spin)
            lay.addStretch(1)
            lay.addWidget(self.hidden_le)

            self.set_rgba_text(rgba_text)

            self.pick_btn.clicked.connect(self._pick_rgb)
            self.alpha_spin.valueChanged.connect(lambda _v: self._sync_to_text())

        @staticmethod
        def _parse_rgba(s: str) -> tuple[QColor, int]:
            # rgba(r,g,b,a) where a is 0..1
            t = (s or "").strip()
            import re
            m = re.match(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)$", t)
            if m:
                r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
                a = float(m.group(4))
                a = max(0.0, min(1.0, a))
                a_pct = int(round(a * 100))
                return QColor(r, g, b), a_pct
            return QColor(120, 160, 235), 55

        @staticmethod
        def _fmt_rgba(c: QColor, a_pct: int) -> str:
            a = max(0.0, min(1.0, a_pct / 100.0))
            return f"rgba({c.red()},{c.green()},{c.blue()},{a:.2f})"

        def _set_preview(self) -> None:
            c = QColor(self._rgb)
            alpha = int(round(255 * (self._alpha_pct / 100.0)))
            c.setAlpha(alpha)
            # HexArgb: #AARRGGBB
            self.preview.setStyleSheet(f"background-color: {c.name(QColor.NameFormat.HexArgb)};")

        def _sync_to_text(self) -> None:
            self._alpha_pct = int(self.alpha_spin.value())
            self.hidden_le.setText(self._fmt_rgba(self._rgb, self._alpha_pct))
            self._set_preview()

        def _pick_rgb(self) -> None:
            col = QColorDialog.getColor(self._rgb, self, "Pick Color")
            if not col.isValid():
                return
            self._rgb = QColor(col.red(), col.green(), col.blue())
            self._sync_to_text()

        def set_rgba_text(self, rgba_text: str) -> None:
            self._rgb, self._alpha_pct = self._parse_rgba(rgba_text)
            self.alpha_spin.setValue(self._alpha_pct)
            self.hidden_le.setText(self._fmt_rgba(self._rgb, self._alpha_pct))
            self._set_preview()

        def rgba_text(self) -> str:
            return str(self.hidden_le.text()).strip()


    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Bar Graph - Settings")
        self.setMinimumWidth(720)

        self._conf = _get_config_merged()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        tabs = QTabWidget()
        root.addWidget(tabs)

        # -------------------- tab: General --------------------
        tab_general = QWidget()
        gl = QVBoxLayout(tab_general)
        gl.setContentsMargins(12, 12, 12, 12)
        gl.setSpacing(12)

        box_general = QGroupBox("General")
        form_g = QFormLayout(box_general)
        form_g.setVerticalSpacing(10)

        self.enabled_cb = QCheckBox()
        self.enabled_cb.setChecked(bool(self._conf.get("enabled", True)))
        form_g.addRow("Enable", self.enabled_cb)

        self.goal_spin = QSpinBox()
        self.goal_spin.setRange(0, 999999)
        self.goal_spin.setValue(int(self._conf.get("goal_per_day", 200) or 0))
        form_g.addRow("Goal per day", self.goal_spin)

        self.goal_line_cb = QCheckBox()
        self.goal_line_cb.setChecked(bool(self._conf.get("show_goal_line", True)))
        form_g.addRow("Show goal line", self.goal_line_cb)

        self.range_combo = QComboBox()
        self.range_combo.addItem("7 days", 7)
        self.range_combo.addItem("30 days", 30)
        self.range_combo.addItem("3 months (90 days)", 90)
        self.range_combo.addItem("6 months (180 days)", 180)
        self.range_combo.addItem("1 year (365 days)", 365)

        allowed = {7, 30, 90, 180, 365}
        cur_days = int(self._conf.get("range_days", 30) or 30)
        if cur_days not in allowed:
            cur_days = 30
            self._conf["range_days"] = 30

        i = self.range_combo.findData(cur_days)
        self.range_combo.setCurrentIndex(i if i >= 0 else 1)

        form_g.addRow("Range", self.range_combo)

        gl.addWidget(box_general)
        gl.addStretch(1)

        tabs.addTab(tab_general, "General")

        # -------------------- tab: Layout --------------------
        tab_layout = QWidget()
        ll = QVBoxLayout(tab_layout)
        ll.setContentsMargins(12, 12, 12, 12)
        ll.setSpacing(12)

        box_layout = QGroupBox("Layout")
        form_l = QFormLayout(box_layout)
        form_l.setVerticalSpacing(10)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(40, 500)
        self.height_spin.setValue(int(self._conf.get("chart_height_px", 140)))
        form_l.addRow("Chart height (px)", self.height_spin)

        self.width_vw_spin = QSpinBox()
        self.width_vw_spin.setRange(30, 100)
        self.width_vw_spin.setValue(int(self._conf.get("chart_width_vw", 75)))
        form_l.addRow("Chart width (vw)", self.width_vw_spin)

        self.minw_spin = QSpinBox()
        self.minw_spin.setRange(200, 3000)
        self.minw_spin.setValue(int(self._conf.get("chart_min_width_px", 600)))
        form_l.addRow("Min width (px)", self.minw_spin)

        self.maxw_spin = QSpinBox()
        self.maxw_spin.setRange(200, 4000)
        self.maxw_spin.setValue(int(self._conf.get("chart_max_width_px", 1100)))
        form_l.addRow("Max width (px)", self.maxw_spin)

        ll.addWidget(box_layout)
        ll.addStretch(1)

        tabs.addTab(tab_layout, "Layout")

        # -------------------- tab: Bars --------------------
        tab_bars = QWidget()
        bl = QVBoxLayout(tab_bars)
        bl.setContentsMargins(12, 12, 12, 12)
        bl.setSpacing(12)

        box_bars = QGroupBox("Bars")
        form_b = QFormLayout(box_bars)
        form_b.setVerticalSpacing(10)

        self.gap_spin = QSpinBox()
        self.gap_spin.setRange(0, 50)
        self.gap_spin.setValue(int(self._conf.get("bar_gap_px", 4)))
        form_b.addRow("Gap (px)", self.gap_spin)

        self.bmin_spin = QSpinBox()
        self.bmin_spin.setRange(1, 60)
        self.bmin_spin.setValue(int(self._conf.get("bar_min_px", 6)))
        form_b.addRow("Min bar width (px)", self.bmin_spin)

        self.bmax_spin = QSpinBox()
        self.bmax_spin.setRange(1, 80)
        self.bmax_spin.setValue(int(self._conf.get("bar_max_px", 28)))
        form_b.addRow("Max bar width (px)", self.bmax_spin)

        bl.addWidget(box_bars)
        bl.addStretch(1)

        tabs.addTab(tab_bars, "Bars")

        # -------------------- tab: Colors --------------------
        tab_colors = QWidget()
        cl = QVBoxLayout(tab_colors)
        cl.setContentsMargins(12, 12, 12, 12)
        cl.setSpacing(12)

        box_colors = QGroupBox("Colors")
        form_c = QFormLayout(box_colors)
        form_c.setVerticalSpacing(10)

        dft = _defaults()

        self.bar_picker = ConfigDialog.RGBAPickerRow(
            "Bar color",
            str(self._conf.get("bar_rgba", dft["bar_rgba"])),
        )
        form_c.addRow("Bar color", self.bar_picker)

        self.today_picker = ConfigDialog.RGBAPickerRow(
            "Today bar color",
            str(self._conf.get("today_bar_rgba", dft["today_bar_rgba"])),
        )
        form_c.addRow("Today bar color", self.today_picker)

        self.goal_line_picker = ConfigDialog.RGBAPickerRow(
            "Goal line color",
            str(self._conf.get("goal_line_rgba", dft["goal_line_rgba"])),
        )
        form_c.addRow("Goal line color", self.goal_line_picker)

        self.tick_picker = ConfigDialog.RGBAPickerRow(
            "Tick line color",
            str(self._conf.get("tick_rgba", dft["tick_rgba"])),
        )
        form_c.addRow("Tick line color", self.tick_picker)

        self.goalmet_picker = ConfigDialog.RGBAPickerRow(
            "Goal-met bar color",
            str(self._conf.get("goal_met_bar_rgba", dft["goal_met_bar_rgba"])),
        )
        form_c.addRow("Goal-met bar color", self.goalmet_picker)

        self.goalmet_outline_picker = ConfigDialog.RGBAPickerRow(
            "Goal-met outline",
            str(self._conf.get("goal_met_outline_rgba", dft["goal_met_outline_rgba"])),
        )
        form_c.addRow("Goal-met outline", self.goalmet_outline_picker)

        self.today_goal_picker = ConfigDialog.RGBAPickerRow(
            "Today + Goal bar color",
            str(self._conf.get("today_goal_bar_rgba", dft["today_goal_bar_rgba"])),
        )
        form_c.addRow("Today + Goal bar color", self.today_goal_picker)

        self.today_goal_outline_picker = ConfigDialog.RGBAPickerRow(
            "Today + Goal outline",
            str(self._conf.get("today_goal_outline_rgba", dft["today_goal_outline_rgba"])),
        )
        form_c.addRow("Today + Goal outline", self.today_goal_outline_picker)

        cl.addWidget(box_colors)
        cl.addStretch(1)

        tabs.addTab(tab_colors, "Colors")

        # -------------------- buttons --------------------
        btns = QHBoxLayout()
        btns.addStretch(1)

        self.reset_btn = QPushButton("Reset to defaults")
        self.reset_btn.clicked.connect(self.on_reset)
        btns.addWidget(self.reset_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("Save")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        btns.addWidget(self.ok_btn)

        root.addLayout(btns)

    def on_reset(self) -> None:
        d = _defaults()
        self.enabled_cb.setChecked(bool(d["enabled"]))
        self.goal_spin.setValue(int(d["goal_per_day"]))
        self.goal_line_cb.setChecked(bool(d["show_goal_line"]))
        allowed = {7, 30, 90, 180, 365}
        range_days = int(d.get("range_days", 30) or 30)
        if range_days not in allowed:
            range_days = 30

        idx = self.range_combo.findData(range_days)
        self.range_combo.setCurrentIndex(idx if idx >= 0 else 1)

        self.height_spin.setValue(int(d["chart_height_px"]))
        self.width_vw_spin.setValue(int(d["chart_width_vw"]))
        self.minw_spin.setValue(int(d["chart_min_width_px"]))
        self.maxw_spin.setValue(int(d["chart_max_width_px"]))

        self.gap_spin.setValue(int(d["bar_gap_px"]))
        self.bmin_spin.setValue(int(d["bar_min_px"]))
        self.bmax_spin.setValue(int(d["bar_max_px"]))

        self.bar_picker.set_rgba_text(str(d["bar_rgba"]))
        self.today_picker.set_rgba_text(str(d["today_bar_rgba"]))
        self.goal_line_picker.set_rgba_text(str(d["goal_line_rgba"]))
        self.tick_picker.set_rgba_text(str(d["tick_rgba"]))

        self.goalmet_picker.set_rgba_text(str(d["goal_met_bar_rgba"]))
        self.goalmet_outline_picker.set_rgba_text(str(d["goal_met_outline_rgba"]))

        self.today_goal_picker.set_rgba_text(str(d["today_goal_bar_rgba"]))
        self.today_goal_outline_picker.set_rgba_text(str(d["today_goal_outline_rgba"]))


    def get_new_conf(self) -> dict[str, Any]:
        c = _get_config_merged()

        c["enabled"] = bool(self.enabled_cb.isChecked())
        c["goal_per_day"] = int(self.goal_spin.value())
        c["show_goal_line"] = bool(self.goal_line_cb.isChecked())
        c["range_days"] = int(self.range_combo.currentData() or 30)

        c["chart_height_px"] = int(self.height_spin.value())
        c["chart_width_vw"] = int(self.width_vw_spin.value())
        c["chart_min_width_px"] = int(self.minw_spin.value())
        c["chart_max_width_px"] = int(self.maxw_spin.value())

        c["bar_gap_px"] = int(self.gap_spin.value())
        c["bar_min_px"] = int(self.bmin_spin.value())
        c["bar_max_px"] = int(self.bmax_spin.value())

        c["bar_rgba"] = self.bar_picker.rgba_text()
        c["today_bar_rgba"] = self.today_picker.rgba_text()
        c["goal_line_rgba"] = self.goal_line_picker.rgba_text()
        c["tick_rgba"] = self.tick_picker.rgba_text()

        c["goal_met_bar_rgba"] = self.goalmet_picker.rgba_text()
        c["goal_met_outline_rgba"] = self.goalmet_outline_picker.rgba_text()

        c["today_goal_bar_rgba"] = self.today_goal_picker.rgba_text()
        c["today_goal_outline_rgba"] = self.today_goal_outline_picker.rgba_text()

        return c


def _show_config_dialog() -> None:
    dlg = ConfigDialog(mw)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        new_conf = dlg.get_new_conf()
        _write_conf(new_conf)

def _install_config_action() -> None:
    # 「アドオン設定画面の Config ボタン」から開く（Toolsメニューは増やさない）
    try:
        mw.addonManager.setConfigAction(_addon_id(), _show_config_dialog)
    except Exception:
        pass

def _ensure_config_defaults() -> None:
    try:
        aid = _addon_id()
        mw.addonManager.setConfigDefaults(aid, _defaults())
    except Exception:
        pass

_ensure_config_defaults()
_install_hooks()
_install_config_action()
