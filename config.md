# Bar Graph (Last 30 Days) – Configuration Guide

This document explains all configuration options available for the **Bar Graph (Last 30 Days)** Anki add-on.

You can edit these settings either:
- via the **custom Settings GUI** (recommended), or
- by editing `config.json` directly (advanced users).

---

## Location of `config.json`

The configuration file is stored next to the add-on code:

```
Anki2/<profile>/addons21/<addon_folder>/config.json
```

Examples:
- Local install: `addons21/bar_graph/config.json`
- AnkiWeb install: `addons21/1234567890/config.json`

---

## General

### `enabled`
- **Type:** boolean
- **Default:** `true`
- **Description:**
  Enable or disable the entire graph display.

### `goal_per_day`
- **Type:** integer
- **Default:** `200`
- **Description:**
  Target number of reviews per day. Used to draw the goal line and to highlight goal-achieved bars.

### `show_goal_line`
- **Type:** boolean
- **Default:** `true`
- **Description:**
  Whether to display a horizontal goal line on the chart.

---

## Layout

### `chart_height_px`
- **Type:** integer
- **Default:** `140`
- **Description:**
  Height of the bar chart in pixels.

### `chart_width_vw`
- **Type:** integer
- **Default:** `75`
- **Description:**
  Chart width as a percentage of the window width (`vw`).
  Recommended range: `60–85`.

### `chart_min_width_px`
- **Type:** integer
- **Default:** `600`
- **Description:**
  Minimum chart width in pixels. Prevents the graph from becoming too narrow.

### `chart_max_width_px`
- **Type:** integer
- **Default:** `1100`
- **Description:**
  Maximum chart width in pixels. Prevents the graph from stretching too wide.

---

## Bars

### `bar_gap_px`
- **Type:** integer
- **Default:** `4`
- **Description:**
  Horizontal gap between bars in pixels.

### `bar_min_px`
- **Type:** integer
- **Default:** `6`
- **Description:**
  Minimum bar width in pixels (used during auto-fitting).

### `bar_max_px`
- **Type:** integer
- **Default:** `28`
- **Description:**
  Maximum bar width in pixels (used during auto-fitting).

---

## Colors (RGBA)

All colors use standard CSS `rgba(r,g,b,a)` notation.

### `bar_rgba`
- **Default:** `rgba(120,160,235,0.55)`
- **Description:**
  Base color for past (non-today) bars.

### `goal_met_bar_rgba`
- **Default:** `rgba(90,135,230,0.75)`
- **Description:**
  Color for bars that meet or exceed the daily goal (past days).

### `goal_met_outline_rgba`
- **Default:** `rgba(70,110,200,0.45)`
- **Description:**
  Outline color for goal-achieved bars.

### `today_bar_rgba`
- **Default:** `rgba(235,120,120,0.80)`
- **Description:**
  Color for today's bar.

### `today_outline_rgba`
- **Default:** `rgba(200,90,90,0.55)`
- **Description:**
  Outline color for today's bar.

### `today_goal_bar_rgba`
- **Default:** `rgba(220,90,90,0.90)`
- **Description:**
  Color for **today's bar when the daily goal is achieved**.

### `today_goal_outline_rgba`
- **Default:** `rgba(180,70,70,0.65)`
- **Description:**
  Outline color for **today + goal achieved** bars.

### `goal_line_rgba`
- **Default:** `rgba(120,160,235,0.75)`
- **Description:**
  Color of the horizontal goal line.

### `goal_label_opacity`
- **Type:** float
- **Default:** `0.90`
- **Description:**
  Opacity of the goal label text.

### `tick_rgba`
- **Default:** `rgba(120,160,235,0.28)`
- **Description:**
  Color of grid/tick lines.

---

## Notes

- Bars are automatically resized to fit the available width.
- Configuration changes take effect immediately after saving.
- If `config.json` is deleted, defaults will be recreated automatically.

---

## Example `config.json`

```json
{
  "enabled": true,
  "goal_per_day": 200,
  "show_goal_line": true,
  "chart_height_px": 140,
  "chart_width_vw": 75,
  "bar_gap_px": 4,
  "bar_rgba": "rgba(120,160,235,0.55)",
  "today_bar_rgba": "rgba(235,120,120,0.80)"
}
```

---

If you encounter issues, try resetting settings via **Reset to defaults** in the settings dialog.