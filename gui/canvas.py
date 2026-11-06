"""
Interactive Image Canvas for PyImageJ Studio.
Provides smooth zoom, pan, pixel coordinates tracking, and overlay visualization.
"""

from typing import Optional, Callable
import numpy as np
from PySide6.QtCore import Qt, QPointF, Signal, QRectF
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QWheelEvent, QMouseEvent
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem


def numpy_to_qimage(arr: np.ndarray) -> QImage:
    """
    Converts 2D grayscale or 3D RGB numpy array to QImage safely without copy issues.
    """
    if arr is None or arr.size == 0:
        return QImage()

    if arr.dtype != np.uint8:
        # Normalize to uint8
        arr = np.clip(arr, 0, 255).astype(np.uint8)

    if arr.ndim == 2:
        h, w = arr.shape
        qimg = QImage(arr.data, w, h, w, QImage.Format_Grayscale8)
        return qimg.copy()
    elif arr.ndim == 3:
        h, w, c = arr.shape
        if c == 3:
            qimg = QImage(arr.data, w, h, 3 * w, QImage.Format_RGB888)
            return qimg.copy()
        elif c == 4:
            qimg = QImage(arr.data, w, h, 4 * w, QImage.Format_RGBA8888)
            return qimg.copy()
    return QImage()


class InteractiveCanvas(QGraphicsView):
    pixel_hovered = Signal(int, int, str)  # x, y, value string
    roi_selected = Signal(int, int, int, int)  # x, y, w, h

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        # ROI selection item
        self.roi_item = QGraphicsRectItem()
        self.roi_item.setPen(QPen(QColor(0, 255, 255), 2, Qt.DashLine))
        self.roi_item.setVisible(False)
        self.scene.addItem(self.roi_item)

        # View settings
        self.setRenderHint(QPainter.Antialiasing, False)
        self.setRenderHint(QPainter.SmoothPixmapTransform, False)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setMouseTracking(True)

        self.raw_numpy: Optional[np.ndarray] = None
        self.zoom_factor: float = 1.0

        # Panning state
        self._is_panning = False
        self._pan_start = QPointF()

        # ROI selection mode
        self.roi_mode = False
        self._roi_start = QPointF()
        self._is_drawing_roi = False

        self.setStyleSheet("background-color: #1e1e1e; border: none;")

    def set_image(self, arr: np.ndarray, reset_zoom: bool = False):
        self.raw_numpy = arr
        qimg = numpy_to_qimage(arr)
        pixmap = QPixmap.fromImage(qimg)
        self.pixmap_item.setPixmap(pixmap)
        self.scene.setSceneRect(QRectF(pixmap.rect()))

        if reset_zoom:
            self.resetTransform()
            self.zoom_factor = 1.0
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    def update_image_fast(self, arr: np.ndarray):
        """
        High-performance pixmap update for live previews.
        Avoids recalculating scene bounds and coordinate matrices.
        """
        self.raw_numpy = arr
        qimg = numpy_to_qimage(arr)
        self.pixmap_item.setPixmap(QPixmap.fromImage(qimg))

    def wheelEvent(self, event: QWheelEvent):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            factor = zoom_in_factor
            self.zoom_factor *= factor
        else:
            factor = zoom_out_factor
            self.zoom_factor *= factor

        self.scale(factor, factor)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        pos = self.mapToScene(event.pos())
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier):
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        elif event.button() == Qt.LeftButton and self.roi_mode:
            self._is_drawing_roi = True
            self._roi_start = pos
            self.roi_item.setRect(QRectF(pos, pos))
            self.roi_item.setVisible(True)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        scene_pos = self.mapToScene(event.pos())
        x = int(scene_pos.x())
        y = int(scene_pos.y())

        # Update pixel info
        if self.raw_numpy is not None:
            h, w = self.raw_numpy.shape[:2]
            if 0 <= x < w and 0 <= y < h:
                if self.raw_numpy.ndim == 2:
                    val_str = f"Val: {self.raw_numpy[y, x]}"
                elif self.raw_numpy.ndim == 3 and self.raw_numpy.shape[2] >= 3:
                    r, g, b = self.raw_numpy[y, x][:3]
                    val_str = f"R:{r} G:{g} B:{b}"
                else:
                    val_str = ""
                self.pixel_hovered.emit(x, y, val_str)

        if self._is_panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return

        if self._is_drawing_roi:
            rect = QRectF(self._roi_start, scene_pos).normalized()
            self.roi_item.setRect(rect)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return

        if self._is_drawing_roi:
            self._is_drawing_roi = False
            rect = self.roi_item.rect()
            x = int(rect.x())
            y = int(rect.y())
            w = int(rect.width())
            h = int(rect.height())
            self.roi_selected.emit(x, y, w, h)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def clear_roi(self):
        self.roi_item.setVisible(False)
