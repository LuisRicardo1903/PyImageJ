"""
Results and measurements panel.
Displays individual particle measurements, summary statistics,
interactive native histograms, and handles export to CSV/Excel and Technical PDF/HTML Report.
"""

from typing import Optional
import os
import pandas as pd
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QFileDialog, QLineEdit, QHeaderView,
    QMessageBox, QTabWidget
)
from core.particle_analyzer import ParticleSummary
from core.scale import ScaleCalibration
from core.report_generator import generate_html_report
from gui.histogram_widget import HistogramWidget
import numpy as np


class ResultsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dataframe: Optional[pd.DataFrame] = None
        self.summary: Optional[ParticleSummary] = None
        self.scale: ScaleCalibration = ScaleCalibration()
        self.original_image: Optional[np.ndarray] = None
        self.overlay_image: Optional[np.ndarray] = None
        self.sample_name: str = "Amostra"

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Summary Header
        self.lbl_summary = QLabel("Nenhuma análise executada ainda.")
        self.lbl_summary.setStyleSheet("""
            background-color: #2b2b2b;
            color: #E0E0E0;
            padding: 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        """)
        layout.addWidget(self.lbl_summary)

        # Top Action Bar: Search, Export CSV, Generate Technical Report
        h_bar = QHBoxLayout()
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("Filtrar por ID ou valor...")
        self.txt_filter.textChanged.connect(self.filter_table)
        h_bar.addWidget(self.txt_filter)

        self.btn_export = QPushButton("Exportar CSV / Excel")
        self.btn_export.setStyleSheet("background-color: #388e3c; color: white; font-weight: bold; padding: 5px 12px;")
        self.btn_export.clicked.connect(self.export_csv)
        h_bar.addWidget(self.btn_export)

        self.btn_report = QPushButton("📄 Gerar Laudo Técnico (PDF)")
        self.btn_report.setStyleSheet("background-color: #0288d1; color: white; font-weight: bold; padding: 5px 12px;")
        self.btn_report.clicked.connect(self.generate_report)
        h_bar.addWidget(self.btn_report)

        layout.addLayout(h_bar)

        # Tabs: Table, Size Histogram, Circularity Histogram
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #333333; background: #242424; }
            QTabBar::tab { background: #2d2d2d; color: #b0b0b0; padding: 6px 14px; font-weight: 500; }
            QTabBar::tab:selected { background: #007acc; color: white; font-weight: bold; }
        """)

        # Tab 1: Table
        tab_table = QWidget()
        l_tab1 = QVBoxLayout(tab_table)
        l_tab1.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #242424;
                color: #FFFFFF;
                gridline-color: #3a3a3a;
                selection-background-color: #007acc;
            }
            QHeaderView::section {
                background-color: #333333;
                color: #FFFFFF;
                padding: 4px;
                font-weight: bold;
                border: 1px solid #444444;
            }
        """)
        l_tab1.addWidget(self.table)
        self.tabs.addTab(tab_table, "📋 Tabela de Medições")

        # Tab 2: Size Histogram
        self.hist_size = HistogramWidget(title="Distribuição do Diâmetro Equivalente dos Poros", unit="µm", color=QColor("#1976d2"))
        self.tabs.addTab(self.hist_size, "📊 Histograma de Tamanhos")

        # Tab 3: Circularity Histogram
        self.hist_circ = HistogramWidget(title="Distribuição de Circularidade (1.0 = Esférico)", unit="", color=QColor("#388e3c"))
        self.tabs.addTab(self.hist_circ, "🔵 Histograma de Circularidade")

        layout.addWidget(self.tabs)

    def set_results(
        self,
        df: pd.DataFrame,
        summary: ParticleSummary,
        scale: ScaleCalibration,
        original_img: Optional[np.ndarray] = None,
        overlay_img: Optional[np.ndarray] = None,
        sample_name: str = "Amostra"
    ):
        self.dataframe = df
        self.summary = summary
        self.scale = scale
        self.original_image = original_img
        self.overlay_image = overlay_img
        self.sample_name = sample_name

        unit = scale.unit
        unit_area = f"{unit}²"
        self.lbl_summary.setText(
            f"<b>Contagem:</b> {summary.count} poros | "
            f"<b>Porosidade:</b> <font color='#4CAF50'>{summary.area_fraction_pct:.2f}%</font> | "
            f"<b>Área Total Analisada:</b> {summary.total_analyzed_area_units:,.1f} {unit_area} | "
            f"<b>Diâmetro Médio:</b> {summary.mean_equiv_diameter_units:.2f} {unit} | "
            f"<b>Circularidade Média:</b> {summary.mean_circularity:.3f} | "
            f"<b>Densidade:</b> {summary.density_per_mm2} poros/mm²"
        )

        self.populate_table(df)

        # Update Histograms
        if len(df) > 0:
            self.hist_size.unit = unit
            self.hist_size.set_data(df["Eq_Diam"].tolist(), bins=25)
            self.hist_circ.set_data(df["Circularity"].tolist(), bins=20)
        else:
            self.hist_size.set_data([])
            self.hist_circ.set_data([])

    def populate_table(self, df: pd.DataFrame):
        self.table.setSortingEnabled(False)
        self.table.clear()
        if df is None or len(df) == 0:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return

        columns = list(df.columns)
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setRowCount(len(df))

        for row_idx, row in df.iterrows():
            for col_idx, col_name in enumerate(columns):
                val = row[col_name]
                item = QTableWidgetItem()
                if isinstance(val, (int, float)):
                    item.setData(Qt.DisplayRole, float(val) if isinstance(val, float) else int(val))
                else:
                    item.setText(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(int(row_idx), col_idx, item)

        self.table.setSortingEnabled(True)

    def filter_table(self, text: str):
        text = text.lower().strip()
        for r in range(self.table.rowCount()):
            match = False
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                if item and text in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(r, not match if text else False)

    def export_csv(self):
        if self.dataframe is None or len(self.dataframe) == 0:
            QMessageBox.warning(self, "Exportar", "Não há dados para exportar.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Medições", "medicoes_poros.csv", "Arquivo CSV (*.csv);;Excel (*.xlsx)"
        )
        if file_path:
            try:
                if file_path.endswith(".xlsx"):
                    self.dataframe.to_excel(file_path, index=False)
                else:
                    self.dataframe.to_csv(file_path, index=False)
                QMessageBox.information(self, "Sucesso", f"Resultados exportados para:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao exportar arquivo:\n{e}")

    def generate_report(self):
        if self.dataframe is None or len(self.dataframe) == 0 or self.summary is None:
            QMessageBox.warning(self, "Aviso", "Execute a análise de partículas antes de gerar o laudo.")
            return

        default_name = f"Laudo_{self.sample_name}.html"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Laudo Técnico", default_name, "Documento HTML / PDF (*.html)"
        )
        if not file_path:
            return

        try:
            generate_html_report(
                original_img=self.original_image,
                overlay_img=self.overlay_image,
                df=self.dataframe,
                summary=self.summary,
                scale=self.scale,
                sample_name=self.sample_name,
                output_html_path=file_path
            )
            # Open automatically in default browser for instant viewing/printing to PDF
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            QMessageBox.information(
                self, "Laudo Gerado",
                f"Laudo técnico gerado com sucesso!\n"
                f"Arquivo salvo em:\n{file_path}\n\n"
                f"O relatório foi aberto no seu navegador. Você pode imprimi-lo ou salvá-lo em PDF com 'Ctrl+P'!"
            )
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao gerar laudo:\n{e}")
