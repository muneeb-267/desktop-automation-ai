"""Custom dark QSS stylesheet for AI Desktop Automation Suite."""

DARK_THEME = """
/* ── Global ─────────────────────────────────────────────── */
* {
    font-family: "Segoe UI", "Ubuntu", "Cantarell", sans-serif;
    font-size: 13px;
    outline: none;
}

QMainWindow, QWidget {
    background-color: #0f1117;
    color: #e4e6eb;
}

QLabel {
    background: transparent;
    color: #e4e6eb;
}

/* ── Header ─────────────────────────────────────────────── */
#headerBar {
    background-color: #161b22;
    border-bottom: 1px solid #2a3140;
    min-height: 56px;
    max-height: 56px;
}

#appTitle {
    font-size: 18px;
    font-weight: 700;
    color: #f0f3f8;
    letter-spacing: 0.3px;
}

#statusBadge {
    font-size: 12px;
    font-weight: 600;
    padding: 4px 14px;
    border-radius: 4px;
    border: 1px solid #3a4255;
    background-color: #1c2230;
    color: #9aa3b5;
}

#statusBadge[status="idle"] {
    background-color: #1c2230;
    border-color: #3a4255;
    color: #9aa3b5;
}

#statusBadge[status="active"] {
    background-color: #0d2e24;
    border-color: #1f9d6e;
    color: #3ddeaa;
}

#statusBadge[status="error"] {
    background-color: #2e1218;
    border-color: #c0392b;
    color: #ff6b6b;
}

/* ── Buttons ────────────────────────────────────────────── */
QPushButton {
    background-color: #1c2230;
    color: #e4e6eb;
    border: 1px solid #2a3140;
    border-radius: 4px;
    padding: 7px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #252d3d;
    border-color: #3ddeaa;
}

QPushButton:pressed {
    background-color: #151a24;
}

QPushButton:disabled {
    background-color: #141820;
    color: #4a5160;
    border-color: #1e2430;
}

QPushButton#btnStart {
    background-color: #0d2e24;
    border-color: #1f9d6e;
    color: #3ddeaa;
    font-weight: 600;
}

QPushButton#btnStart:hover {
    background-color: #134035;
    border-color: #3ddeaa;
}

QPushButton#btnStart:disabled {
    background-color: #141820;
    border-color: #1e2430;
    color: #4a5160;
}

QPushButton#btnStop {
    background-color: #2e1218;
    border-color: #c0392b;
    color: #ff6b6b;
    font-weight: 600;
}

QPushButton#btnStop:hover {
    background-color: #3d1820;
    border-color: #ff6b6b;
}

QPushButton#btnStop:disabled {
    background-color: #141820;
    border-color: #1e2430;
    color: #4a5160;
}

QPushButton#btnQuick {
    padding: 5px 12px;
    font-size: 12px;
}

QPushButton#btnQuick[active="true"] {
    background-color: #0d2e24;
    border-color: #1f9d6e;
    color: #3ddeaa;
}

/* ── Panels & Frames ────────────────────────────────────── */
#feedPanel, #controlsPanel, #logsPanel {
    background-color: #141820;
    border: 1px solid #2a3140;
    border-radius: 6px;
}

#panelHeader {
    font-size: 12px;
    font-weight: 600;
    color: #7a8499;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    padding: 2px 0;
}

/* ── Tabs ───────────────────────────────────────────────── */
QTabWidget::pane {
    background-color: #141820;
    border: 1px solid #2a3140;
    border-radius: 0 0 4px 4px;
    top: -1px;
}

QTabBar::tab {
    background-color: #1c2230;
    color: #7a8499;
    border: 1px solid #2a3140;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 7px 18px;
    margin-right: 2px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #141820;
    color: #3ddeaa;
    border-color: #2a3140;
    border-bottom: 1px solid #141820;
}

QTabBar::tab:hover:!selected {
    color: #e4e6eb;
    background-color: #252d3d;
}

/* ── Form Controls ──────────────────────────────────────── */
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #0f1117;
    color: #e4e6eb;
    border: 1px solid #2a3140;
    border-radius: 4px;
    padding: 6px 10px;
    selection-background-color: #1f9d6e;
}

QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #3ddeaa;
}

QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #3ddeaa;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #7a8499;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #1c2230;
    color: #e4e6eb;
    border: 1px solid #2a3140;
    selection-background-color: #0d2e24;
    selection-color: #3ddeaa;
    outline: none;
}

QSlider::groove:horizontal {
    height: 4px;
    background: #2a3140;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #3ddeaa;
    border: none;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}

QSlider::sub-page:horizontal {
    background: #1f9d6e;
    border-radius: 2px;
}

QCheckBox {
    color: #e4e6eb;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #2a3140;
    border-radius: 3px;
    background-color: #0f1117;
}

QCheckBox::indicator:checked {
    background-color: #1f9d6e;
    border-color: #3ddeaa;
}

QGroupBox {
    border: 1px solid #2a3140;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: #7a8499;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}

/* ── Splitter ───────────────────────────────────────────── */
QSplitter::handle {
    background-color: #2a3140;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

/* ── Scroll Bars ────────────────────────────────────────── */
QScrollBar:vertical {
    background: #0f1117;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #2a3140;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #3a4255;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: #0f1117;
    height: 8px;
}

QScrollBar::handle:horizontal {
    background: #2a3140;
    border-radius: 4px;
    min-width: 24px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Logs ───────────────────────────────────────────────── */
#logOutput {
    background-color: #0a0c10;
    color: #c8cdd8;
    border: 1px solid #2a3140;
    border-radius: 4px;
    font-family: "Cascadia Code", "Fira Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
    padding: 6px;
    selection-background-color: #1f9d6e;
}

/* ── Feed Overlay Labels ────────────────────────────────── */
#feedPlaceholder {
    color: #4a5160;
    font-size: 14px;
}

#targetInfo {
    color: #3ddeaa;
    font-size: 11px;
    font-family: "Cascadia Code", "Fira Code", "Consolas", monospace;
}
"""
