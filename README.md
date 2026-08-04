# AI Desktop Automation Suite

Python + PyQt5 desktop GUI for AI-driven screen automation (OpenCV vision, OCR, and input control).

## Quick start

```bash
pip install -r requirements.txt
python main.py
```

## Layout

| Area | Module | Role |
|------|--------|------|
| Header | `main_window.py` | Title, status badge, quick actions |
| Left (60%) | `feed_widget.py` | Live vision feed + target boxes |
| Right (40%) | `controls_widget.py` | Task / OCR / params + Start/Stop |
| Bottom | `logs_widget.py` | Timestamped colored execution log |

Background work runs on `QThread` workers in `src/gui/workers.py` so the UI stays responsive. Capture and automation are stubbed with dummy data — replace the worker internals with real OpenCV / pytesseract / pyautogui calls when ready.

## Project structure

```
main.py
requirements.txt
src/
  gui/
    main_window.py
    styles.py
    workers.py
    components/
      feed_widget.py
      controls_widget.py
      logs_widget.py
```
