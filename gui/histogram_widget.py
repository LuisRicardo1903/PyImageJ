"""
High-performance native Qt Histogram Widget.
Renders frequency distribution bars with mean, median, and std indicators
using pure QPainter (zero external dependencies like matplotlib).
"""

from typing import List, Optional, Tuple
import numpy as np
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPaintEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout


class HistogramWidget(QWidget):
    def __init__(self, title: str = "Distribuição", unit: str = "µm", color: QColor = QColor(33, 150, 243), parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.bar_color = color
        self.data: np.ndarray = np.array([])
        self.bins: int = 20
        self.counts: np.ndarray = np.array([])
        self.bin_edges: np.ndarray = np.array([])

        self.setMinimumHeight(180)
        self.setStyleSheet("background-color: #202020; border-radius: 4px;")

    def set_data(self, values: List[float], bins: int = 20):
        if values is None or len(values) == 0:
            self.data = np.array([])
            self.counts = np.array([])
            self.bin_edges = np.array([])
            self.update()
            return

        self.data = np.array(values, dtype=float)
        self.bins = bins
        self.counts, self.bin_edges = np.histogram(self.data, bins=self.bins)
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#1e1e1e"))

        if len(self.counts) == 0:
            painter.setPen(QColor("#777777"))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "Nenhum dado para exibir no histograma.")
            return

        # Margins
        left = 55
        right = 20
        top = 35
        bottom = 35

        plot_w = w - left - right
        plot_h = h - top - bottom

        if plot_w <= 0 or plot_h <= 0:
            return

        # Header Title and Stats
        mean_val = np.mean(self.data)
        std_val = np.std(self.data)
        median_val = np.median(self.data)
        max_val = np.max(self.data)
        min_val = np.min(self.data)

        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.drawText(left, 22, f"{self.title}")

        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QColor("#AAAAAA"))
        stats_str = f"Média: {mean_val:.2f} {self.unit} | Mediana: {median_val:.2f} | Desvio: ±{std_val:.2f} | Mín: {min_val:.2f} | Máx: {max_val:.2f}"
        painter.drawText(QRectF(left, 5, w - left - right, 25), Qt.AlignRight | Qt.AlignVCenter, stats_str)

        # Axes & Grid
        max_count = int(np.max(self.counts))
        if max_count == 0:
            max_count = 1

        # Horizontal Grid lines (3 lines)
        painter.setPen(QPen(QColor("#333333"), 1, Qt.DashLine))
        for i in range(4):
            y_pos = top + (plot_h / 3) * i
            painter.drawLine(left, int(y_pos), w - right, int(y_pos))
            # Y label
            y_label_val = int(max_count * (3 - i) / 3)
            painter.setPen(QColor("#888888"))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(QRectF(0, y_pos - 8, left - 8, 16), Qt.AlignRight | Qt.AlignVCenter, str(y_label_val))
            painter.setPen(QPen(QColor("#333333"), 1, Qt.DashLine))

        # Draw Bars
        bar_w = plot_w / len(self.counts)
        painter.setPen(QPen(QColor("#0d47a1"), 1))
        painter.setBrush(QBrush(self.bar_color))

        for idx, count in enumerate(self.counts):
            bar_h = (count / max_count) * plot_h
            bx = left + idx * bar_w
            by = top + (plot_h - bar_h)
            rect = QRectF(bx + 1, by, max(1, bar_w - 2), bar_h)
            painter.drawRect(rect)

        # Baseline axis
        painter.setPen(QPen(QColor("#555555"), 1.5))
        painter.drawLine(left, top + plot_h, w - right, top + plot_h)
        painter.drawLine(left, top, left, top + plot_h)

        # X-axis ticks (min, mid, max)
        painter.setPen(QColor("#AAAAAA"))
        painter.setFont(QFont("Segoe UI", 8))

        x_min_str = f"{self.bin_edges[0]:.1f} {self.unit}"
        x_mid_str = f"{(self.bin_edges[0] + self.bin_edges[-1])/2:.1f} {self.unit}"
        x_max_str = f"{self.bin_edges[-1]:.1f} {self.unit}"

        painter.drawText(QRectF(left, top + plot_h + 5, 80, 20), Qt.AlignLeft, x_min_str)
        painter.drawText(QRectF(left + plot_w/2 - 40, top + plot_h + 5, 80, 20), Qt.AlignCenter, x_mid_str)
        painter.drawText(QRectF(w - right - 80, top + plot_h + 5, 80, 20), Qt.AlignRight, x_max_str)
