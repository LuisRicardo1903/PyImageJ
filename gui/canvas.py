"""
Interactive Image Canvas for PyImageJ Studio.
Provides smooth zoom, pan, pixel coordinates tracking, and advanced ROI selection
(Rectangle, Ellipse/Circle, and Freeform Polygon).
"""

from typing import Optional, List, Tuple
import cv2
import numpy as np
from PySide6.QtCore import Qt, QPointF, Signal, QRectF
from PySide6.QtGui import (
    QImage, QPixmap, QPainter, QColor, QPen, QBrush,
    QWheelEvent, QMouseEvent, QPolygonF
)
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPolygonItem
)


def numpy_to_qimage(arr: np.ndarray) -> QImage:
    """Converts 2D grayscale or 3D RGB numpy array to QImage safely."""
    if arr is None or arr.size == 0:
        return QImage()

    if arr.dtype != np.uint8:
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
    roi_selected = Signal(int, int, int, int)  # x, y, w, h (legacy rect)
    roi_mask_defined = Signal(object, str)  # boolean 2D mask, description

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        # ROI Items
        pen_dash = QPen(QColor(0, 255, 255), 2, Qt.DashLine)

        self.roi_rect_item = QGraphicsRectItem()
        self.roi_rect_item.setPen(pen_dash)
        self.roi_rect_item.setVisible(False)
        self.scene.addItem(self.roi_rect_item)

        self.roi_ellipse_item = QGraphicsEllipseItem()
        self.roi_ellipse_item.setPen(pen_dash)
        self.roi_ellipse_item.setVisible(False)
        self.scene.addItem(self.roi_ellipse_item)

        self.roi_poly_item = QGraphicsPolygonItem()
        self.roi_poly_item.setPen(pen_dash)
        self.roi_poly_item.setBrush(QBrush(QColor(0, 255, 255, 35)))
        self.roi_poly_item.setVisible(False)
        self.scene.addItem(self.roi_poly_item)

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

        # ROI selection mode: "none", "rect", "ellipse", "polygon"
        self.roi_mode: str = "none"
        self._roi_start = QPointF()
        self._is_drawing_roi = False
        self._poly_points: List[QPointF] = []

        self.setStyleSheet("background-color: #1e1e1e; border: none;")

    def set_roi_mode(self, mode: str):
        self.roi_mode = mode.lower()
        self._poly_points = []
        if self.roi_mode == "polygon":
            self.roi_poly_item.setPolygon(QPolygonF())
            self.roi_poly_item.setVisible(True)

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
        """High-performance pixmap update for live previews."""
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

        # Pan
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier):
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        # Polygon Mode
        if self.roi_mode == "polygon":
            if event.button() == Qt.LeftButton:
                self._poly_points.append(pos)
                poly = QPolygonF(self._poly_points)
                self.roi_poly_item.setPolygon(poly)
                self.roi_poly_item.setVisible(True)
                event.accept()
                return
            elif event.button() == Qt.RightButton and len(self._poly_points) >= 3:
                self.finish_polygon_roi()
                event.accept()
                return

        # Rect / Ellipse Mode
        if event.button() == Qt.LeftButton and self.roi_mode in ["rect", "ellipse"]:
            self._is_drawing_roi = True
            self._roi_start = pos
            if self.roi_mode == "rect":
                self.roi_rect_item.setRect(QRectF(pos, pos))
                self.roi_rect_item.setVisible(True)
            elif self.roi_mode == "ellipse":
                self.roi_ellipse_item.setRect(QRectF(pos, pos))
                self.roi_ellipse_item.setVisible(True)
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
            if self.roi_mode == "rect":
                self.roi_rect_item.setRect(rect)
            elif self.roi_mode == "ellipse":
                self.roi_ellipse_item.setRect(rect)
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
            if self.raw_numpy is None:
                return

            h, w = self.raw_numpy.shape[:2]

            if self.roi_mode == "rect":
                rect = self.roi_rect_item.rect()
                rx, ry, rw, rh = int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height())
                if rw > 2 and rh > 2:
                    mask = np.zeros((h, w), dtype=bool)
                    x0 = max(0, rx)
                    y0 = max(0, ry)
                    x1 = min(w, rx + rw)
                    y1 = min(h, ry + rh)
                    mask[y0:y1, x0:x1] = True
                    self.roi_selected.emit(rx, ry, rw, rh)
                    self.roi_mask_defined.emit(mask, f"Retângulo [{x0}, {y0}] a [{x1}, {y1}]")

            elif self.roi_mode == "ellipse":
                rect = self.roi_ellipse_item.rect()
                rx, ry, rw, rh = rect.x(), rect.y(), rect.width(), rect.height()
                if rw > 2 and rh > 2:
                    mask = np.zeros((h, w), dtype=np.uint8)
                    cx = int(rx + rw / 2.0)
                    cy = int(ry + rh / 2.0)
                    axes = (int(rw / 2.0), int(rh / 2.0))
                    cv2.ellipse(mask, (cx, cy), axes, 0, 0, 360, 255, -1)
                    self.roi_mask_defined.emit(mask > 0, f"Elipse Centro ({cx}, {cy}), Eixos {axes[0]}x{axes[1]}")

            event.accept()
            return

        super().mouseReleaseEvent(event)

    def finish_polygon_roi(self):
        if self.raw_numpy is None or len(self._poly_points) < 3:
            return
        h, w = self.raw_numpy.shape[:2]
        pts = np.array([[int(p.x()), int(p.y())] for p in self._poly_points], dtype=np.int32)
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [pts], 255)
        self.roi_mask_defined.emit(mask > 0, f"Polígono com {len(self._poly_points)} vértices")

    def clear_roi(self):
        self.roi_rect_item.setVisible(False)
        self.roi_ellipse_item.setVisible(False)
        self.roi_poly_item.setVisible(False)
        self._poly_points = []
