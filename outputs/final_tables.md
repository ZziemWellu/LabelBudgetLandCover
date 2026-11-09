
### Table: DeepGlobe mIoU (%) vs. labelled images (mean ± SD over 15 folds×draws)

| labelled images   |   area (km²) | Linear probe   | Class-balanced probe   | Cluster-then-label (K=50)   | Linear − cluster                  | Balanced − linear                |
|:------------------|-------------:|:---------------|:-----------------------|:----------------------------|:----------------------------------|:---------------------------------|
| 1                 |         1.5  | 14.5 ± 4.3     | 15.4 ± 4.5             | 16.2 ± 6.0                  | -1.7 (d_z=-0.4, p_Holm=0.34)      | +0.9 (d_z=1.9, p_Holm=1.8e-05)*  |
| 2                 |         3    | 19.2 ± 5.8     | 20.5 ± 5.7             | 19.8 ± 6.3                  | -0.7 (d_z=-0.1, p_Holm=0.6)       | +1.3 (d_z=1.3, p_Holm=0.00052)*  |
| 5                 |         7.49 | 27.6 ± 6.7     | 29.1 ± 6.6             | 25.3 ± 6.0                  | +2.4 (d_z=0.5, p_Holm=0.24)       | +1.4 (d_z=1.5, p_Holm=0.00021)*  |
| 10                |        14.98 | 35.6 ± 7.0     | 37.5 ± 6.1             | 29.2 ± 6.1                  | +6.4 (d_z=1.5, p_Holm=0.00018)*   | +1.9 (d_z=1.2, p_Holm=0.0015)*   |
| 25                |        37.45 | 45.9 ± 5.2     | 46.5 ± 4.1             | 32.1 ± 4.5                  | +13.8 (d_z=5.0, p_Holm=7.4e-11)*  | +0.5 (d_z=0.3, p_Holm=0.24)      |
| 50                |        74.91 | 52.5 ± 3.0     | 52.0 ± 2.2             | 33.9 ± 2.5                  | +18.6 (d_z=6.4, p_Holm=3.2e-12)*  | -0.5 (d_z=-0.5, p_Holm=0.16)     |
| 100               |       149.82 | 57.2 ± 1.3     | 55.9 ± 1.4             | 34.3 ± 2.1                  | +23.0 (d_z=11.9, p_Holm=7.7e-16)* | -1.3 (d_z=-2.0, p_Holm=1.8e-05)* |
| 250               |       374.54 | 61.9 ± 0.7     | 59.9 ± 1.1             | 34.3 ± 1.8                  | +27.5 (d_z=19.3, p_Holm=1e-18)*   | -2.0 (d_z=-3.4, p_Holm=2.2e-08)* |
| all               |       961.83 | 64.1 ± 0.9     | 61.5 ± 1.0             | 34.6 ± 1.8                  | +29.5 (d_z=22.8, p_Holm=1.1e-19)* | -2.6 (d_z=-8.6, p_Holm=9e-14)*   |

