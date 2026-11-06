# PyImageJ Studio

**PyImageJ Studio** é uma reconstrução moderna, rápida e intuitiva do **ImageJ (1.54)** em **Python + PySide6 (Qt)**, desenvolvida especificamente para análise metalográfica, contagem de partículas e medição de porosidade.

---

## 🚀 Principais Recursos

- **Calibração Automática de Escala**: Detecta automaticamente caixas de legenda e barras de escala em micrografias (ex: 100 µm = 189 px), calculando a razão $\mu\text{m}/\text{pixel}$ sem necessidade de cliques manuais.
- **Exclusão Inteligente de Legenda**: Exclui a área da legenda da análise para evitar falsos positivos na contagem de poros.
- **Limiarização em Tempo Real (Live Threshold)**: Slider interativo com visualização imediata da máscara sobre a imagem e cálculo dinâmico da porcentagem de porosidade estimada.
- **Algoritmos do ImageJ**: Otsu, Triangle, Default (IsoData), Li, Yen, Mean, Minimum e Watershed para separação de partículas aglomeradas.
- **Analyze Particles Completo**: Calcula Área ($\mu\text{m}^2$), Diâmetro Equivalente, Perímetro, Circularidade ($4\pi \cdot \text{Área}/\text{Perímetro}^2$), Aspect Ratio, Roundness e Solidity.
- **Tabela de Resultados Ordenável**: Busca rápida por ID/valores e exportação direta para **CSV** ou **Excel**.
- **Processamento em Lote (Batch Processing)**: Processa uma pasta inteira de micrografias com um único clique, gerando imagens com contornos destacados e um arquivo CSV consolidado.

---

## 💻 Como Executar

### Opção 1: Executar diretamente via Python (Windows ou Linux)
1. Certifique-se de que o Python 3.9+ está instalado.
2. Dê duplo clique no arquivo **`run.bat`** (no Windows) ou execute no terminal:
   ```bash
   pip install -r requirements.txt
   python main.py
   ```

### Opção 2: Gerar o Executável Standalone (.exe)
1. Dê duplo clique no arquivo **`build_exe.bat`** no Windows.
2. O PyInstaller irá compilar todos os arquivos e criar o executável final em:
   ```
   dist\PyImageJ-Studio.exe
   ```
3. O `.exe` gerado pode ser copiado para qualquer outro computador Windows sem precisar instalar Python!

---

## 📂 Estrutura do Projeto

```
PyImageJ-Studio/
├── core/
│   ├── processor.py          # Carregamento, filtros (Gaussiano, Mediana) e histórico Undo
│   ├── scale.py              # Calibração e auto-detecção de barra de escala
│   ├── threshold.py          # Algoritmos de thresholding e operações binárias (Watershed)
│   └── particle_analyzer.py  # Fórmulas 1:1 do ImageJ para medição de partículas
├── gui/
│   ├── canvas.py             # Canvas interativo com zoom, pan e tracking de pixels
│   ├── main_window.py        # Janela principal moderna em Dark Theme
│   ├── results_panel.py      # Tabela de medições e exportação CSV/Excel
│   ├── scale_dialog.py       # Diálogo Set Scale com botão auto-detectar
│   └── threshold_panel.py    # Painel lateral com slider e live preview
├── build_exe.bat             # Script para gerar o executável Windows (.exe)
├── run.bat                   # Atalho de execução rápida
├── main.py                   # Ponto de entrada da aplicação
└── requirements.txt          # Dependências do projeto
```
