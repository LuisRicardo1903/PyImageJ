"""
Results and measurements table panel.
Displays individual particle measurements, summary statistics,
and handles export to CSV/Excel.
"""

from typing import Optional
import os
import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QFileDialog, QLineEdit, QHeaderView, QMessageBox
)
from core.particle_analyzer import ParticleSummary


class ResultsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dataframe: Optional[pd.DataFrame] = None
        self.summary: Optional[ParticleSummary] = None
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

        # Filter bar and export button
        h_bar = QHBoxLayout()
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("Filtrar por ID ou valor...")
        self.txt_filter.textChanged.connect(self.filter_table)
        h_bar.addWidget(self.txt_filter)

        self.btn_export = QPushButton("Exportar CSV / Excel")
        self.btn_export.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 5px 12px;")
        self.btn_export.clicked.connect(self.export_csv)
        h_bar.addWidget(self.btn_export)

        layout.addLayout(h_bar)

        # Table
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
        layout.addWidget(self.table)

    def set_results(self, df: pd.DataFrame, summary: ParticleSummary, unit: str = "µm"):
        self.dataframe = df
        self.summary = summary

        # Format summary string
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
