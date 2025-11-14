from PyQt6.QtWidgets import QMessageBox, QWidget
from typing import Optional


class DialogHelper:
    @staticmethod
    def show_error(
        parent: Optional[QWidget],
        title: str,
        message: str,
        details: Optional[str] = None
    ) -> None:
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)

        if details:
            msg_box.setDetailedText(details)

        msg_box.exec()

    @staticmethod
    def show_warning(
        parent: Optional[QWidget],
        title: str,
        message: str
    ) -> None:
        QMessageBox.warning(parent, title, message)

    @staticmethod
    def show_info(
        parent: Optional[QWidget],
        title: str,
        message: str
    ) -> None:
        QMessageBox.information(parent, title, message)

    @staticmethod
    def show_confirm(
        parent: Optional[QWidget],
        title: str,
        message: str
    ) -> bool:
        reply = QMessageBox.question(
            parent,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes
