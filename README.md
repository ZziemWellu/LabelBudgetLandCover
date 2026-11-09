# Label wisely, not heavily

Code, results and manuscript for *"Label wisely, not heavily: annotation budgets for land-cover
mapping with frozen self-supervised vision features"* (Z.P. Wellu and S. Mensah, University of
Ghana), prepared for *Remote Sensing Applications: Society and Environment*.

The study measures how many labels land-cover mapping needs when it is built on frozen DINOv2
features. It uses DeepGlobe and LoveDA and covers dense versus point annotation, four classifiers,
four backbones, a DeepLabV3 fine-tuning baseline and urban–rural transfer.

## Contents

| Path | What it is |
|---|---|
| `common.py`, `lab.py` | Data loading, feature extraction, classifiers, exact pixel-level scoring |
| `prepare.py` | Extracts and caches DINOv2 ViT-B/14 patch features and patch label histograms |
| `run_final.py` | Main experiment: budgets, point labels, sensitivity, urban–rural transfer → `outputs/final.jsonl` |
| `run_backbones.py` | Backbone comparison (DINOv2 ViT-S/B/L, ResNet-50) → `outputs/backbone_*.jsonl` |
| `finetune.py` | DeepLabV3-ResNet50 fine-tuning baseline → `outputs/finetune.jsonl` |
| `analyze_final.py` | Tables (`outputs/final_tables.md`) and figures (`outputs/figures_final/`) |
| `robustness.py` | Fold-level tests, labelled patches per image, break-even cost → `outputs/robustness.md` |
| `run_experiments.py`, `analyze.py` | Earlier pilot run (`outputs/pilot/`), superseded by the files above |
| `manuscript/` | Manuscript (.docx/.pdf), highlights, figures, graphical abstract and the scripts that build them |
| `outputs/` | Splits, per-run results, confusion matrices and logs |

Every number in the manuscript comes from the result files in `outputs/`.
`outputs/finetune_os8_abandoned/` holds one abandoned fine-tuning run at output stride 8. It was
too slow on the GPU and is not used in the paper.

## Reproducing

1. Download [DeepGlobe Land Cover](https://competitions.codalab.org/competitions/18468) and
   [LoveDA](https://github.com/Junjue-Wang/LoveDA). Neither dataset is redistributed here.
2. Set `DATA_ROOT` in `common.py` to your dataset folder.
3. Run, in order:

   ```
   python prepare.py
   python run_final.py
   python run_backbones.py
   python finetune.py
   python analyze_final.py
   python robustness.py
   ```
4. Build the manuscript:

   ```
   python manuscript/make_fig1.py
   python manuscript/build_manuscript.py
   ```

Large feature caches (about 9 GB) are not in the repository; `prepare.py` and `run_backbones.py`
regenerate them.

Environment: Python 3.10, PyTorch 2.1, scikit-learn 1.4, python-docx; a 6 GB GPU (GTX 1060 Max-Q)
was enough.
