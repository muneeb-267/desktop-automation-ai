"""Automate AI wireframe-inspired light theme."""

APP_STYLE = """
* {
    font-family: "Segoe UI", "IBM Plex Sans", "Source Sans 3", "Noto Sans", sans-serif;
    color: #1a1d21;
    font-size: 13px;
}

QMainWindow, QDialog {
    background: #f3f4f6;
}

/* ── Login / Landing ───────────────────────── */
#landingRoot {
    background: #f3f4f6;
}
#brandPanel {
    background: #eef0f3;
}
#formPanel {
    background: #ffffff;
}
#brandLogo {
    font-size: 22px;
    font-weight: 800;
    color: #111827;
}
#brandEyebrow {
    color: #6b7280;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.2px;
}
#brandHeadline {
    font-size: 34px;
    font-weight: 800;
    color: #111827;
}
#brandHeadlineAccent {
    font-size: 34px;
    font-weight: 500;
    font-style: italic;
    color: #6b7280;
}
#brandBody {
    color: #4b5563;
    font-size: 14px;
}
#featureCard {
    background: #111827;
    border-radius: 14px;
    color: #f9fafb;
    padding: 18px;
}
#featureCardTitle {
    color: #ffffff;
    font-size: 18px;
    font-weight: 700;
}
#featureCardBody {
    color: #d1d5db;
    font-size: 12px;
}
#loginTitle {
    font-size: 26px;
    font-weight: 800;
}
#loginSubtitle {
    color: #6b7280;
}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 10px 12px;
    selection-background-color: #dbe4ee;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #111827;
}

QPushButton {
    background: #111827;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-weight: 700;
}
QPushButton:hover { background: #1f2937; }
QPushButton:disabled { background: #9ca3af; }
QPushButton#btnGhost, QPushButton#btnSecondary {
    background: #f3f4f6;
    color: #111827;
    border: 1px solid #d1d5db;
}
QPushButton#btnGhost:hover, QPushButton#btnSecondary:hover {
    background: #e5e7eb;
}
QPushButton#btnNav {
    background: transparent;
    color: #374151;
    text-align: left;
    padding: 12px 14px;
    border-radius: 10px;
    font-weight: 600;
}
QPushButton#btnNav:hover { background: #e5e7eb; }
QPushButton#btnNav[active="true"] {
    background: #e5e7eb;
    color: #111827;
    font-weight: 800;
}
QPushButton#btnMicBig {
    background: #111827;
    border-radius: 48px;
    min-width: 120px;
    min-height: 96px;
    max-width: 160px;
    max-height: 96px;
    font-size: 18px;
    font-weight: 800;
    padding: 8px 14px;
}
QPushButton#btnMicBig:disabled {
    background: #6b7280;
}
QPushButton#btnDanger {
    background: #b42318;
}

/* ── Shell ─────────────────────────────────── */
#sideBar {
    background: #ffffff;
    border-right: 1px solid #e5e7eb;
}
#sideBrand {
    font-size: 16px;
    font-weight: 800;
}
#topBar {
    background: #ffffff;
    border-bottom: 1px solid #e5e7eb;
}
#pageTitle {
    font-size: 26px;
    font-weight: 800;
}
#pageSubtitle {
    color: #6b7280;
    font-size: 13px;
}
#statusChip {
    background: #ecfdf3;
    color: #067647;
    border-radius: 12px;
    padding: 4px 10px;
    font-weight: 700;
}

/* Cards used as interactive / metric containers from wireframes */
#metricCard, #panelCard, #workflowCard, #voicePanel {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
}
#metricValue {
    font-size: 28px;
    font-weight: 800;
}
#metricLabel {
    color: #6b7280;
    font-size: 12px;
    font-weight: 600;
}
#metricHint {
    color: #9ca3af;
    font-size: 11px;
}

QTableWidget {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    gridline-color: #f3f4f6;
}
QHeaderView::section {
    background: #f9fafb;
    border: none;
    border-bottom: 1px solid #e5e7eb;
    padding: 8px;
    font-weight: 700;
    color: #4b5563;
}
QListWidget {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #e5e7eb;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: #111827;
}
QCheckBox { spacing: 8px; }
QScrollArea { border: none; background: transparent; }
#footerLabel {
    color: #9ca3af;
    font-size: 11px;
}
"""
