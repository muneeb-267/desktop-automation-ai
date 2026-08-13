"""Application stylesheet — calm light academic desktop look."""

LIGHT_THEME = """
* {
    font-family: "Segoe UI", "IBM Plex Sans", "Source Sans 3", "Noto Sans", sans-serif;
    font-size: 13px;
    color: #1f2a30;
}

QMainWindow, QDialog {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #eef3f6, stop:0.45 #f7fafb, stop:1 #e7eef2);
}

#headerBar, #loginCard {
    background: rgba(255, 255, 255, 0.92);
    border-bottom: 1px solid #d5dee4;
}

#loginCard {
    border: 1px solid #d5dee4;
    border-radius: 10px;
}

#appTitle {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 0.2px;
    color: #0f3d4c;
}

#appSubtitle {
    color: #5b6b73;
    font-size: 12px;
}

#statusBadge {
    padding: 4px 12px;
    border-radius: 4px;
    background: #e6eef2;
    color: #35505c;
    font-weight: 600;
    min-width: 90px;
}
#statusBadge[status="idle"] { background: #e6eef2; color: #35505c; }
#statusBadge[status="running"] { background: #d9f0e4; color: #146c43; }
#statusBadge[status="error"] { background: #fde2e1; color: #9b2226; }
#statusBadge[status="success"] { background: #d9f0e4; color: #146c43; }

QPushButton {
    background: #0f6b7a;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover { background: #0c5966; }
QPushButton:disabled { background: #9bb4bb; color: #eef4f6; }
QPushButton#btnSecondary, QPushButton#btnQuick {
    background: #ffffff;
    color: #0f3d4c;
    border: 1px solid #c5d2d8;
}
QPushButton#btnSecondary:hover, QPushButton#btnQuick:hover {
    background: #f2f7f9;
}
QPushButton#btnDanger {
    background: #b42318;
}
QPushButton#btnDanger:hover { background: #912018; }
QPushButton#btnMic {
    background: #c45c26;
    min-width: 42px;
}
QPushButton#btnMic:hover { background: #a34b1e; }
QPushButton#btnMic[listening="true"] { background: #8a3414; }

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QListWidget {
    background: #ffffff;
    border: 1px solid #c9d5db;
    border-radius: 6px;
    padding: 7px 9px;
    selection-background-color: #b7dde4;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #0f6b7a;
}

QTabWidget::pane {
    border: 1px solid #d5dee4;
    border-radius: 8px;
    background: rgba(255,255,255,0.88);
    top: -1px;
}
QTabBar::tab {
    background: #e4ecef;
    border: 1px solid #d5dee4;
    border-bottom: none;
    padding: 8px 16px;
    margin-right: 3px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: #40555e;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #0f3d4c;
    font-weight: 600;
}

QGroupBox {
    border: 1px solid #d5dee4;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 10px;
    background: rgba(255,255,255,0.7);
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #0f3d4c;
}

QCheckBox { spacing: 8px; }
QStatusBar { background: #e8eef1; color: #40555e; }
QSplitter::handle { background: #d5dee4; }

#feedFrame, #logFrame {
    background: #102227;
    border-radius: 8px;
    border: 1px solid #234049;
}
#feedLabel {
    color: #d7e6ea;
    padding: 6px;
}
#sectionHint {
    color: #5b6b73;
    font-size: 12px;
}
"""
