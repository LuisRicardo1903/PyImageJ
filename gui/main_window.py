"""
Main Window for PyImageJ Studio.
Modern desktop application replacing ImageJ with updated UI,
interactive canvas, particle analyzer, live thresholding, and batch processing.
"""

from typing import Optional
import os
import cv2
import numpy as np
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QDockWidget, QFileDialog, QMessageBox,
    QStatusBar, QToolBar, QLabel, QInputDialog
)

from core.processor import ImageDocument
from core.scale import ScaleCalibration, auto_detect_scale_bar
from core.threshold import calculate_threshold, apply_threshold, binary_watershed
from core.particle_analyzer import analyze_particles
from gui.canvas import InteractiveCanvas
from gui.threshold_panel import ThresholdPanel
from gui.results_panel import ResultsPanel
from gui.scale_dialog import ScaleDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyImageJ Studio - Análise e Processamento de Imagens")
        self.resize(1300, 850)

        # Set application icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.doc: ImageDocument = ImageDocument()
        self.calibration: ScaleCalibration = ScaleCalibration(pixels=1.0, known_distance=1.0, unit="px")
        self.active_binary_mask: Optional[np.ndarray] = None
        self.scale_box_crop: Optional[tuple] = None  # (min_x, min_y, max_x, max_y)
        self.valid_roi_mask: Optional[np.ndarray] = None

        self.init_ui()
        self.apply_dark_theme()

    def init_ui(self):
        # Center Canvas
        self.canvas = InteractiveCanvas(self)
        self.canvas.pixel_hovered.connect(self.on_pixel_hovered)
        self.canvas.roi_selected.connect(self.on_roi_selected)
        self.canvas.roi_mask_defined.connect(self.on_roi_mask_defined)
        self.setCentralWidget(self.canvas)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_status_pos = QLabel("X: --  Y: --  Valor: --")
        self.lbl_status_scale = QLabel("Escala: 1.0000 px/px")
        self.lbl_status_dim = QLabel("Dimensões: -- x --")
        self.status_bar.addWidget(self.lbl_status_dim, 1)
        self.status_bar.addWidget(self.lbl_status_pos, 1)
        self.status_bar.addWidget(self.lbl_status_scale, 1)

        # Docks
        self.init_docks()

        # Menus & Toolbars
        self.init_actions()
        self.init_menus()
        self.init_toolbar()

    def init_docks(self):
        # Threshold Dock (Right)
        self.dock_threshold = QDockWidget("Ajuste de Limiar (Threshold)", self)
        self.dock_threshold.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.threshold_panel = ThresholdPanel(self)
        self.threshold_panel.threshold_changed.connect(self.on_threshold_preview)
        self.threshold_panel.method_selected.connect(self.on_threshold_method_selected)
        self.threshold_panel.apply_clicked.connect(self.on_threshold_applied)
        self.threshold_panel.watershed_clicked.connect(self.on_watershed_applied)
        self.threshold_panel.reset_clicked.connect(self.on_reset_view)
        self.dock_threshold.setWidget(self.threshold_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_threshold)

        # Results Dock (Bottom)
        self.dock_results = QDockWidget("Medições de Partículas (Results Table)", self)
        self.dock_results.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        self.results_panel = ResultsPanel(self)
        self.dock_results.setWidget(self.results_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_results)

    def init_actions(self):
        # File Actions
        self.act_open = QAction("Abrir Imagem...", self)
        self.act_open.setShortcut(QKeySequence.Open)
        self.act_open.triggered.connect(self.open_image_dialog)

        self.act_save = QAction("Salvar Imagem", self)
        self.act_save.setShortcut(QKeySequence.Save)
        self.act_save.triggered.connect(self.save_image)

        self.act_batch = QAction("Processamento em Lote (Pasta)...", self)
        self.act_batch.triggered.connect(self.run_batch_processing)

        self.act_exit = QAction("Sair", self)
        self.act_exit.triggered.connect(self.close)

        # Edit Actions
        self.act_undo = QAction("Desfazer", self)
        self.act_undo.setShortcut(QKeySequence.Undo)
        self.act_undo.triggered.connect(self.undo)

        self.act_roi_rect = QAction("ROI Retângulo", self)
        self.act_roi_rect.setCheckable(True)
        self.act_roi_rect.triggered.connect(lambda: self.set_roi_mode("rect"))

        self.act_roi_ellipse = QAction("ROI Elipse/Círculo", self)
        self.act_roi_ellipse.setCheckable(True)
        self.act_roi_ellipse.triggered.connect(lambda: self.set_roi_mode("ellipse"))

        self.act_roi_polygon = QAction("ROI Polígono Livre", self)
        self.act_roi_polygon.setCheckable(True)
        self.act_roi_polygon.triggered.connect(lambda: self.set_roi_mode("polygon"))

        self.act_clear_roi = QAction("Limpar ROI", self)
        self.act_clear_roi.triggered.connect(self.clear_roi)

        # Process Actions
        self.act_gaussian = QAction("Filtro Gaussiano (Smooth)...", self)
        self.act_gaussian.triggered.connect(lambda: self.apply_filter("gaussian", sigma=1.5))

        self.act_median = QAction("Filtro de Mediana...", self)
        self.act_median.triggered.connect(lambda: self.apply_filter("median", ksize=3))

        self.act_sharpen = QAction("Nitidez (Sharpen)", self)
        self.act_sharpen.triggered.connect(lambda: self.apply_filter("sharpen"))

        self.act_edges = QAction("Detectar Bordas (Sobel)", self)
        self.act_edges.triggered.connect(lambda: self.apply_filter("find_edges"))

        self.act_invert = QAction("Inverter Cores", self)
        self.act_invert.triggered.connect(lambda: self.apply_filter("invert"))

        # Analyze Actions
        self.act_scale = QAction("Calibrar Escala (Set Scale)...", self)
        self.act_scale.triggered.connect(self.open_scale_dialog)

        self.act_auto_scale = QAction("Auto-Detectar Barra de Escala", self)
        self.act_auto_scale.triggered.connect(self.auto_detect_scale)

        self.act_analyze = QAction("Analisar Partículas (Analyze Particles)", self)
        self.act_analyze.setShortcut(QKeySequence("Ctrl+M"))
        self.act_analyze.triggered.connect(self.run_analyze_particles)

        # View Actions
        self.act_reset_zoom = QAction("Ajustar à Tela", self)
        self.act_reset_zoom.triggered.connect(lambda: self.canvas.set_image(self.doc.current_image, reset_zoom=True))

    def init_menus(self):
        menubar = self.menuBar()

        # File
        m_file = menubar.addMenu("&Arquivo")
        m_file.addAction(self.act_open)
        m_file.addAction(self.act_save)
        m_file.addSeparator()
        m_file.addAction(self.act_batch)
        m_file.addSeparator()
        m_file.addAction(self.act_exit)

        # Edit
        m_edit = menubar.addMenu("&Editar")
        m_edit.addAction(self.act_undo)
        m_edit.addSeparator()
        m_roi_menu = m_edit.addMenu("Região de Interesse (ROI)")
        m_roi_menu.addAction(self.act_roi_rect)
        m_roi_menu.addAction(self.act_roi_ellipse)
        m_roi_menu.addAction(self.act_roi_polygon)
        m_edit.addAction(self.act_clear_roi)

        # Process
        m_proc = menubar.addMenu("&Processar")
        m_proc.addAction(self.act_gaussian)
        m_proc.addAction(self.act_median)
        m_proc.addAction(self.act_sharpen)
        m_proc.addAction(self.act_edges)
        m_proc.addSeparator()
        m_proc.addAction(self.act_invert)

        # Analyze
        m_ana = menubar.addMenu("&Analisar")
        m_ana.addAction(self.act_scale)
        m_ana.addAction(self.act_auto_scale)
        m_ana.addSeparator()
        m_ana.addAction(self.act_analyze)

    def init_toolbar(self):
        toolbar = QToolBar("Barra Principal", self)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        toolbar.addAction(self.act_open)
        toolbar.addAction(self.act_save)
        toolbar.addAction(self.act_undo)
        toolbar.addSeparator()
        toolbar.addAction(self.act_reset_zoom)
        toolbar.addSeparator()
        toolbar.addAction(self.act_roi_rect)
        toolbar.addAction(self.act_roi_ellipse)
        toolbar.addAction(self.act_roi_polygon)
        toolbar.addAction(self.act_clear_roi)
        toolbar.addSeparator()
        toolbar.addAction(self.act_auto_scale)
        toolbar.addAction(self.act_scale)
        toolbar.addSeparator()
        toolbar.addAction(self.act_analyze)

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QMenuBar {
                background-color: #2d2d2d;
                color: #FFFFFF;
                border-bottom: 1px solid #3d3d3d;
            }
            QMenuBar::item:selected {
                background-color: #3e3e3e;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #FFFFFF;
                border: 1px solid #444;
            }
            QMenu::item:selected {
                background-color: #007acc;
            }
            QToolBar {
                background-color: #282828;
                border-bottom: 1px solid #383838;
                spacing: 6px;
                padding: 3px;
            }
            QToolButton {
                background-color: transparent;
                color: #FFFFFF;
                padding: 4px;
                border-radius: 3px;
            }
            QToolButton:hover {
                background-color: #3a3a3a;
            }
            QToolButton:checked {
                background-color: #007acc;
            }
            QDockWidget {
                color: #FFFFFF;
                titlebar-close-icon: url(close.png);
                titlebar-normal-icon: url(undock.png);
            }
            QDockWidget::title {
                background-color: #2d2d2d;
                padding: 6px;
                font-weight: bold;
                border-bottom: 1px solid #3d3d3d;
            }
            QStatusBar {
                background-color: #252525;
                color: #B0B0B0;
                font-size: 11px;
            }
        """)

    # ---------------- Slot implementations ----------------

    def open_image_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Abrir Imagem", "",
            "Imagens (*.tif *.tiff *.jpg *.jpeg *.png *.bmp);;Todos os Arquivos (*.*)"
        )
        if file_path:
            self.load_image(file_path)

    def load_image(self, file_path: str):
        self._base_rgb = None
        if self.doc.load(file_path):
            self.canvas.set_image(self.doc.current_image, reset_zoom=True)
            self.setWindowTitle(f"PyImageJ Studio - {self.doc.title}")
            h, w = self.doc.shape[:2]
            self.lbl_status_dim.setText(f"Dimensões: {w} x {h}")
            self.valid_roi_mask = np.ones((h, w), dtype=bool)

            # Auto-detect scale bar if present
            calib, bbox = auto_detect_scale_bar(self.doc.current_image, known_distance=100.0, unit="µm")
            if calib:
                self.calibration = calib
                self.scale_box_crop = bbox
                # Exclude scale bar from valid ROI
                min_x, min_y, max_x, max_y = bbox
                self.valid_roi_mask[max(0, min_y - 5):, max(0, min_x - 5):] = False
                self.update_scale_status()
                self.status_bar.showMessage(f"Barra de escala detectada automaticamente ({calib.pixels:.0f} px = {calib.known_distance} {calib.unit})", 5000)

            # Initial threshold calculation
            self.on_threshold_method_selected("Otsu")
        else:
            QMessageBox.critical(self, "Erro", f"Não foi possível abrir a imagem:\n{file_path}")

    def save_image(self):
        if not self.doc.is_loaded:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Imagem", self.doc.title,
            "TIFF (*.tif);;PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp)"
        )
        if file_path:
            if self.doc.save(file_path):
                self.status_bar.showMessage(f"Imagem salva em {file_path}", 4000)
            else:
                QMessageBox.critical(self, "Erro", "Falha ao salvar imagem.")

    def undo(self):
        if self.doc.undo():
            self._base_rgb = None
            self.canvas.set_image(self.doc.current_image)
            self.status_bar.showMessage("Ação desfeita", 2000)

    def apply_filter(self, filter_name: str, **kwargs):
        if not self.doc.is_loaded:
            return
        self.doc.apply_filter(filter_name, **kwargs)
        self._base_rgb = None
        self.canvas.set_image(self.doc.current_image)
        self.status_bar.showMessage(f"Filtro aplicado: {filter_name}", 3000)

    def set_roi_mode(self, mode: str):
        # Uncheck other ROI actions
        self.act_roi_rect.setChecked(mode == "rect")
        self.act_roi_ellipse.setChecked(mode == "ellipse")
        self.act_roi_polygon.setChecked(mode == "polygon")
        self.canvas.set_roi_mode(mode)
        if mode == "polygon":
            self.status_bar.showMessage("Modo Polígono: clique pontos para desenhar e clique com botão DIREITO para fechar.", 6000)
        elif mode in ["rect", "ellipse"]:
            self.status_bar.showMessage(f"Modo {mode.capitalize()}: clique e arraste na imagem.", 4000)
        else:
            self.status_bar.showMessage("Seleção de ROI desativada.", 2000)

    def on_roi_mask_defined(self, mask: np.ndarray, desc: str):
        self.valid_roi_mask = mask.copy()
        if self.scale_box_crop:
            min_x, min_y, _, _ = self.scale_box_crop
            self.valid_roi_mask[max(0, min_y - 5):, max(0, min_x - 5):] = False
        self.status_bar.showMessage(f"ROI ativa: {desc}", 4000)
        self.on_threshold_preview(self.threshold_panel.slider.value(), self.threshold_panel.chk_dark.isChecked())

    def clear_roi(self):
        self.act_roi_rect.setChecked(False)
        self.act_roi_ellipse.setChecked(False)
        self.act_roi_polygon.setChecked(False)
        self.canvas.set_roi_mode("none")
        self.canvas.clear_roi()
        if self.doc.is_loaded:
            h, w = self.doc.shape[:2]
            self.valid_roi_mask = np.ones((h, w), dtype=bool)
            if self.scale_box_crop:
                min_x, min_y, _, _ = self.scale_box_crop
                self.valid_roi_mask[max(0, min_y - 5):, max(0, min_x - 5):] = False
            self.on_threshold_preview(self.threshold_panel.slider.value(), self.threshold_panel.chk_dark.isChecked())
        self.status_bar.showMessage("Seleção de ROI limpa.", 2000)

    def on_roi_selected(self, x: int, y: int, w: int, h: int):
        if self.doc.is_loaded and w > 0 and h > 0:
            img_h, img_w = self.doc.shape[:2]
            mask = np.zeros((img_h, img_w), dtype=bool)
            x0 = max(0, x)
            y0 = max(0, y)
            x1 = min(img_w, x + w)
            y1 = min(img_h, y + h)
            mask[y0:y1, x0:x1] = True
            self.valid_roi_mask = mask
            self.status_bar.showMessage(f"ROI selecionada: [{x0}, {y0}] até [{x1}, {y1}] ({w}x{h} px)", 4000)

    def on_pixel_hovered(self, x: int, y: int, val_str: str):
        calib_x = self.calibration.to_units_length(x)
        calib_y = self.calibration.to_units_length(y)
        unit = self.calibration.unit
        self.lbl_status_pos.setText(f"X: {x} ({calib_x:.1f}{unit})  Y: {y} ({calib_y:.1f}{unit})  {val_str}")

    def update_scale_status(self):
        unit = self.calibration.unit
        units_per_px = self.calibration.units_per_pixel
        px_per_unit = self.calibration.pixels_per_unit
        self.lbl_status_scale.setText(f"Escala: {units_per_px:.4f} {unit}/px ({px_per_unit:.2f} px/{unit})")

    def open_scale_dialog(self):
        if not self.doc.is_loaded:
            QMessageBox.warning(self, "Aviso", "Carregue uma imagem antes de calibrar a escala.")
            return

        dlg = ScaleDialog(self.calibration, self.doc.current_image, self)
        if dlg.exec():
            self.calibration = dlg.get_calibration()
            self.update_scale_status()
            self.status_bar.showMessage(f"Escala definida: {self.calibration.units_per_pixel:.4f} {self.calibration.unit}/pixel", 4000)

    def auto_detect_scale(self):
        if not self.doc.is_loaded:
            return
        calib, bbox = auto_detect_scale_bar(self.doc.current_image, known_distance=100.0, unit="µm")
        if calib:
            self.calibration = calib
            self.scale_box_crop = bbox
            h, w = self.doc.shape[:2]
            min_x, min_y, _, _ = bbox
            if self.valid_roi_mask is None:
                self.valid_roi_mask = np.ones((h, w), dtype=bool)
            self.valid_roi_mask[max(0, min_y - 5):, max(0, min_x - 5):] = False
            self.update_scale_status()
            QMessageBox.information(
                self, "Escala Detectada",
                f"Barra de escala detectada com sucesso!\n"
                f"Tamanho: {calib.pixels:.1f} pixels = {calib.known_distance} {calib.unit}\n"
                f"Escala: {calib.units_per_pixel:.4f} {calib.unit}/pixel"
            )
        else:
            QMessageBox.warning(self, "Aviso", "Não foi encontrada uma barra de escala na imagem.")

    def on_threshold_method_selected(self, method_name: str):
        if not self.doc.is_loaded:
            return
        gray = self.doc.get_grayscale()
        val = calculate_threshold(gray, method=method_name, mask=self.valid_roi_mask)
        self.threshold_panel.set_threshold_value(val)
        self.on_threshold_preview(val, self.threshold_panel.chk_dark.isChecked())

    def on_threshold_preview(self, threshold_val: int, dark_objects: bool):
        if not self.doc.is_loaded:
            return
        gray = self.doc.get_grayscale()
        binary = apply_threshold(gray, threshold_val, dark_objects=dark_objects, mask=self.valid_roi_mask)
        self.active_binary_mask = binary

        # Fast porosity calculation using numpy count_nonzero
        total_valid = int(np.count_nonzero(self.valid_roi_mask)) if self.valid_roi_mask is not None else binary.size
        pore_count = int(np.count_nonzero(binary))
        porosity_pct = (pore_count / total_valid * 100.0) if total_valid > 0 else 0.0
        self.threshold_panel.update_porosity_preview(porosity_pct)

        # High-performance overlay rendering
        if getattr(self, '_base_rgb', None) is None:
            if self.doc.current_image.ndim == 2:
                self._base_rgb = cv2.cvtColor(self.doc.current_image, cv2.COLOR_GRAY2RGB)
            else:
                self._base_rgb = self.doc.current_image.copy()

        preview = self._base_rgb.copy()
        mask = (binary > 0)
        # Direct vectorized red tint: blend red channel instantly
        preview[mask, 0] = np.clip(preview[mask, 0].astype(np.uint16) + 140, 0, 255).astype(np.uint8)
        preview[mask, 1] = (preview[mask, 1] // 3).astype(np.uint8)
        preview[mask, 2] = (preview[mask, 2] // 3).astype(np.uint8)
        self.canvas.update_image_fast(preview)

    def on_threshold_applied(self):
        if self.active_binary_mask is not None:
            self.doc.push_undo()
            self.doc.current_image = self.active_binary_mask.copy()
            self.canvas.set_image(self.doc.current_image)
            self.status_bar.showMessage("Limiarização aplicada e convertida em máscara binária.", 3000)

    def on_watershed_applied(self):
        if self.active_binary_mask is None:
            return
        self.active_binary_mask = binary_watershed(self.active_binary_mask)
        self.canvas.set_image(self.active_binary_mask)
        self.status_bar.showMessage("Separação de partículas por Watershed aplicada.", 3000)

    def on_reset_view(self):
        if self.doc.is_loaded:
            self.canvas.set_image(self.doc.current_image)

    def run_analyze_particles(self):
        if not self.doc.is_loaded:
            QMessageBox.warning(self, "Aviso", "Abra uma imagem antes de executar a análise.")
            return

        if self.active_binary_mask is None:
            # Generate binary mask using Otsu if not already binarized
            gray = self.doc.get_grayscale()
            thresh = calculate_threshold(gray, "Otsu", mask=self.valid_roi_mask)
            self.active_binary_mask = apply_threshold(gray, thresh, dark_objects=True, mask=self.valid_roi_mask)

        df, summary, overlay = analyze_particles(
            binary_mask=self.active_binary_mask,
            gray_image=self.doc.current_image,
            scale=self.calibration,
            min_size_px=5.0,
            valid_roi_mask=self.valid_roi_mask
        )

        self.canvas.set_image(overlay)
        sample_name = os.path.splitext(self.doc.title)[0]
        self.results_panel.set_results(
            df=df,
            summary=summary,
            scale=self.calibration,
            original_img=self.doc.current_image,
            overlay_img=overlay,
            sample_name=sample_name
        )
        self.dock_results.show()
        self.dock_results.raise_()
        self.status_bar.showMessage(f"Análise concluída: {summary.count} poros identificados ({summary.area_fraction_pct:.2f}% porosidade).", 5000)

    def run_batch_processing(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecione a Pasta de Imagens para Processamento em Lote")
        if not folder:
            return

        out_folder = os.path.join(folder, "resultados_analise")
        os.makedirs(out_folder, exist_ok=True)

        exts = (".tif", ".tiff", ".jpg", ".jpeg", ".png", ".bmp")
        files = [f for f in os.listdir(folder) if f.lower().endswith(exts)]
        if not files:
            QMessageBox.warning(self, "Aviso", "Nenhuma imagem encontrada na pasta selecionada.")
            return

        total_processed = 0
        summary_rows = []

        for fname in files:
            fpath = os.path.join(folder, fname)
            img = cv2.imread(fpath)
            if img is None:
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape

            calib, bbox = auto_detect_scale_bar(img, known_distance=100.0, unit="µm")
            if not calib:
                calib = self.calibration

            valid_mask = np.ones((h, w), dtype=bool)
            if bbox:
                min_x, min_y, _, _ = bbox
                valid_mask[max(0, min_y - 5):, max(0, min_x - 5):] = False

            thresh = calculate_threshold(gray, "Otsu", mask=valid_mask)
            binary = apply_threshold(gray, thresh, dark_objects=True, mask=valid_mask)

            df, summ, overlay = analyze_particles(
                binary_mask=binary,
                gray_image=img,
                scale=calib,
                min_size_px=5.0,
                valid_roi_mask=valid_mask
            )

            base_name = os.path.splitext(fname)[0]
            # Save overlay image
            cv2.imwrite(os.path.join(out_folder, f"{base_name}_overlay.jpg"), overlay)
            # Save particles CSV
            df.to_csv(os.path.join(out_folder, f"{base_name}_particulas.csv"), index=False)

            summary_rows.append({
                "Imagem": fname,
                "Poros_Contados": summ.count,
                "Porosidade_Pct": summ.area_fraction_pct,
                "Area_Total_um2": summ.total_analyzed_area_units,
                "Diametro_Medio_um": summ.mean_equiv_diameter_units,
                "Circularidade_Media": summ.mean_circularity,
                "Densidade_mm2": summ.density_per_mm2
            })
            total_processed += 1

        # Save consolidated summary
        from core.particle_table import ParticleTable
        df_summary = ParticleTable(summary_rows)
        df_summary.to_csv(os.path.join(out_folder, "RESUMO_LOTE_CONSOLIDADO.csv"), index=False)

        QMessageBox.information(
            self, "Processamento em Lote Concluído",
            f"Processamento concluído com sucesso!\n"
            f"Total de imagens analisadas: {total_processed}\n"
            f"Resultados e imagens salvas em:\n{out_folder}"
        )
