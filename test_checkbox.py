from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QCheckBox
from PySide6.QtCore import Qt
import sys

app = QApplication(sys.argv)

window = QWidget()
layout = QVBoxLayout(window)

# 测试复选框样式
checkbox = QCheckBox("测试复选框")
checkbox.setStyleSheet("""
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid #666;
    background: #2c2c2c;
}
QCheckBox::indicator:checked {
    background-color: #5c6bc0;
    border-color: #5c6bc0;
    image: url(data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 16 16'><polyline points='3,8 6,11 13,4' fill='none' stroke='white' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/></svg>);
}
""")

layout.addWidget(checkbox)
window.show()
sys.exit(app.exec())
