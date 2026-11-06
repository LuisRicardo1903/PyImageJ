"""
Scale calibration dialog.
Allows setting manual physical scale (px to µm) or auto-detecting from image.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox,
    QLineEdit, QPushButton, QDialogButtonBox, QMessageBox
)
from core.scale import ScaleCalibration, auto_detect_scale_bar
import numpy as np


class ScaleDialog(QDialog):
    def __init__(self, current_calibration: ScaleCalibration, current_image: np.ndarray = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calibrar Escala (Set Scale)")
        self.setMinimumWidth(360)
        self.calibration = current_calibration
        self.image = current_image
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Pixels
        h_px = QHBoxLayout()
        h_px.addWidget(QLabel("Distância em Pixels:"))
        self.spin_px = QDoubleSpinBox()
        self.spin_px.setRange(0.1, 100000.0)
        self.spin_px.setValue(self.calibration.pixels)
        self.spin_px.setDecimals(2)
        h_px.addWidget(self.spin_px)
        layout.addLayout(h_px)

        # Known Distance
        h_dist = QHBoxLayout()
        h_dist.addWidget(QLabel("Distância Conhecida:"))
        self.spin_dist = QDoubleSpinBox()
        self.spin_dist.setRange(0.0001, 100000.0)
        self.spin_dist.setValue(self.calibration.known_distance)
        self.spin_dist.setDecimals(4)
        h_dist.addWidget(self.spin_dist)
        layout.addLayout(h_dist)

        # Unit
        h_unit = QHBoxLayout()
        h_unit.addWidget(QLabel("Unidade de Comprimento:"))
        self.txt_unit = QLineEdit(self.calibration.unit)
        h_unit.addWidget(self.txt_unit)
        layout.addLayout(h_unit)

        # Scale display label
        self.lbl_ratio = QLabel()
        self.update_ratio_label()
        self.spin_px.valueChanged.connect(self.update_ratio_label)
        self.spin_dist.valueChanged.connect(self.update_ratio_label)
        self.txt_unit.textChanged.connect(self.update_ratio_label)
        layout.addWidget(self.lbl_ratio)

        # Auto-detect button
        self.btn_auto = QPushButton("🔍 Detectar Barra Automaticamente na Imagem")
        self.btn_auto.setStyleSheet("background-color: #2196F3; color: white; padding: 6px; font-weight: bold;")
        self.btn_auto.clicked.connect(self.run_auto_detect)
        layout.addWidget(self.btn_auto)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def update_ratio_label(self):
        px = self.spin_px.value()
        dist = self.spin_dist.value()
        unit = self.txt_unit.text() or "px"
        if px > 0:
            scale_val = dist / px
            self.lbl_ratio.setText(f"Escala calculada: <b>{scale_val:.4f} {unit}/pixel</b> ({px/dist:.2f} px/{unit})")

    def run_auto_detect(self):
        if self.image is None:
            QMessageBox.warning(self, "Aviso", "Nenhuma imagem carregada para detecção.")
            return

        calib, bbox = auto_detect_scale_bar(self.image, known_distance=self.spin_dist.value(), unit=self.txt_unit.text())
        if calib:
            self.spin_px.setValue(calib.pixels)
            self.spin_dist.setValue(calib.known_distance)
            self.txt_unit.setText(calib.unit)
            QMessageBox.information(
                self, "Sucesso",
                f"Barra de escala detectada com sucesso!\n"
                f"Comprimento: {calib.pixels:.1f} pixels\n"
                f"Posição: X=[{bbox[0]}, {bbox[2]}], Y=[{bbox[1]}, {bbox[3]}]"
            )
        else:
            QMessageBox.warning(self, "Não Encontrado", "Não foi possível detectar automaticamente a barra de legenda nesta imagem.")

    def get_calibration(self) -> ScaleCalibration:
        return ScaleCalibration(
            pixels=self.spin_px.value(),
            known_distance=self.spin_dist.value(),
            unit=self.txt_unit.text().strip() or "px"
        )
