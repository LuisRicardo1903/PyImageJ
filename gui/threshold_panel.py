"""
Threshold and segmentation dock panel.
Features interactive live threshold adjustment, algorithm selection,
and instant porosity percentage preview.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QComboBox, QCheckBox, QPushButton, QGroupBox, QSpinBox
)
from core.threshold import THRESHOLD_METHODS


class ThresholdPanel(QWidget):
    threshold_changed = Signal(int, bool)  # threshold_val, dark_objects
    method_selected = Signal(str)
    apply_clicked = Signal()
    watershed_clicked = Signal()
    reset_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Algorithm Group
        grp_method = QGroupBox("Algoritmo de Threshold")
        layout_method = QVBoxLayout(grp_method)

        self.combo_method = QComboBox()
        self.combo_method.addItems(THRESHOLD_METHODS)
        self.combo_method.currentTextChanged.connect(self.on_method_changed)
        layout_method.addWidget(self.combo_method)

        self.chk_dark = QCheckBox("Objetos Escuros (Poros / Defeitos)")
        self.chk_dark.setChecked(True)
        self.chk_dark.toggled.connect(self.on_param_changed)
        layout_method.addWidget(self.chk_dark)

        layout.addWidget(grp_method)

        # Slider Group
        grp_slider = QGroupBox("Ajuste Manual do Limiar (0 - 255)")
        layout_slider = QVBoxLayout(grp_slider)

        h_spin = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 255)
        self.slider.setValue(128)
        self.slider.valueChanged.connect(self.on_slider_changed)

        self.spin_val = QSpinBox()
        self.spin_val.setRange(0, 255)
        self.spin_val.setValue(128)
        self.spin_val.valueChanged.connect(self.slider.setValue)

        h_spin.addWidget(self.slider)
        h_spin.addWidget(self.spin_val)
        layout_slider.addLayout(h_spin)

        # Live Porosity Label
        self.lbl_porosity = QLabel("Porosidade Estimada: -- %")
        self.lbl_porosity.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 13px;")
        layout_slider.addWidget(self.lbl_porosity)

        layout.addWidget(grp_slider)

        # Morphology Operations
        grp_morph = QGroupBox("Operações Binárias")
        layout_morph = QVBoxLayout(grp_morph)

        self.btn_watershed = QPushButton("Separar Partículas (Watershed)")
        self.btn_watershed.clicked.connect(self.watershed_clicked.emit)
        layout_morph.addWidget(self.btn_watershed)

        layout.addWidget(grp_morph)

        # Action Buttons
        h_actions = QHBoxLayout()
        self.btn_apply = QPushButton("Aplicar e Binarizar")
        self.btn_apply.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 6px;")
        self.btn_apply.clicked.connect(self.apply_clicked.emit)

        self.btn_reset = QPushButton("Resetar")
        self.btn_reset.clicked.connect(self.reset_clicked.emit)

        h_actions.addWidget(self.btn_apply)
        h_actions.addWidget(self.btn_reset)
        layout.addLayout(h_actions)

        layout.addStretch()

    def on_method_changed(self, method_name: str):
        self.method_selected.emit(method_name)

    def on_slider_changed(self, val: int):
        self.spin_val.blockSignals(True)
        self.spin_val.setValue(val)
        self.spin_val.blockSignals(False)
        self.threshold_changed.emit(val, self.chk_dark.isChecked())

    def on_param_changed(self):
        self.threshold_changed.emit(self.slider.value(), self.chk_dark.isChecked())

    def set_threshold_value(self, val: int):
        self.slider.blockSignals(True)
        self.spin_val.blockSignals(True)
        self.slider.setValue(val)
        self.spin_val.setValue(val)
        self.slider.blockSignals(False)
        self.spin_val.blockSignals(False)

    def update_porosity_preview(self, porosity_pct: float):
        self.lbl_porosity.setText(f"Porosidade Estimada: {porosity_pct:.2f}%")
