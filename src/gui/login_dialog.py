"""Local login dialog."""

from __future__ import annotations

from typing import Any, Dict, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QWidget,
    QMessageBox,
)

from src.db.repositories import UserRepository


class LoginDialog(QDialog):
    def __init__(self, users: UserRepository, app_name: str = "Desktop Automation Using AI", parent=None) -> None:
        super().__init__(parent)
        self.users = users
        self.user: Optional[Dict[str, Any]] = None
        self.setWindowTitle(f"Sign in — {app_name}")
        self.setModal(True)
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(12)

        card = QWidget()
        card.setObjectName("loginCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 22, 22, 22)
        card_layout.setSpacing(10)

        brand = QLabel(app_name)
        brand.setObjectName("appTitle")
        brand.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Local desktop assistant · Group S26CS089")
        subtitle.setObjectName("appSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        hint = QLabel("Default login: demo / demo123")
        hint.setObjectName("sectionHint")
        hint.setAlignment(Qt.AlignCenter)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.username.setText("demo")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setText("demo123")
        self.password.returnPressed.connect(self._try_login)

        btn_row = QHBoxLayout()
        self.btn_login = QPushButton("Sign in")
        self.btn_login.clicked.connect(self._try_login)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btnSecondary")
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_login)

        card_layout.addWidget(brand)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(8)
        card_layout.addWidget(self.username)
        card_layout.addWidget(self.password)
        card_layout.addWidget(hint)
        card_layout.addLayout(btn_row)

        root.addWidget(card)

    def _try_login(self) -> None:
        user = self.users.authenticate(self.username.text().strip(), self.password.text())
        if not user:
            QMessageBox.warning(self, "Sign in failed", "Invalid username or password.")
            return
        self.user = user
        self.accept()