Zero labels (k-means, K = #classes, Hungarian-matched on test — optimistic): 20.6 ± 2.4. Patch-oracle ceiling (every 14×14 patch assigned its majority class): 90.2 ± 0.7. Paired differences: same labelled images; Holm correction across the 9 budgets; * p_Holm<0.05.
- DeepGlobe: probe exceeds the 0-label baseline from n=5 images; full-pool mIoU 64.1 (71% of the patch ceiling); 80/90/95% of full-pool mIoU reached at n=50/250/250 images.

### Table: LoveDA mIoU (%) vs. labelled images (mean ± SD over 5 folds×draws)

| labelled images   |   area (km²) | Linear probe   | Class-balanced probe   | Cluster-then-label (K=50)   | Linear − cluster                  | Balanced − linear                 |
|:------------------|-------------:|:---------------|:-----------------------|:----------------------------|:----------------------------------|:----------------------------------|
| 1                 |         0.09 | 11.0 ± 4.0     | 12.4 ± 3.5             | 15.1 ± 6.6                  | -4.1 (d_z=-0.8, p_Holm=0.53)      | +1.4 (d_z=1.2, p_Holm=0.22)       |
| 2                 |         0.19 | 19.7 ± 5.8     | 20.8 ± 5.9             | 22.0 ± 8.5                  | -2.3 (d_z=-0.5, p_Holm=0.97)      | +1.1 (d_z=1.7, p_Holm=0.13)       |
| 5                 |         0.47 | 26.9 ± 4.2     | 28.4 ± 4.4             | 25.9 ± 3.7                  | +1.0 (d_z=0.5, p_Holm=0.97)       | +1.5 (d_z=1.1, p_Holm=0.22)       |
| 10                |         0.94 | 32.9 ± 2.9     | 34.1 ± 3.3             | 31.1 ± 1.2                  | +1.7 (d_z=0.5, p_Holm=0.97)       | +1.3 (d_z=1.9, p_Holm=0.099)      |
| 25                |         2.36 | 37.6 ± 1.2     | 38.4 ± 1.2             | 32.2 ± 1.8                  | +5.4 (d_z=2.0, p_Holm=0.053)      | +0.8 (d_z=1.6, p_Holm=0.13)       |
| 50                |         4.72 | 39.0 ± 0.9     | 39.9 ± 1.2             | 33.0 ± 0.9                  | +6.0 (d_z=4.8, p_Holm=0.0026)*    | +0.8 (d_z=0.9, p_Holm=0.22)       |
| 100               |         9.44 | 41.9 ± 0.7     | 42.6 ± 0.9             | 33.1 ± 0.6                  | +8.8 (d_z=13.1, p_Holm=7.2e-05)*  | +0.7 (d_z=2.4, p_Holm=0.044)*     |
| 250               |        23.59 | 44.1 ± 1.1     | 43.6 ± 1.0             | 32.8 ± 0.5                  | +11.4 (d_z=7.7, p_Holm=0.00048)*  | -0.6 (d_z=-0.8, p_Holm=0.22)      |
| all               |       238.01 | 45.9 ± 0.1     | 45.0 ± 0.1             | 32.3 ± 1.2                  | +13.6 (d_z=10.9, p_Holm=0.00013)* | -0.9 (d_z=-18.3, p_Holm=1.9e-05)* |

Zero labels (k-means, K = #classes, Hungarian-matched on test — optimistic): 28.6 ± 2.2. Patch-oracle ceiling (every 14×14 patch assigned its majority class): 84.0. Paired differences: same labelled images; Holm correction across the 9 budgets; * p_Holm<0.05.
- LoveDA: probe exceeds the 0-label baseline from n=10 images; full-pool mIoU 45.9 (55% of the patch ceiling); 80/90/95% of full-pool mIoU reached at n=25/100/250 images.

### Table: DeepGlobe sparse point annotation (linear probe, points spread over the whole pool)

|   random point labels | mIoU       |   ≈ dense images with equal mIoU |
|----------------------:|:-----------|---------------------------------:|
|                   100 | 39.1 ± 3.7 |                               10 |
|                   300 | 47.0 ± 1.0 |                               25 |
|                  1000 | 52.4 ± 0.9 |                               50 |
|                  3000 | 55.1 ± 1.5 |                              100 |
|                 10000 | 59.1 ± 0.8 |                              100 |
|                 30000 | 62.2 ± 0.9 |                              250 |
- DeepGlobe: 100 points 39.1 vs 5 full images 27.6 (diff +11.4, paired p=2.1e-05, n=15); a full image holds 1369 patch labels.
- DeepGlobe: 300 points 47.0 vs 10 full images 35.6 (diff +11.4, paired p=2.8e-05, n=15); a full image holds 1369 patch labels.
- DeepGlobe: 1000 points 52.4 vs 50 full images 52.5 (diff -0.1, paired p=0.89, n=15); a full image holds 1369 patch labels.

### Table: LoveDA sparse point annotation (linear probe, points spread over the whole pool)

|   random point labels | mIoU       |   ≈ dense images with equal mIoU |
|----------------------:|:-----------|---------------------------------:|
|                   100 | 29.9 ± 2.6 |                                5 |
|                   300 | 34.6 ± 1.7 |                               10 |
|                  1000 | 36.1 ± 1.5 |                               25 |
|                  3000 | 36.4 ± 0.4 |                               25 |
|                 10000 | 40.7 ± 0.4 |                              100 |
|                 30000 | 43.8 ± 0.4 |                              250 |
- LoveDA: 100 points 29.9 vs 5 full images 26.9 (diff +3.0, paired p=0.14, n=5); a full image holds 1369 patch labels.
- LoveDA: 300 points 34.6 vs 10 full images 32.9 (diff +1.8, paired p=0.38, n=5); a full image holds 1369 patch labels.
- LoveDA: 1000 points 36.1 vs 50 full images 39.0 (diff -2.9, paired p=0.048, n=5); a full image holds 1369 patch labels.

### Table: DeepGlobe L2-strength sensitivity, linear probe mIoU (%)

|               | 5          | 50         | all        |
|:--------------|:-----------|:-----------|:-----------|
| λ=1e-4        | 26.3 ± 5.8 | 50.5 ± 2.8 | 63.9 ± 0.9 |
| λ=1e-3 (main) | 27.6 ± 6.7 | 52.5 ± 3.0 | 64.1 ± 0.9 |
| λ=1e-2        | 28.7 ± 6.8 | 53.0 ± 3.3 | 62.3 ± 0.7 |
| λ=1e-1        | 28.3 ± 6.5 | 50.5 ± 3.6 | 57.2 ± 0.7 |

### Table: DeepGlobe cluster-then-label K sensitivity (same draws), mIoU (%)

|              | 5          | 50         | all        |
|:-------------|:-----------|:-----------|:-----------|
| K=25         | 28.5 ± 3.6 | 32.7 ± 1.8 | 32.5 ± 2.2 |
| K=50 (main)  | 28.5 ± 4.3 | 34.6 ± 2.5 | 34.4 ± 2.5 |
| K=100        | 29.0 ± 3.3 | 34.7 ± 1.6 | 36.7 ± 1.3 |
| K=200        | 29.3 ± 1.8 | 38.1 ± 2.6 | 38.9 ± 2.3 |
| linear probe | 29.9 ± 3.8 | 53.7 ± 1.5 | 64.1 ± 0.9 |

### Table: LoveDA L2-strength sensitivity, linear probe mIoU (%)

|               | 5          | 50         | all        |
|:--------------|:-----------|:-----------|:-----------|
| λ=1e-4        | 24.0 ± 4.4 | 36.8 ± 0.8 | 45.7 ± 0.1 |
| λ=1e-3 (main) | 26.9 ± 4.2 | 39.0 ± 0.9 | 45.9 ± 0.1 |
| λ=1e-2        | 29.8 ± 3.7 | 40.6 ± 0.9 | 45.3 ± 0.1 |
| λ=1e-1        | 30.2 ± 3.5 | 40.1 ± 1.0 | 43.4 ± 0.1 |

### Table: LoveDA cluster-then-label K sensitivity (same draws), mIoU (%)

|              | 5          | 50         | all        |
|:-------------|:-----------|:-----------|:-----------|
| K=25         | 27.5 ± 4.0 | 32.0 ± 1.0 | 32.0 ± 1.4 |
| K=50 (main)  | 25.9 ± 3.7 | 33.0 ± 0.9 | 32.3 ± 1.2 |
| K=100        | 28.4 ± 3.8 | 33.1 ± 0.7 | 34.8 ± 0.5 |
| K=200        | 27.4 ± 2.6 | 33.8 ± 0.9 | 36.1 ± 0.8 |
| linear probe | 26.9 ± 4.2 | 39.0 ± 0.9 | 45.9 ± 0.1 |

### Table: LoveDA rural/urban transfer, linear probe mIoU (%) (5 draws)

|                                 | test rural   | test urban   |
|:--------------------------------|:-------------|:-------------|
| Rural train, n=10               | 29.9 ± 4.3   | 29.0 ± 5.1   |
| Rural train, n=100              | 37.3 ± 0.7   | 41.7 ± 1.2   |
| Rural train, n=all (1366)       | 41.1 ± 0.0   | 47.3 ± 0.0   |
| Urban train, n=10               | 20.0 ± 6.2   | 28.6 ± 7.9   |
| Urban train, n=100              | 31.7 ± 1.6   | 41.1 ± 1.1   |
| Urban train, n=all (1156)       | 36.7 ± 0.0   | 45.8 ± 0.0   |
| Rural+Urban train, n=10         | 29.3 ± 3.3   | 35.2 ± 3.0   |
| Rural+Urban train, n=100        | 37.5 ± 1.3   | 43.4 ± 1.1   |
| Rural+Urban train, n=all (2522) | 40.8 ± 0.1   | 48.2 ± 0.1   |
- n=10, test rural: rural-trained − urban-trained = +9.8 (paired over draws, p=0.035).
- n=10, test urban: rural-trained − urban-trained = +0.4 (paired over draws, p=0.92).
- n=100, test rural: rural-trained − urban-trained = +5.6 (paired over draws, p=0.0019).
- n=100, test urban: rural-trained − urban-trained = +0.6 (paired over draws, p=0.52).

### Table: LoveDA per-class IoU (%), in- vs cross-domain training, n=100 images

|             |   test rural: in-domain |   test rural: cross-domain |   test rural: Δ |   test urban: in-domain |   test urban: cross-domain |   test urban: Δ |
|:------------|------------------------:|---------------------------:|----------------:|------------------------:|---------------------------:|----------------:|
| Background  |                    41   |                       37.4 |            -3.6 |                    35.9 |                       32.7 |            -3.2 |
| Building    |                    49.4 |                       38.8 |           -10.6 |                    50.3 |                       49.1 |            -1.2 |
| Road        |                    35.1 |                       36.8 |             1.7 |                    52.3 |                       46.8 |            -5.5 |
| Water       |                    56.7 |                       49.6 |            -7.1 |                    58.7 |                       55.3 |            -3.4 |
| Barren      |                     5.3 |                        6.8 |             1.5 |                    13   |                       26.9 |            13.8 |
| Forest      |                    20.3 |                       14.6 |            -5.6 |                    34.4 |                       35.2 |             0.8 |
| Agriculture |                    53.5 |                       38.1 |           -15.3 |                    43.1 |                       45.7 |             2.6 |

### Table: DeepGlobe per-class IoU (%)

|             |   0 labels |   5 img |   100 pts |   50 img |   all img |   patch ceiling |
|:------------|-----------:|--------:|----------:|---------:|----------:|----------------:|
| Urban       |       41.4 |    39.3 |      50   |     66.2 |      71.6 |            88.7 |
| Agriculture |       36.9 |    65.9 |      71.9 |     78.3 |      83.6 |            96.3 |
| Rangeland   |        8.7 |     8.4 |       8.5 |     15.3 |      27   |            82.8 |
| Forest      |       15.5 |    21.8 |      47   |     57.4 |      73.9 |            95.6 |
| Water       |        9.4 |    24.8 |      37.6 |     60.6 |      70.3 |            85.1 |
| Barren      |       11.6 |     5.7 |      19.4 |     37.3 |      58.1 |            92.7 |

### Table: LoveDA per-class IoU (%)

|             |   0 labels |   5 img |   100 pts |   50 img |   all img |   patch ceiling |
|:------------|-----------:|--------:|----------:|---------:|----------:|----------------:|
| Background  |       21.2 |    31.5 |      32.1 |     40.3 |      46.7 |            86.3 |
| Building    |       46.3 |    31.2 |      37.4 |     47.6 |      54.6 |            77   |
| Road        |       30.3 |    31.4 |      30.6 |     44.3 |      49.4 |            72.6 |
| Water       |       26.8 |    35.4 |      37.9 |     52.6 |      64.6 |            90.3 |
| Barren      |        4.4 |     1.2 |       6.2 |     10.7 |      16.2 |            86.2 |
| Forest      |       26.7 |    19.5 |      18.6 |     28   |      32.9 |            81.2 |
| Agriculture |       44.6 |    38   |      46.2 |     49.7 |      56.8 |            94.1 |

### Table: DeepGlobe backbone comparison, identical protocol (256 patches/img), mIoU (%)

|                        | 0 labels   | linear n=5   | linear n=10   | linear n=50   | linear n=all   | cluster K=50, all   |
|:-----------------------|:-----------|:-------------|:--------------|:--------------|:---------------|:--------------------|
| DINOv2 ViT-S/14        | 17.3 ± 1.4 | 26.7 ± 4.0   | 36.2 ± 4.1    | 51.3 ± 2.6    | 61.8 ± 1.3     | 35.2 ± 1.3          |
| DINOv2 ViT-B/14        | 20.7 ± 0.2 | 29.8 ± 3.7   | 38.8 ± 4.1    | 52.2 ± 2.3    | 63.9 ± 0.9     | 34.0 ± 1.4          |
| DINOv2 ViT-L/14        | 18.1 ± 1.2 | 28.1 ± 4.3   | 36.8 ± 4.2    | 52.3 ± 0.7    | 63.3 ± 1.5     | 31.2 ± 1.3          |
| ResNet-50 (IN-1k sup.) | 21.3 ± 2.6 | 24.9 ± 3.3   | 31.1 ± 5.1    | 46.5 ± 0.8    | 57.3 ± 1.5     | 35.1 ± 1.5          |
- DeepGlobe / DINOv2 ViT-S/14: linear > cluster-then-label (Holm p<0.05) at budgets ['25', '50', '100', '250', 'all'].
- DeepGlobe / DINOv2 ViT-B/14: linear > cluster-then-label (Holm p<0.05) at budgets ['25', '50', '100', '250', 'all'].
- DeepGlobe / DINOv2 ViT-L/14: linear > cluster-then-label (Holm p<0.05) at budgets ['25', '50', '100', '250', 'all'].
- DeepGlobe / ResNet-50 (IN-1k sup.): linear > cluster-then-label (Holm p<0.05) at budgets ['50', '100', '250', 'all'].

### Table: LoveDA backbone comparison, identical protocol (256 patches/img), mIoU (%)

|                        | 0 labels   | linear n=5   | linear n=10   | linear n=50   | linear n=all   | cluster K=50, all   |
|:-----------------------|:-----------|:-------------|:--------------|:--------------|:---------------|:--------------------|
| DINOv2 ViT-S/14        | 23.5 ± 2.6 | 25.3 ± 5.5   | 26.9 ± 3.2    | 35.7 ± 1.0    | 43.7 ± 0.0     | 31.5 ± 0.7          |
| DINOv2 ViT-B/14        | 27.3 ± 2.3 | 27.5 ± 4.8   | 30.8 ± 2.3    | 37.4 ± 1.2    | 45.9 ± 0.1     | 33.1 ± 0.9          |
| DINOv2 ViT-L/14        | 25.4 ± 1.3 | 28.6 ± 5.1   | 31.9 ± 2.0    | 38.6 ± 1.0    | 46.1 ± 0.0     | 31.4 ± 1.1          |
| ResNet-50 (IN-1k sup.) | 21.2 ± 3.8 | 21.2 ± 4.5   | 23.8 ± 3.6    | 31.1 ± 2.1    | 41.2 ± 0.0     | 30.2 ± 1.6          |
- LoveDA / DINOv2 ViT-S/14: linear > cluster-then-label (Holm p<0.05) at budgets ['250', 'all'].
- LoveDA / DINOv2 ViT-B/14: linear > cluster-then-label (Holm p<0.05) at budgets ['100', '250', 'all'].
- LoveDA / DINOv2 ViT-L/14: linear > cluster-then-label (Holm p<0.05) at budgets ['50', '100', '250', 'all'].
- LoveDA / ResNet-50 (IN-1k sup.): linear > cluster-then-label (Holm p<0.05) at budgets [].

### Table: end-to-end DeepLabV3-ResNet50 fine-tuning vs frozen DINOv2-B probe, same labelled images (1500 iterations), mIoU (%)

|                    |   runs | finetune   | linear     | balanced   |
|:-------------------|-------:|:-----------|:-----------|:-----------|
| ('DeepGlobe', 10)  |      3 | 41.4 ± 2.5 | 40.9 ± 2.7 | 41.8 ± 2.1 |
| ('DeepGlobe', 100) |      3 | 59.7 ± 4.7 | 58.2 ± 1.1 | 56.3 ± 1.1 |
| ('LoveDA', 10)     |      3 | 27.4 ± 3.7 | 31.8 ± 1.6 | 33.1 ± 2.0 |
| ('LoveDA', 100)    |      3 | 42.3 ± 0.9 | 42.0 ± 0.9 | 42.8 ± 1.2 |
- DeepGlobe, n=10: probe − fine-tune = -0.5 (paired p=0.86, 3 pairs).
- DeepGlobe, n=100: probe − fine-tune = -1.5 (paired p=0.54, 3 pairs).
- LoveDA, n=10: probe − fine-tune = +4.4 (paired p=0.099, 3 pairs).
- LoveDA, n=100: probe − fine-tune = -0.2 (paired p=0.78, 3 pairs).
