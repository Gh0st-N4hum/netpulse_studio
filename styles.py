# styles.py
"""Cyber-Tech Dark Mode Theme & Color Constants for NetPulse Studio."""

BG_CANVAS = "#0B0F19"
BG_PANEL = "#111827"
BG_CARD = "#1E293B"
BORDER_COLOR = "#1F2937"
ACCENT_CYAN = "#00F0FF"
ACCENT_EMERALD = "#10B981"
ACCENT_PURPLE = "#A855F7"
ACCENT_AMBER = "#F59E0B"
ACCENT_RED = "#EF4444"
TEXT_PRIMARY = "#F9FAFB"
TEXT_MUTED = "#9CA3AF"

MAIN_STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 12px;
}}

QToolBar {{
    background-color: #0F172A;
    border-bottom: 1px solid {BORDER_COLOR};
    spacing: 6px;
    padding: 6px;
}}

QToolButton {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid #334155;
    border-radius: 5px;
    padding: 6px 10px;
    font-weight: 600;
}}

QToolButton:hover {{
    border-color: {ACCENT_CYAN};
    color: {ACCENT_CYAN};
    background-color: #1E293B;
}}

QToolButton:checked {{
    background-color: #083344;
    border: 1px solid {ACCENT_CYAN};
    color: {ACCENT_CYAN};
}}

QDockWidget {{
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
    font-weight: bold;
    color: {ACCENT_CYAN};
}}

QDockWidget::title {{
    background: #0F172A;
    padding: 8px;
    border-bottom: 1px solid {BORDER_COLOR};
}}

QGroupBox {{
    border: 1px solid #334155;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 10px;
    font-weight: bold;
    color: {ACCENT_CYAN};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}}

QLineEdit, QComboBox, QSpinBox, QTextEdit {{
    background-color: #0B0F19;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 5px 8px;
    color: {TEXT_PRIMARY};
    font-family: 'Cascadia Code', 'Consolas', 'JetBrains Mono', monospace;
}}

QLineEdit:focus, QComboBox:focus {{
    border: 1px solid {ACCENT_CYAN};
}}

QLineEdit:read-only {{
    background-color: #161F30;
    color: {TEXT_MUTED};
    border-color: #1E293B;
}}

QPushButton {{
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 5px;
    padding: 6px 12px;
    color: {TEXT_PRIMARY};
    font-weight: 600;
}}

QPushButton:hover {{
    border-color: {ACCENT_CYAN};
    color: {ACCENT_CYAN};
}}

QPushButton#primaryBtn {{
    background-color: #065F46;
    border-color: {ACCENT_EMERALD};
    color: #ECFDF5;
}}

QPushButton#primaryBtn:hover {{
    background-color: #047857;
}}

QStatusBar {{
    background-color: #090D16;
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER_COLOR};
    font-family: 'Consolas', monospace;
}}

QScrollArea {{
    border: none;
}}
"""