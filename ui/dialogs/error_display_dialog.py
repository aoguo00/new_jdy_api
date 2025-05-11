from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QSizePolicy, QHBoxLayout
from PySide6.QtCore import Qt

class ErrorDisplayDialog(QDialog):
    """用于显示验证错误的自定义对话框"""
    def __init__(self, error_message: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文件验证失败")
        
        # 调整对话框大小
        self.setMinimumSize(300, 300)
        self.resize(500, 400)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setText(error_message)
        self.text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        main_layout.addWidget(self.text_edit)

        button_container_layout = QHBoxLayout()
        button_container_layout.addStretch(1)
        
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        self.ok_button.setMinimumWidth(100)

        button_container_layout.addWidget(self.ok_button)
        
        main_layout.addLayout(button_container_layout)

        self.setSizeGripEnabled(True) 