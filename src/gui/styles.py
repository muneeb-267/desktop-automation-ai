"""Automate AI light / dark themes."""

from __future__ import annotations

LIGHT_STYLE = """
* {
    font-family: "Segoe UI", "IBM Plex Sans", "Source Sans 3", "Noto Sans", sans-serif;
    color: #1a1d21;
    font-size: 13px;
}

QMainWindow, QDialog {
    background: #f3f4f6;
}

#landingRoot { background: #f3f4f6; }
#brandPanel { background: #eef0f3; }
#formPanel { background: #ffffff; }
#brandLogo { font-size: 22px; font-weight: 800; color: #111827; }
#brandEyebrow {
    color: #6b7280; font-size: 11px; font-weight: 700; letter-spacing: 1.2px;
}
#brandHeadline { font-size: 34px; font-weight: 800; color: #111827; }
#brandHeadlineAccent {
    font-size: 34px; font-weight: 500; font-style: italic; color: #6b7280;
}
#brandBody { color: #4b5563; font-size: 14px; }
#featureCard {
    background: #111827; border-radius: 14px; color: #f9fafb; padding: 18px;
}
#featureCardTitle { color: #ffffff; font-size: 18px; font-weight: 700; }
#featureCardBody { color: #d1d5db; font-size: 12px; }
#loginTitle { font-size: 26px; font-weight: 800; }
#loginSubtitle { color: #6b7280; }

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 10px 12px;
    selection-background-color: #dbe4ee;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus { border: 1px solid #111827; }

QPushButton {
    background: #111827; color: #ffffff; border: none; border-radius: 8px;
    padding: 10px 16px; font-weight: 700;
}
QPushButton:hover { background: #1f2937; }
QPushButton:disabled { background: #9ca3af; }
QPushButton#btnGhost, QPushButton#btnSecondary {
    background: #f3f4f6; color: #111827; border: 1px solid #d1d5db;
}
QPushButton#btnGhost:hover, QPushButton#btnSecondary:hover { background: #e5e7eb; }
QPushButton#btnNav {
    background: transparent; color: #374151; text-align: left;
    padding: 12px 14px; border-radius: 10px; font-weight: 600;
}
QPushButton#btnNav:hover { background: #e5e7eb; }
QPushButton#btnNav[active="true"] {
    background: #e5e7eb; color: #111827; font-weight: 800;
}
QPushButton#btnMicBig {
    background: #111827; border-radius: 48px;
    min-width: 120px; min-height: 96px; max-width: 160px; max-height: 96px;
    font-size: 18px; font-weight: 800; padding: 8px 14px;
}
QPushButton#btnMicBig:disabled { background: #6b7280; }
QPushButton#btnDanger { background: #b42318; color: #ffffff; }

#sideBar { background: #ffffff; border-right: 1px solid #e5e7eb; }
#sideBrand { font-size: 16px; font-weight: 800; }
#topBar { background: #ffffff; border-bottom: 1px solid #e5e7eb; }
#pageTitle { font-size: 26px; font-weight: 800; }
#pageSubtitle { color: #6b7280; font-size: 13px; }
#statusChip {
    background: #ecfdf3; color: #067647; border-radius: 12px;
    padding: 4px 10px; font-weight: 700;
}
#metricCard, #panelCard, #workflowCard, #voicePanel {
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px;
}
#metricValue { font-size: 28px; font-weight: 800; }
#metricLabel { color: #6b7280; font-size: 12px; font-weight: 600; }
#metricHint { color: #9ca3af; font-size: 11px; }

QTableWidget {
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px;
    gridline-color: #f3f4f6;
}
QHeaderView::section {
    background: #f9fafb; border: none; border-bottom: 1px solid #e5e7eb;
    padding: 8px; font-weight: 700; color: #4b5563;
}
QListWidget { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px; }
QSlider::groove:horizontal { height: 6px; background: #e5e7eb; border-radius: 3px; }
QSlider::handle:horizontal {
    width: 16px; margin: -6px 0; border-radius: 8px; background: #111827;
}
QCheckBox { spacing: 8px; }
QScrollArea { border: none; background: transparent; }
#footerLabel { color: #9ca3af; font-size: 11px; }
#logFrame { border: 1px solid #1f2937; border-radius: 10px; }
"""

