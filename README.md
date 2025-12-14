# Bar Graph (Last 30 Days)

A lightweight Anki add-on that displays a **30-day review history bar graph** directly on the **Decks screen**.

This add-on is designed to give you an immediate visual overview of your recent study activity, without opening the Statistics window.

---

## Screenshot

![Decks screen – last 30 days bar graph](screenshots/screenshot-1.png)

---

## Features

* 📊 Shows **review counts for the last 30 days** on the Decks screen
* ⚡ **Very lightweight**: minimal queries, cached results
* 🔄 Updates automatically after review sessions
* 🎯 Optional **daily goal line** with visual feedback
* 🎨 Clear color coding:

  * Past days: blue tones
  * Goal achieved: stronger blue
  * Today: red tone
  * Today + goal achieved: emphasized red
* 🖱️ Hover to display exact review counts
* 📐 Responsive layout (window-width based)
* 🧩 Built-in **custom settings GUI** (no extra Tools menu entries)

---

## Installation

### Option 1: AnkiWeb (recommended)

1. Open Anki
2. Go to **Tools → Add-ons → Get Add-ons**
3. Enter the add-on code (from AnkiWeb)
4. Restart Anki

### Option 2: Manual installation

1. Download the add-on files
2. Place them in:

   ```
   Anki2/<profile>/addons21/bar_graph/
   ```
3. Restart Anki

---

## Usage

* The graph appears automatically on the **Decks screen**.
* No action is required during normal use.
* Data is refreshed after review sessions.

---

## Configuration

All settings are available via:

**Tools → Add-ons → Bar Graph (Last 30 Days) → Config**

You can configure:

* Enable / disable the graph
* Daily review goal
* Chart size and layout
* Bar spacing and width limits
* Full color customization (RGBA)

For detailed explanations, see **`config.md`**.

---

## Compatibility

* Anki 24.x
* Anki 25.x
* Windows / macOS / Linux

---

## Performance Notes

* Only the last 30 days of review data are queried
* Results are cached to avoid repeated database access
* No background timers or polling

This ensures negligible performance impact even on large collections.

---

## License

MIT License

---

## Author

Created by @yuwayanagitani

---

## Notes

* If `config.json` is deleted, it will be automatically recreated with default values.
* The add-on does not modify cards, decks, or scheduling behavior.
