# Bar Graph (Last 30 Days)

A lightweight Anki add-on that displays a **30‑day review history bar graph** directly on the **Decks screen**.

The graph is designed to be fast, unobtrusive, and informative at a glance, helping you understand your recent study volume without opening the Statistics window.

---

## Features

- 📊 **Last 30 days bar graph** shown on the Decks screen
- ⚡ **Ultra‑lightweight**: only 30 bars, cached data, no heavy queries
- 🔄 **Updates automatically after review sessions**
- 🎯 **Daily goal line** with visual feedback
- 🎨 **Clear visual states**:
  - Past days (blue)
  - Goal achieved days (stronger blue)
  - Today (red)
  - Today + goal achieved (strong red)
- 🖱️ **Hover to see exact review counts**
- 📐 **Responsive layout** (auto‑fit bar width, window‑based sizing)
- 🧩 **Custom settings GUI** (no extra Tools menu entries)

---

## How It Works

- The add-on reads review counts from Anki’s `revlog`.
- Data is aggregated **once per review session** and cached.
- The Decks screen displays the graph using lightweight HTML/CSS/JS.
- No background timers or continuous polling are used.

This ensures minimal performance impact, even on large collections.

---

## Configuration

All settings are available via the **Add-ons → Config** button:

- Enable / disable the graph
- Daily review goal
- Chart size and layout
- Bar spacing and auto-fit limits
- Full color customization (RGBA)

See **`config.md`** for a complete list of configuration options.

---

## Compatibility

- Anki **24 / 25** series
- Windows, macOS, Linux

---

## Notes

- If `config.json` is deleted, it will be recreated automatically with default values.
- The graph appears only on the **Decks screen** and does not affect study screens.

---

## License

MIT License

---

## Acknowledgements

Inspired by the desire for a quick, always‑visible overview of recent study habits, without relying on the Statistics window.

