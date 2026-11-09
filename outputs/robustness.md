### DeepGlobe fold-level paired tests (3 draws averaged within each fold; n = 5 folds)

| Comparison | budget | mean diff | p (fold-level) | p_Holm | folds with diff > 0 |
|---|---|---|---|---|---|
| probe − cluster | 1 | -1.7 | 0.21 | 0.62 | 1/5 |
| probe − cluster | 2 | -0.7 | 0.45 | 0.62 | 1/5 |
| probe − cluster | 5 | +2.4 | 0.24 | 0.62 | 4/5 |
| probe − cluster | 10 | +6.4 | 0.0095 | 0.038 | 5/5 |
| probe − cluster | 25 | +13.8 | 1.4e-05 | 7.8e-05 | 5/5 |
| probe − cluster | 50 | +18.6 | 1.3e-05 | 7.8e-05 | 5/5 |
| probe − cluster | 100 | +23.0 | 1.4e-06 | 9.6e-06 | 5/5 |
| probe − cluster | 250 | +27.5 | 1.6e-07 | 1.3e-06 | 5/5 |
| probe − cluster | all | +29.5 | 1.1e-07 | 1e-06 | 5/5 |
| balanced − probe | 1 | +0.9 | 0.0023 | 0.012 | 5/5 |
| balanced − probe | 2 | +1.3 | 0.008 | 0.024 | 5/5 |
| balanced − probe | 5 | +1.4 | 0.00082 | 0.0066 | 5/5 |
| balanced − probe | 10 | +1.9 | 0.0015 | 0.0087 | 5/5 |
| balanced − probe | 25 | +0.5 | 0.41 | 0.46 | 3/5 |
| balanced − probe | 50 | -0.5 | 0.23 | 0.46 | 2/5 |
| balanced − probe | 100 | -1.3 | 0.0043 | 0.017 | 0/5 |
| balanced − probe | 250 | -2.0 | 0.00084 | 0.0066 | 0/5 |
| balanced − probe | all | -2.6 | 5.9e-05 | 0.00053 | 0/5 |
| 100 points − 5 images | — | +11.4 | 0.0012 | — | 5/5 |
| 300 points − 10 images | — | +11.4 | 0.0035 | — | 5/5 |
| 1000 points − 50 images | — | -0.1 | 0.9 | — | 2/5 |
| 30000 points − 250 images | — | +0.4 | 0.19 | — | 4/5 |

### Labelled training patches per image after the 50% purity rule

- DeepGlobe: mean 1366 of 1369 patches per image are labelled (median 1368; 99.8%).
- LoveDA train: mean 1308 of 1369 patches per image are labelled (median 1361; 95.6%).

### Break-even annotation cost (from equal-accuracy pairs)

- DeepGlobe: 1000 points ≈ 50 images (52.4 vs 52.5) → point labelling is cheaper whenever labelling 20 points takes less time than annotating one 2448 × 2448 image.
- DeepGlobe: 30,000 points ≈ 250 images (62.2 vs 61.9) → break-even at 120 points per image.
- LoveDA: 30,000 points (43.8) ≈ 250 images (44.1) → break-even at 120 points per image.
- Patch labels supplied: DeepGlobe 50 images ≈ 68,289; 250 images ≈ 341,444; LoveDA 250 images ≈ 327,067.
