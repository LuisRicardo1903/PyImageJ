"""
Technical Report Generator module.
Exports professional ISO/ASTM style metallographic analysis reports in HTML/PDF format
with embedded base64 images, KPI cards, and statistical tables.
"""

from datetime import datetime
import base64
import os
import cv2
import numpy as np
from core.particle_table import ParticleTable
from core.particle_analyzer import ParticleSummary
from core.scale import ScaleCalibration


def encode_image_base64(img_bgr_or_rgb: np.ndarray) -> str:
    """Encodes numpy image to base64 JPEG string for standalone HTML embedding."""
    if img_bgr_or_rgb is None or img_bgr_or_rgb.size == 0:
        return ""
    if img_bgr_or_rgb.ndim == 3 and img_bgr_or_rgb.shape[2] == 3:
        # Check if RGB or BGR
        bgr = cv2.cvtColor(img_bgr_or_rgb, cv2.COLOR_RGB2BGR)
    else:
        bgr = img_bgr_or_rgb
    _, buffer = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    return base64.b64encode(buffer).decode("utf-8")


def generate_html_report(
    original_img: np.ndarray,
    overlay_img: np.ndarray,
    df: ParticleTable,
    summary: ParticleSummary,
    scale: ScaleCalibration,
    sample_name: str = "Amostra_01",
    output_html_path: str = "laudo_metalografico.html"
) -> str:
    """
    Generates a standalone, professional HTML report.
    """
    now_str = datetime.now().strftime("%d/%m/%Y às %H:%M")
    orig_b64 = encode_image_base64(original_img)
    over_b64 = encode_image_base64(overlay_img)

    unit = scale.unit
    unit_area = f"{unit}²"

    # Compute additional statistics if df has items
    if len(df) > 0:
        diam_mean = df["Eq_Diam"].mean()
        diam_std = df["Eq_Diam"].std()
        diam_min = df["Eq_Diam"].min()
        diam_max = df["Eq_Diam"].max()
        diam_p50 = df["Eq_Diam"].median()

        circ_mean = df["Circularity"].mean()
        circ_std = df["Circularity"].std()
        circ_min = df["Circularity"].min()
        circ_max = df["Circularity"].max()

        top_pores = df.sort_values(by="Area", ascending=False).head(15)
        top_rows_html = ""
        for _, r in top_pores.iterrows():
            top_rows_html += f"""
            <tr>
                <td>#{int(r['ID'])}</td>
                <td>{r['Area']:.2f}</td>
                <td>{r['Eq_Diam']:.2f}</td>
                <td>{r['Perimeter']:.2f}</td>
                <td>{r['Circularity']:.3f}</td>
                <td>{r['Aspect_Ratio']:.2f}</td>
                <td>{r['Roundness']:.2f}</td>
                <td>{r['Solidity']:.3f}</td>
            </tr>
            """
    else:
        diam_mean = diam_std = diam_min = diam_max = diam_p50 = 0
        circ_mean = circ_std = circ_min = circ_max = 0
        top_rows_html = "<tr><td colspan='8'>Nenhum poro identificado.</td></tr>"

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Laudo Técnico de Porosidade - {sample_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f8f9fa;
            color: #212529;
            margin: 0;
            padding: 30px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: #ffffff;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 3px solid #007acc;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .title h1 {{
            margin: 0;
            font-size: 24px;
            color: #1a1a1a;
        }}
        .title p {{
            margin: 5px 0 0 0;
            color: #666;
            font-size: 14px;
        }}
        .meta {{
            text-align: right;
            font-size: 13px;
            color: #555;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }}
        .kpi-card {{
            background: #f1f5f9;
            border-left: 4px solid #007acc;
            padding: 15px;
            border-radius: 4px;
        }}
        .kpi-card.highlight {{
            border-left-color: #2e7d32;
            background: #e8f5e9;
        }}
        .kpi-card .label {{
            font-size: 12px;
            color: #555;
            text-transform: uppercase;
            font-weight: bold;
        }}
        .kpi-card .value {{
            font-size: 22px;
            font-weight: bold;
            color: #111;
            margin-top: 5px;
        }}
        .image-comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .image-box {{
            text-align: center;
        }}
        .image-box img {{
            width: 100%;
            height: auto;
            border-radius: 4px;
            border: 1px solid #ddd;
        }}
        .image-box .caption {{
            margin-top: 8px;
            font-size: 13px;
            color: #444;
            font-weight: 500;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-size: 13px;
        }}
        th, td {{
            padding: 10px;
            text-align: center;
            border: 1px solid #e0e0e0;
        }}
        th {{
            background-color: #007acc;
            color: #ffffff;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: bold;
            color: #1a1a1a;
            margin-top: 30px;
            margin-bottom: 15px;
            border-bottom: 2px solid #eee;
            padding-bottom: 8px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            color: #777;
        }}
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
                padding: 10px;
            }}
            .btn-print {{
                display: none;
            }}
        }}
        .btn-print {{
            background: #007acc;
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 14px;
            font-weight: bold;
            border-radius: 4px;
            cursor: pointer;
            float: right;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <button class="btn-print" onclick="window.print()">🖨️ Imprimir / Salvar em PDF</button>
        <div style="clear: both;"></div>

        <div class="header">
            <div class="title">
                <h1>Laudo Técnico de Análise Metalográfica</h1>
                <p>Caracterização Morfológica e Fração Volumétrica de Porosidade</p>
            </div>
            <div class="meta">
                <div><strong>Amostra:</strong> {sample_name}</div>
                <div><strong>Data:</strong> {now_str}</div>
                <div><strong>Software:</strong> PyImageJ Studio v1.0.0</div>
            </div>
        </div>

        <div class="kpi-grid">
            <div class="kpi-card highlight">
                <div class="label">Porosidade Total</div>
                <div class="value">{summary.area_fraction_pct:.2f} %</div>
            </div>
            <div class="kpi-card">
                <div class="label">Total de Poros</div>
                <div class="value">{summary.count} poros</div>
            </div>
            <div class="kpi-card">
                <div class="label">Diâmetro Médio</div>
                <div class="value">{diam_mean:.2f} {unit}</div>
            </div>
            <div class="kpi-card">
                <div class="label">Densidade de Poros</div>
                <div class="value">{summary.density_per_mm2} /mm²</div>
            </div>
        </div>

        <div class="image-comparison">
            <div class="image-box">
                <img src="data:image/jpeg;base64,{orig_b64}" alt="Micrografia Original">
                <div class="caption">1. Micrografia Original (Calibração: {scale.pixels_per_unit:.2f} px/{unit})</div>
            </div>
            <div class="image-box">
                <img src="data:image/jpeg;base64,{over_b64}" alt="Segmentação de Poros">
                <div class="caption">2. Mapeamento e Contornos dos Poros Identificados ({summary.count} partículas)</div>
            </div>
        </div>

        <div class="section-title">Quadro Estatístico de Distribuição</div>
        <table>
            <thead>
                <tr>
                    <th>Parâmetro</th>
                    <th>Média</th>
                    <th>Desvio Padrão</th>
                    <th>Mínimo</th>
                    <th>Mediana (P50)</th>
                    <th>Máximo</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>Diâmetro Equivalente ({unit})</strong></td>
                    <td>{diam_mean:.2f}</td>
                    <td>±{diam_std:.2f}</td>
                    <td>{diam_min:.2f}</td>
                    <td>{diam_p50:.2f}</td>
                    <td>{diam_max:.2f}</td>
                </tr>
                <tr>
                    <td><strong>Circularidade (0 a 1)</strong></td>
                    <td>{circ_mean:.3f}</td>
                    <td>±{circ_std:.3f}</td>
                    <td>{circ_min:.3f}</td>
                    <td>{summary.mean_circularity:.3f}</td>
                    <td>{circ_max:.3f}</td>
                </tr>
                <tr>
                    <td><strong>Área Unitária ({unit_area})</strong></td>
                    <td>{summary.mean_area_units:.2f}</td>
                    <td>--</td>
                    <td>{df['Area'].min() if len(df)>0 else 0:.2f}</td>
                    <td>{df['Area'].median() if len(df)>0 else 0:.2f}</td>
                    <td>{df['Area'].max() if len(df)>0 else 0:.2f}</td>
                </tr>
            </tbody>
        </table>

        <div class="section-title">Maiores Poros Detectados (Top 15 por Área)</div>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Área ({unit_area})</th>
                    <th>Diâm. Equiv. ({unit})</th>
                    <th>Perímetro ({unit})</th>
                    <th>Circularidade</th>
                    <th>Aspect Ratio</th>
                    <th>Roundness</th>
                    <th>Solidity</th>
                </tr>
            </thead>
            <tbody>
                {top_rows_html}
            </tbody>
        </table>

        <div class="footer">
            <div>Área total examinada: {summary.total_analyzed_area_units:,.1f} {unit_area} | Metodologia: ImageJ 1.54 / ASTM E1245</div>
            <div>Emitido por PyImageJ Studio</div>
        </div>
    </div>
</body>
</html>
"""
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_html_path