DARK_STYLE = """
* {
    font-family: "Segoe UI", "IBM Plex Sans", "Source Sans 3", "Noto Sans", sans-serif;
    color: #e5e7eb;
    font-size: 13px;
}

QMainWindow, QDialog { background: #0f172a; }

#landingRoot { background: #0f172a; }
#brandPanel { background: #111827; }
#formPanel { background: #1e293b; }
#brandLogo { font-size: 22px; font-weight: 800; color: #f8fafc; }
#brandEyebrow {
    color: #94a3b8; font-size: 11px; font-weight: 700; letter-spacing: 1.2px;
}
#brandHeadline { font-size: 34px; font-weight: 800; color: #f8fafc; }
#brandHeadlineAccent {
    font-size: 34px; font-weight: 500; font-style: italic; color: #94a3b8;
}
#brandBody { color: #cbd5e1; font-size: 14px; }
#featureCard {
    background: #020617; border-radius: 14px; color: #f8fafc; padding: 18px;
}
#featureCardTitle { color: #ffffff; font-size: 18px; font-weight: 700; }
#featureCardBody { color: #94a3b8; font-size: 12px; }
#loginTitle { font-size: 26px; font-weight: 800; color: #f8fafc; }
#loginSubtitle { color: #94a3b8; }

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 10px 12px;
    color: #e2e8f0;
    selection-background-color: #334155;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus { border: 1px solid #94a3b8; }

QPushButton {
    background: #38bdf8; color: #0f172a; border: none; border-radius: 8px;
    padding: 10px 16px; font-weight: 700;
}
QPushButton:hover { background: #7dd3fc; }
QPushButton:disabled { background: #475569; color: #cbd5e1; }
QPushButton#btnGhost, QPushButton#btnSecondary {
    background: #1e293b; color: #e2e8f0; border: 1px solid #334155;
}
QPushButton#btnGhost:hover, QPushButton#btnSecondary:hover { background: #334155; }
QPushButton#btnNav {
    background: transparent; color: #cbd5e1; text-align: left;
    padding: 12px 14px; border-radius: 10px; font-weight: 600;
}
QPushButton#btnNav:hover { background: #1e293b; }
QPushButton#btnNav[active="true"] {
    background: #1e293b; color: #f8fafc; font-weight: 800;
}
QPushButton#btnMicBig {
    background: #38bdf8; color: #0f172a; border-radius: 48px;
    min-width: 120px; min-height: 96px; max-width: 160px; max-height: 96px;
    font-size: 18px; font-weight: 800; padding: 8px 14px;
}
QPushButton#btnMicBig:disabled { background: #475569; color: #cbd5e1; }
QPushButton#btnDanger { background: #ef4444; color: #ffffff; }

#sideBar { background: #111827; border-right: 1px solid #1e293b; }
#sideBrand { font-size: 16px; font-weight: 800; color: #f8fafc; }
#topBar { background: #111827; border-bottom: 1px solid #1e293b; }
#pageTitle { font-size: 26px; font-weight: 800; color: #f8fafc; }
#pageSubtitle { color: #94a3b8; font-size: 13px; }
#statusChip {
    background: #064e3b; color: #6ee7b7; border-radius: 12px;
    padding: 4px 10px; font-weight: 700;
}
#metricCard, #panelCard, #workflowCard, #voicePanel {
    background: #1e293b; border: 1px solid #334155; border-radius: 14px;
}
#metricValue { font-size: 28px; font-weight: 800; color: #f8fafc; }
#metricLabel { color: #94a3b8; font-size: 12px; font-weight: 600; }
#metricHint { color: #64748b; font-size: 11px; }

QTableWidget {
    background: #0f172a; border: 1px solid #334155; border-radius: 10px;
    gridline-color: #1e293b; color: #e2e8f0;
}
QHeaderView::section {
    background: #1e293b; border: none; border-bottom: 1px solid #334155;
    padding: 8px; font-weight: 700; color: #94a3b8;
}
QListWidget {
    background: #0f172a; border: 1px solid #334155; border-radius: 10px; color: #e2e8f0;
}
QSlider::groove:horizontal { height: 6px; background: #334155; border-radius: 3px; }
QSlider::handle:horizontal {
    width: 16px; margin: -6px 0; border-radius: 8px; background: #38bdf8;
}
QCheckBox { spacing: 8px; color: #e2e8f0; }
QScrollArea { border: none; background: transparent; }
#footerLabel { color: #64748b; font-size: 11px; }
#logFrame { border: 1px solid #334155; border-radius: 10px; }
"""

# Backward-compatible alias
APP_STYLE = LIGHT_STYLE


def get_app_style(theme: str = "light") -> str:
    return DARK_STYLE if str(theme).lower() in ("dark", "night") else LIGHT_STYLE
