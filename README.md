# PyImageJ Studio

**PyImageJ Studio** é uma reconstrução moderna, ultrarrápida e intuitiva do **ImageJ (1.54)** em **Python + PySide6 (Qt)**, desenvolvida especificamente para análise metalográfica, contagem de partículas e medição de porosidade.

---

## 🚀 Principais Recursos

- **Calibração Automática de Escala**: Detecta automaticamente caixas de legenda e barras de escala em micrografias (ex: 100 µm = 189 px), calculando a razão $\mu\text{m}/\text{pixel}$ sem necessidade de cliques manuais.
- **Exclusão Inteligente de Legenda**: Exclui a área da legenda da análise para evitar falsos positivos na contagem de poros.
- **Limiarização em Tempo Real (Live Threshold)**: Slider interativo com visualização imediata da máscara sobre a imagem e cálculo dinâmico da porcentagem de porosidade estimada.
- **Algoritmos do ImageJ**: Otsu, Triangle, Default (IsoData), Li, Yen, Mean, Minimum e Watershed para separação de partículas aglomeradas (implementados em C++/OpenCV para máxima velocidade).
- **Analyze Particles Completo**: Calcula Área ($\mu\text{m}^2$), Diâmetro Equivalente, Perímetro, Circularidade ($4\pi \cdot \text{Área}/\text{Perímetro}^2$), Aspect Ratio, Roundness e Solidity.
- **Tabela e Histogramas Nativos**: Visualização em abas com tabela completa de partículas e histogramas de frequência (Diâmetro Equivalente e Circularidade) renderizados nativamente em Qt.
- **Ferramentas Avançadas de ROI**: Seleção de regiões de interesse por Retângulo, Elipse/Círculo e Polígono livre com realce dourado de alto contraste (`#FFD600`).
- **Laudo Técnico em PDF/HTML**: Botão com 1 clique para exportar relatório completo de análise com imagens comparativas, KPIs de porosidade e tabelas estatísticas.
- **Arquitetura Leve e Otimizada (v1.0.1)**: Removidas dependências pesadas (`scipy`, `scikit-image`, `pandas`), reduzindo o tamanho do executável de 116 MB para menos de 50 MB com abertura instantânea.
- **Ícone Personalizado**: Design exclusivo de microscopia/metalográfica integrado no executável `.exe` e na janela.
- **Processamento em Lote (Batch Processing)**: Processa uma pasta inteira de micrografias com um único clique, gerando imagens com contornos destacados e um arquivo CSV consolidado.

---

## 💻 Como Executar

### Opção 1: Baixar o Executável Pré-compilado (.exe)
Baixe a última release na aba [Releases](https://github.com/LuisRicardo1903/PyImageJ/releases) do repositório no GitHub.

### Opção 2: Executar diretamente via Python (Windows ou Linux)
1. Certifique-se de que o Python 3.9+ está instalado.
2. Dê duplo clique no arquivo **`run.bat`** (no Windows) ou execute no terminal:
   ```bash
   pip install -r requirements.txt
   python main.py
   ```

### Opção 3: Gerar o Executável Standalone (.exe) Localmente

Você pode escolher entre dois modos de compilação:

1. **Modo Rápido / Diretório (`build_exe_fast.bat`) - Recomendado**:
   - Compila com `--onedir`.
   - **Inicialização instantânea** (menos de 1 segundo).
   - O executável fica pronto em `dist\PyImageJ-Studio\PyImageJ-Studio.exe`.

2. **Modo Arquivo Único (`build_exe.bat`)**:
   - Compila em um único arquivo `.exe` portátil.
   - Otimizado com exclusão estrita de módulos desnecessários para reduzir o tamanho.

---

## 📂 Estrutura do Projeto

```
PyImageJ-Studio/
├── core/
│   ├── processor.py          # Carregamento, filtros (Gaussiano, Mediana) e histórico Undo
│   ├── scale.py              # Calibração e auto-detecção de barra de escala
│   ├── threshold.py          # Algoritmos de thresholding e operações binárias (Watershed)
│   ├── particle_analyzer.py  # Fórmulas 1:1 do ImageJ para medição de partículas
│   ├── particle_table.py     # Container tabular leve e rápido (substitui pandas)
│   └── report_generator.py   # Gerador de laudos técnicos em PDF/HTML
├── gui/
│   ├── canvas.py             # Canvas interativo com zoom, pan, ROIs e tracking de pixels
│   ├── main_window.py        # Janela principal moderna em Dark Theme
│   ├── results_panel.py      # Tabela de medições, exportação CSV e abas de histogramas
│   ├── histogram_widget.py   # Widget nativo de histogramas vetoriais (QPainter)
│   ├── scale_dialog.py       # Diálogo Set Scale com botão auto-detectar
│   └── threshold_panel.py    # Painel lateral com slider e live preview
├── icon.ico                  # Ícone da aplicação multi-resolução para Windows
├── icon.png                  # Ícone em alta resolução PNG
├── build_exe.bat             # Script para gerar o executável único Windows (.exe)
├── build_exe_fast.bat        # Script para gerar o executável no modo onedir rápido
├── run.bat                   # Atalho de execução rápida
├── main.py                   # Ponto de entrada da aplicação
└── requirements.txt          # Dependências mínimas e leves
```
