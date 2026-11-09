"""Builds the RSASE submission (manuscript + highlights) as .docx from the final results.
Every number in the text is taken from outputs/final_tables.md, which analyze_final.py
computes from final.jsonl, backbone_*.jsonl and finetune.jsonl.
Run with the base conda python (python-docx): python manuscript/build_manuscript.py
"""
import re
from pathlib import Path
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "outputs" / "figures_final"
OUTDIR = ROOT / "manuscript"
FONT = "Times New Roman"

# ════════════════════════════════════════════════════════════════
# Front matter
# ════════════════════════════════════════════════════════════════
TITLE = ("Label wisely, not heavily: annotation budgets for land-cover mapping "
         "with frozen self-supervised vision features")
AUTHORS = [("Ziem Patrick Wellu", "a", True), ("Solomon Mensah", "a", False)]
AFFIL = {"a": "Department of Computer Science, University of Ghana, Legon, Accra, Ghana"}
CORR = ("Corresponding author: Ziem Patrick Wellu, Department of Computer Science, University of "
        "Ghana, Legon, Accra, Ghana. E-mail: ziemwellu@gmail.com")
EMAILS = ("E-mail addresses: ziemwellu@gmail.com (Z.P. Wellu), smensah03@ug.edu.gh (S. Mensah). "
          "ORCID: Z.P. Wellu 0009-0004-5808-2675; S. Mensah [TO CONFIRM — candidate 0000-0001-5629-2661].")

HIGHLIGHTS = [
    "A frozen DINOv2 linear probe reaches ~90% of full-pool mIoU with 100 labelled images",
    "100 random point labels beat 5 fully annotated images by 11 mIoU on DeepGlobe",
    "Cluster-then-label saturates at 32–35% mIoU regardless of the label budget",
    "Findings hold across four backbones; ViT-L gives no gain over ViT-B",
    "Rural-trained probes transfer to urban scenes; urban-trained probes lose 6–10 points",
]

ABSTRACT = (
    "Pixel-level reference labels are the dominant cost of land-cover mapping, especially for "
    "small agencies. Self-supervised vision foundation models promise to reduce this "
    "cost, but practitioners lack evidence on how many labels are still needed, how to collect "
    "them, and whether the answer depends on the model. We report a controlled label-budget study "
    "with frozen DINOv2 patch features on two very-high-resolution benchmarks, DeepGlobe (rural) "
    "and LoveDA (urban and rural). We varied the number of fully annotated images from one to the "
    "full pool, compared dense annotation with sparse single-pixel point labels, and tested "
    "linear probing, cluster-then-label and zero-label clustering against a patch-resolution "
    "ceiling, using cross-validation, repeated label draws and Holm-corrected "
    "paired tests. With 100 labelled images the linear probe reached 57.2% mIoU on DeepGlobe and "
    "41.9% on LoveDA, about 90% of its full-pool accuracy (64.1% and 45.9%), whereas "
    "cluster-then-label saturated at 32–35%. On DeepGlobe, spreading labels as random points was "
    "far more efficient than annotating whole images: 100 points outperformed five annotated "
    "images by 11.4 points, and 1000 points matched 50 images. On LoveDA, whose images cover 16 "
    "times less ground, the advantage was small and not significant. Conclusions held across three "
    "DINOv2 sizes and an ImageNet-supervised ResNet-50; self-supervised features led by "
    "up to 8 points, and ViT-L gave no gain over ViT-B. With 10 or 100 labelled images the frozen "
    "probe did not differ significantly from a fine-tuned DeepLabV3 network. Rural-trained probes "
    "transferred to urban scenes, whereas urban-trained probes lost 5.6–9.8 points on rural "
    "scenes. We derive annotation guidance.")

KEYWORDS = ("Land-cover mapping; Label efficiency; Self-supervised learning; Foundation models; "
            "Point annotation; Domain shift; Semantic segmentation")

# ════════════════════════════════════════════════════════════════
# Body. Markup: ("h1"|"h2"|"p"|"table"|"fig"|"eq"|"bullets", ...). *italic* inline.
# ════════════════════════════════════════════════════════════════
B = []
h1 = lambda t: B.append(("h1", t))
h2 = lambda t: B.append(("h2", t))
p = lambda t: B.append(("p", t))

h1("1. Introduction")
p("Land-cover maps underpin land-use planning, food-security monitoring, ecosystem accounting and "
  "disaster response, and their quality is ultimately limited by the reference data used to train "
  "and assess them (Foody, 2002; Stehman and Foody, 2019). Global products such as Dynamic World "
  "and ESA WorldCover now provide 10 m maps (Brown et al., 2022; Zanaga et al., 2022), but many "
  "applications — urban growth analysis, smallholder agriculture, informal settlement mapping — "
  "require very-high-resolution (VHR) imagery and locally defined legends. Deep semantic "
  "segmentation networks are the standard tool for such maps (Zhu et al., 2017; Ma et al., 2019), "
  "yet they are usually trained on thousands of images annotated pixel by pixel. Producing such "
  "annotation is slow, requires trained interpreters, and is often the single largest cost of a "
  "mapping project. For national agencies, universities and non-governmental organisations in "
  "low-resource settings, this cost frequently decides whether a mapping project happens at all.")
p("Self-supervised learning offers a way out. Models such as DINO and DINOv2 learn general-purpose "
  "visual features from unlabelled images (Caron et al., 2021; Oquab et al., 2024), and a growing "
  "family of remote-sensing foundation models is pretrained on satellite archives (Manas et al., "
  "2021; Ayush et al., 2021; Cong et al., 2022; Reed et al., 2023; Bastani et al., 2023; Jakubik "
  "et al., 2023; Wang et al., 2022). When such features are kept frozen, a lightweight classifier "
  "fitted on top can be trained in seconds on a laptop, a strategy that has proved effective for "
  "global prediction tasks from satellite imagery (Rolf et al., 2021) and is the standard protocol "
  "for evaluating representations (Kolesnikov et al., 2019). Dense patch features of vision "
  "transformers are also semantically meaningful enough to support unsupervised segmentation by "
  "clustering (Ji et al., 2019; Cho et al., 2021; Hamilton et al., 2022; Amir et al., 2023).")
p("For a practitioner planning an annotation campaign, however, benchmark results answer the wrong "
  "question. Benchmarks typically report accuracy for a fixed training set or a few label "
  "fractions (Lacoste et al., 2023), on a single split and without uncertainty estimates — a "
  "practice known to produce unreliable conclusions (Dietterich, 1998; Oliver et al., 2018; "
  "Bouthillier et al., 2021). Conversely, the remote-sensing literature has long studied how "
  "training-set size and sampling design affect land-cover classifiers (Foody et al., 2006; "
  "Ramezan et al., 2021), but for classifiers trained from scratch on hand-crafted or spectral "
  "features; how these questions play out when a single pretrained representation serves every "
  "budget is largely untested. A practitioner instead needs to know: how accuracy grows with the "
  "number of labelled images; whether a fixed effort is better spent on complete masks of a few "
  "images or on scattered labels across many; whether unsupervised clustering can substitute for "
  "labels; whether the answer depends on the chosen model; whether a frozen model leaves much "
  "accuracy on the table compared with full fine-tuning; and whether labels collected in one "
  "setting (for example urban areas) serve another (rural areas).")
p("This paper answers these questions with a controlled label-budget study. We use frozen DINOv2 "
  "patch features and two public VHR benchmarks that differ in scale and setting — DeepGlobe "
  "(Demir et al., 2018), with large rural scenes, and LoveDA (Wang et al., 2021), with explicit "
  "urban and rural domains. Our contributions are:")
B.append(("bullets", [
    "Label-efficiency curves over nine budgets (one image to the full pool) on both datasets, "
    "using five-fold cross-validation and repeated label draws, exact pixel-level scoring and a "
    "patch-resolution ceiling that separates resolution loss from feature and classifier "
    "limitations.",
    "A direct comparison of dense image annotation with sparse single-pixel point annotation, "
    "showing that spreading labels can be an order of magnitude more efficient per label.",
    "A comparison of four classifiers that span supervised and unsupervised use of the features, "
    "including the commonly proposed cluster-then-label strategy, with sensitivity analyses of "
    "their hyperparameters.",
    "A robustness check across four frozen backbones — three DINOv2 sizes and an "
    "ImageNet-supervised ResNet-50 — and an end-to-end DeepLabV3 fine-tuning baseline trained on "
    "the identical labelled images.",
    "An urban–rural transfer analysis with per-class attribution, and practical, evidence-based "
    "guidance for annotation campaigns. All code, splits and result files are released.",
]))
p("We frame the study around five research questions. RQ1: How does mapping accuracy scale with "
  "the number of labelled images, and how close does it come to the attainable ceiling? RQ2: Is it "
  "better to annotate a few images completely or to spread point labels across many images? RQ3: "
  "Can clustering-based use of the features replace supervised fitting when labels are scarce? "
  "RQ4: Are the answers specific to one backbone, and does a frozen model lose accuracy relative "
  "to end-to-end fine-tuning? RQ5: How well do labels from urban scenes transfer to rural scenes, "
  "and vice versa?")

h1("2. Related work")
h2("2.1. Self-supervised and foundation models for Earth observation")
p("Self-supervised learning trains feature extractors without labels, typically through "
  "self-distillation or masked image modelling. DINO showed that vision transformers trained by "
  "self-distillation produce patch features with emergent semantic structure (Caron et al., "
  "2021); DINOv2 scaled this recipe to a curated set of 142 million web images and produced "
  "features that transfer across tasks without fine-tuning (Oquab et al., 2024). Adding a small "
  "number of register tokens removes artefacts in the patch-feature maps of large vision "
  "transformers (Darcet et al., 2024), which matters when patch features are used directly for "
  "dense prediction, as here. In remote sensing, self-supervised pretraining has exploited "
  "seasonal and geographic structure (Manas et al., 2021; Ayush et al., 2021), multispectral and "
  "temporal inputs (Cong et al., 2022), scale (Reed et al., 2023) and large curated archives "
  "(Bastani et al., 2023; Jakubik et al., 2023); see Wang et al. (2022) for a review. Whether "
  "in-domain pretraining beats general-purpose natural-image pretraining depends on the task and "
  "the input modality (Neumann et al., 2019; Wang et al., 2023). For RGB VHR imagery — the input "
  "domain of DeepGlobe and LoveDA — general-purpose models remain strong, freely available "
  "baselines: a DINOv2-style self-supervised vision transformer trained on VHR RGB satellite "
  "imagery, for example, underpins recent meter-scale canopy-height maps (Tolan et al., 2024). "
  "This motivates their use here.")
h2("2.2. Label-efficient semantic segmentation")
p("Approaches that reduce annotation for segmentation include weak supervision with points, "
  "scribbles or boxes (Bearman et al., 2016; Hua et al., 2022), active learning that selects the "
  "most informative samples (Settles, 2009; Ren et al., 2021), and unsupervised segmentation "
  "that groups pixels without any labels (Ji et al., 2019; Cho et al., 2021; Hamilton et al., "
  "2022; Ziegler and Asano, 2022). A common pragmatic hybrid is cluster-then-label: features are "
  "clustered without labels and a handful of labels are used to name the clusters. Point "
  "supervision is of special interest in remote sensing because sample-based reference data are "
  "already the norm for map accuracy assessment (Olofsson et al., 2014; Stehman and Foody, 2019): "
  "interpreters routinely label randomly placed points rather than complete images. In classical "
  "land-cover classification, accuracy depends both on the number of training samples and on how "
  "they are distributed (Foody et al., 2006; Ramezan et al., 2021), and spatially clustered "
  "samples carry less independent information than their number suggests (Karasiak et al., "
  "2022). Hua et al. "
  "(2022) showed that sparse annotations can train remote-sensing segmentation networks; we ask "
  "the complementary budget question — at a matched number of labels, is spreading them better "
  "than concentrating them — for frozen foundation-model features.")
h2("2.3. Linear probing, fine-tuning and domain shift")
p("Fitting a linear classifier on frozen features (linear probing) is cheap and stable, while "
  "end-to-end fine-tuning adapts all weights but can distort pretrained features and overfit when "
  "data are scarce (Kumar et al., 2022). Remote-sensing models face strong domain shift between "
  "regions, sensors and settings (Tuia et al., 2016); LoveDA was built specifically to study the "
  "shift between urban and rural scenes (Wang et al., 2021). We therefore pair the label-budget "
  "analysis with a fine-tuning baseline and an urban–rural transfer experiment.")

h1("3. Data")
p("We use two public VHR land-cover benchmarks. Both provide RGB imagery with dense pixel-level "
  "reference masks; they differ in ground sampling distance (GSD), image footprint, landscape and "
  "legend. Table 1 summarises both datasets together with the quantities derived from them in this "
  "study: the evaluation splits, the ground area covered by one image, the ground footprint of one "
  "feature patch (Section 4.1) and the patch-oracle ceiling (Section 4.2).")
h2("3.1. DeepGlobe Land Cover")
p("The DeepGlobe 2018 Land Cover Classification dataset (Demir et al., 2018) contains 803 "
  "labelled RGB images of 2448 × 2448 pixels at 0.5 m GSD, covering about 1.5 km² each, acquired "
  "over rural areas in Thailand, Indonesia and India. Masks contain six land-cover classes (urban, "
  "agriculture, rangeland, forest, water, barren) and an *unknown* class, which we ignore during "
  "training and evaluation as in the original challenge. Labelled pixels are dominated by "
  "agriculture (57.8%), followed by forest (11.2%), urban (10.8%), rangeland (8.5%), barren (8.5%) "
  "and water (3.3%). Because reference masks were released only for the 803 training images, we "
  "evaluate with five-fold cross-validation over these images (Section 4.5).")
h2("3.2. LoveDA")
p("LoveDA (Wang et al., 2021) contains 1024 × 1024 pixel RGB images at 0.3 m GSD (about 0.09 km² "
  "each) from Nanjing, Changzhou and Wuhan, China, split into urban and rural domains. Masks "
  "contain seven classes (background, building, road, water, barren, forest, agriculture) and a "
  "no-data value, which we ignore. We use the official training split (2522 images: 1366 rural, "
  "1156 urban) as the annotation pool. Because test labels are held on an evaluation server, we "
  "use the official validation split (1669 images: 992 rural, 677 urban) as the held-out test "
  "set; it is never used for model selection or tuning. Class shares differ between the splits "
  "(e.g. agriculture 20.2% of training vs 28.6% of validation pixels; forest 16.1% vs 7.4%), "
  "which adds a realistic distribution shift.")
B.append(("table", "Table 1. Datasets and the derived quantities used in this study.",
          ["", "DeepGlobe", "LoveDA"],
          [["Images used (pool / test)", "803 (5-fold CV: 642–643 / 160–161)", "2522 train / 1669 val"],
           ["Domains", "Rural (TH, ID, IN)", "Rural 1366+992; urban 1156+677"],
           ["Image size; GSD", "2448 × 2448 px; 0.5 m", "1024 × 1024 px; 0.3 m"],
           ["Effective GSD at 518 × 518 px", "2.36 m", "0.59 m"],
           ["Ground area per image", "1.50 km²", "0.094 km²"],
           ["Classes (ignored label)", "6 (unknown)", "7 (no-data)"],
           ["Patch footprint after resampling", "33.1 m × 33.1 m", "8.3 m × 8.3 m"],
           ["Patch-oracle ceiling (mIoU, %)", "90.2 ± 0.7", "84.0"]],
          [5.2, 5.4, 5.4]))

h1("4. Methods")
p("Fig. 1 summarises the pipeline. Every image is passed once through a frozen backbone to obtain "
  "a grid of patch features. All classifiers operate on these features, one label per patch, and "
  "predictions are scored at pixel level against the reference masks.")
h2("4.1. Frozen patch features")
p("Images are resized with bilinear interpolation to 518 × 518 pixels, normalised with ImageNet "
  "statistics and passed through DINOv2 ViT-B/14 with four register tokens (Oquab et al., 2024; "
  "Darcet et al., 2024), with all weights frozen. The normalised final-layer patch tokens form a "
  "37 × 37 grid of 768-dimensional features per image (1369 patches), which we L2-normalise and "
  "store in half precision. Resampling reduces the effective GSD to 2.36 m for DeepGlobe (a "
  "4.7-fold reduction) and 0.59 m for LoveDA, so one 14 × 14 pixel patch corresponds to 33.1 m on "
  "the ground for DeepGlobe and 8.3 m for LoveDA (Table 1). We chose a single input size so that "
  "every image yields the same feature grid; the patch-oracle ceiling (Section 4.2) quantifies "
  "what this costs. Feature extraction took about 0.27 s "
  "per image on a 6 GB laptop GPU (NVIDIA GTX 1060 Max-Q).")
h2("4.2. Patch labels and exact pixel-level scoring")
p("Reference masks are resized to 518 × 518 with nearest-neighbour interpolation. For each patch we "
  "compute the histogram of reference classes over its 196 pixels. A training patch receives the "
  "majority class if that class covers at least 50% of the patch, and is otherwise excluded. For "
  "evaluation, the class predicted for a patch is assigned to all its pixels, and the confusion "
  "matrix is accumulated exactly from the histograms (row = prediction, column = reference). This "
  "is identical to scoring a nearest-neighbour-upsampled patch map against the full 518 × 518 "
  "reference mask, but is computed without materialising pixel maps. We report per-class "
  "intersection-over-union (IoU), its mean over classes (mIoU) and overall accuracy, excluding "
  "ignored pixels.")
p("Because each patch carries a single label, no patch-level classifier can reach 100% mIoU. We "
  "therefore report a *patch-oracle* ceiling that assigns every test patch its majority reference "
  "class. The ceiling isolates the accuracy lost to the 14-pixel patch resolution; the gap between "
  "the ceiling and a classifier is due to the features and the classifier.")
h2("4.3. Classifiers")
p("We compare four ways of turning frozen features into a map.")
p("*Linear probe.* Multinomial logistic regression on standardised features with an L2 penalty "
  "λ‖W‖² (λ = 10⁻³, fixed a priori), fitted by full-batch L-BFGS (Liu and Nocedal, 1989) with a "
  "strong-Wolfe line search and at most 200 iterations, implemented in PyTorch (Paszke et al., "
  "2019) on the GPU.")
p("*Class-balanced probe.* The same model with class weights inversely proportional to class "
  "frequency in the labelled set, w_c = N / (C·N_c), to counter class imbalance.")
p("*Cluster-then-label.* Mini-batch k-means (Sculley, 2010; Pedregosa et al., 2011) with K = 50 "
  "clusters is fitted once per pool and draw on 300,000 unlabelled patches sampled from the whole "
  "annotation pool (batch 4096, three initialisations, 100 iterations). Each cluster is named by "
  "the majority label of the labelled patches assigned to it; clusters without labelled patches "
  "inherit the label of the nearest labelled cluster centre. This uses the unlabelled pool, which "
  "the probes do not.")
p("*Zero-label clustering.* k-means with K equal to the number of classes, with clusters mapped to "
  "classes by the Hungarian algorithm (Kuhn, 1955) to maximise agreement with the test reference. "
  "This follows the unsupervised-segmentation literature (Ji et al., 2019; Cho et al., 2021), but "
  "because the matching consults test labels it is an optimistic upper bound on what zero labels "
  "can achieve.")
h2("4.4. Annotation regimes and budgets")
p("*Dense annotation* labels n complete images. We use n ∈ {1, 2, 5, 10, 25, 50, 100, 250, all}. "
  "All patches of the labelled images are used, subject to the purity rule, unless their number "
  "exceeds a memory cap of 500,000 patches; in that case a fixed random subset of patches is "
  "used per image. The cap binds only at the full-pool budget (400 of 1369 patches per image for "
  "DeepGlobe; 198 for LoveDA). Draws are nested: for each draw a random permutation of the pool "
  "is fixed and budget n uses its first n images, so smaller labelled sets are subsets of larger "
  "ones.")
p("*Sparse point annotation* labels P single pixels, P ∈ {100, 300, 1000, 3000, 10,000, 30,000}, "
  "at uniformly random positions in uniformly random images of the pool. The class of each "
  "point is the reference class of a uniformly random pixel within the selected patch, and its "
  "feature is the feature of that patch. Points therefore simulate an interpreter clicking random "
  "locations across the whole archive. Because a point takes the class of one random pixel rather "
  "than the patch majority, point labels are noisier than dense patch labels in mixed patches; "
  "this favours dense annotation and makes the comparison conservative for points. To compare "
  "regimes at equal numbers of labels: after the purity rule, one fully annotated image supplies "
  "on average 1366 patch labels on DeepGlobe and 1308 on LoveDA, so five DeepGlobe images supply "
  "about 6800 labels, 68 times more than 100 points.")
p("We also report the labelled ground area for dense budgets alongside the results, because one "
  "image means 1.50 km² in DeepGlobe but 0.094 km² in LoveDA.")
h2("4.5. Evaluation protocol")
p("Table 2 summarises all experiments: for each it lists the annotation pool and test set, the "
  "label budgets, the methods compared and the number of paired replicates. "
  "*DeepGlobe.* The 803 images are randomly partitioned (fixed seed) into five folds of 160–161 "
  "images. For each fold, the remaining 642–643 images form the annotation pool; three "
  "independent label draws per fold give 15 replicates per budget. Results are pooled over folds. "
  "*LoveDA.* The pool is the full training split and the test set is the validation split, "
  "reported for rural, urban and combined test images; five label draws give five replicates. "
  "*Urban–rural transfer.* The LoveDA pool is restricted to rural (1366) or urban (1156) training "
  "images and tested on both domains, with five draws. "
  "*Sensitivity.* As robustness checks — never for model selection — we refit the linear probe with "
  "λ ∈ {10⁻⁴, 10⁻², 10⁻¹} at n ∈ {5, 50, all} and cluster-then-label with K ∈ {25, 100, 200} "
  "(DeepGlobe: first draw of each fold; LoveDA: all draws).")
h2("4.6. Backbone comparison")
p("To test whether the conclusions are specific to one model, we repeat the core experiment "
  "(linear probe, cluster-then-label with K = 50 and zero-label clustering) with four frozen "
  "backbones: DINOv2 ViT-S/14, ViT-B/14 and ViT-L/14, all with registers (about 21, 86 and 300 "
  "million parameters; Oquab et al., 2024), and an ImageNet-1k supervised ResNet-50 (He et al., "
  "2016; torchvision weights). For ResNet-50 we use the output of the third residual stage "
  "(stride 16, 1024 channels) at 592 × 592 input, which yields the same 37 × 37 grid and therefore "
  "the same ground footprint per patch as the vision transformers. To keep the computation "
  "feasible on one GPU, all four backbones share a reduced protocol: 256 fixed random patch "
  "positions per training image (identical across backbones), one draw per DeepGlobe fold and "
  "three LoveDA draws; test images are scored at all patches. Under this protocol ViT-B differs "
  "from the main protocol by at most 0.2 mIoU at the full pool (DeepGlobe 63.9 vs 64.1; LoveDA "
  "45.9 vs 45.9).")
h2("4.7. End-to-end fine-tuning baseline")
p("As a reference for what full network training achieves with the same labels, we fine-tune "
  "DeepLabV3 with a ResNet-50 backbone (Chen et al., 2017), initialised from COCO-pretrained "
  "weights (Lin et al., 2014), on exactly the images of the matched probe draws (n = 10 and 100; "
  "DeepGlobe folds 0–2 and LoveDA draws 0–2). The recipe was fixed a priori: output stride 16, "
  "518 × 518 inputs, batch size 4, 1500 iterations, AdamW (Loshchilov and Hutter, 2019) with "
  "learning rates 10⁻⁴ (backbone) and 10⁻³ (heads), weight decay 10⁻⁴, polynomial decay (power "
  "0.9), random flips and 90° rotations, cross-entropy with a 0.4-weighted auxiliary loss. The "
  "final iterate is evaluated (no validation set and no checkpoint selection, matching the "
  "probes). Predictions are dense at 518 × 518 and are therefore not limited by the patch "
  "ceiling. Each run took about 30 min on the same GPU. The baseline differs from the probe in "
  "both the network (a COCO-pretrained ResNet-50 rather than DINOv2) and the training regime, and "
  "it predicts at pixel rather than patch resolution. It therefore answers a practical question — "
  "does a standard fine-tuned segmentation network outperform the frozen probe at these budgets? "
  "— rather than isolating the effect of fine-tuning itself.")
h2("4.8. Statistical analysis")
p("We report means and standard deviations across replicates. Comparisons between methods use "
  "the same labelled images (same fold and draw) and are tested with paired t-tests; we report "
  "the mean difference, the paired effect size d_z (mean difference divided by the standard "
  "deviation of the differences), and p-values adjusted with the Holm (1979) procedure across the "
  "nine budgets of each comparison. Replicates that share a test fold are not fully independent "
  "(Dietterich, 1998; Bouthillier et al., 2021). We therefore repeated the main DeepGlobe tests at "
  "fold level, averaging the three draws within each fold and testing the five fold means, and we "
  "report in how many folds an effect had the same sign. Even so, p-values should be read as "
  "indicative; we emphasise effect sizes and consistency across folds, datasets and backbones.")
h2("4.9. Implementation and reproducibility")
p("All experiments ran on a single laptop (NVIDIA GTX 1060 Max-Q, 6 GB; 16 GB RAM) with Python "
  "3.10, PyTorch 2.1 and scikit-learn 1.4. After feature extraction, the complete main experiment "
  "— 1418 fitted models and 2684 evaluation records — ran in 77 minutes. The fold-level tests are "
  "computed from the same result files without refitting. Random seeds, fold "
  "assignments, labelled-image orders and per-run confusion matrices are saved and released with "
  "the code.")

h1("5. Results")
h2("5.1. Label efficiency (RQ1, RQ3)")
p("Table 3 and Fig. 2 report mIoU as a function of the number of fully annotated images. On "
  "DeepGlobe, the linear probe rose from 14.5% with one image to 57.2% with 100 images and 64.1% "
  "with the full pool of 642–643 images, which is 71% of the patch-oracle ceiling of 90.2%. It "
  "reached 80% of its full-pool accuracy with 50 images (about 8% of the pool) and 90% with 250. "
  "On LoveDA, accuracy rose from 11.0% to 41.9% with 100 images and 45.9% with all 2522 (55% of "
  "the 84.0% ceiling); 80% of full-pool accuracy required only 25 images (1% of the pool) and 90% "
  "required 100. Variability across draws was large for the smallest budgets (standard "
  "deviations of 4–7 points up to ten images) and fell below 1.5 points from 100 images onward, "
  "so single-split results at small budgets should be treated with caution. Absolute values are "
  "not comparable with published benchmark results, which are obtained at native resolution, on "
  "other splits and with the full training sets; our interest is in differences between budgets "
  "and methods under one fixed protocol.")
p("The optimistic zero-label clustering baseline reached 20.6% on DeepGlobe and 28.6% on LoveDA. "
  "The linear probe exceeded it from five labelled images on DeepGlobe and from ten on LoveDA. "
  "Cluster-then-label was competitive with the probe up to five images — none of the differences "
  "was significant — but then saturated: on DeepGlobe it stayed between 32.1% and 34.6% from 25 "
  "images to the full pool, and on LoveDA between 32.2% and 33.1%. The probe's advantage grew "
  "monotonically, from +6.4 points at ten images (p_Holm < 0.001) to +29.5 points at the full "
  "pool on DeepGlobe (d_z = 22.8), and from +6.0 points at 50 images (p_Holm = 0.003) to +13.6 "
  "points at the full pool on LoveDA. The fold-level analysis on DeepGlobe confirmed this: the "
  "probe beat cluster-then-label in all five folds at every budget from ten images onward "
  "(p_Holm ≤ 0.038).")
p("Class balancing helped only when labels were scarce. On DeepGlobe the balanced probe gained "
  "0.9–1.9 points for one to ten images (all p_Holm ≤ 0.002) but lost 1.3–2.6 points from 100 "
  "images onward (all p_Holm < 0.001); at fold level, both the gains and the losses had the same "
  "sign in all five folds (p_Holm ≤ 0.024). On LoveDA it gained 0.7–1.5 points up to 100 images, "
  "significant only at 100 images, and lost 0.9 points at the full pool. The crossover lay "
  "between 25 and 250 images.")
p("The patch ceilings show that resampling to 518 pixels costs about 10 mIoU points on DeepGlobe "
  "and 16 on LoveDA, whereas the gap between the ceiling and the full-pool probe (26 and 38 "
  "points) is larger. Most of the remaining error is therefore attributable to the separability "
  "of the frozen features and the linear classifier rather than to resolution.")
h2("5.2. Sparse points versus dense images (RQ2)")
p("Spreading labels was far more efficient than concentrating them on DeepGlobe (Table 4, Fig. 3). "
  "With 100 random point labels the probe reached 39.1%, 11.4 points more than five fully "
  "annotated images (27.6%; paired p < 0.001) even though the five images supplied about 68 times "
  "more labelled patches. Likewise, 300 points beat ten images by 11.4 points (47.0% vs 35.6%; p "
  "< 0.001). Both advantages held at fold level (p = 0.001 and 0.004; positive in all five "
  "folds). 1000 points matched 50 images (52.4% vs 52.5%; p = 0.89), which contain about 68,000 "
  "patch labels, and 30,000 points (62.2%) matched 250 images (61.9%; about 342,000 patch "
  "labels). Point-based results were also more stable: the standard deviation at 300 points was "
  "1.0, compared with 7.0 for ten images.")
p("On LoveDA the effect was weaker. 100 and 300 points exceeded five and ten images by 3.0 and 1.8 "
  "points, but neither difference was significant (p = 0.14 and 0.38), and 1000 points fell 2.9 "
  "points short of 50 images (p = 0.048). Measured per label (Fig. 3), points nevertheless "
  "dominated dense annotation on both datasets: on LoveDA, 30,000 points (43.8%) approached the "
  "accuracy of 250 images (44.1%), which carry about eleven times as many patch labels.")
h2("5.3. Per-class behaviour")
p("Per-class IoU (Table 5, Fig. 4) reveals which classes drive the budget curves. On DeepGlobe, "
  "agriculture — the majority class — was learnt fastest (65.9% IoU from five images), whereas "
  "rangeland remained poor at every budget (27.0% with the full pool) despite a patch ceiling of "
  "82.8%, so its difficulty lies in the features, not in resolution. Points helped spatially "
  "clustered classes most: forest rose from 21.8% with five images to 47.0% with 100 points, and "
  "barren from 5.7% to 19.4%. On LoveDA, barren (16.2%) and forest (32.9%) remained the weakest "
  "classes even with the full pool, again far below their ceilings (86.2% and 81.2%). Road "
  "needed about 50 images before the probe clearly exceeded zero-label clustering (44.3% vs "
  "30.3%), and building only exceeded it clearly with the full pool (54.6% vs 46.3%), "
  "because clustering alone already separates buildings well.")
h2("5.4. Sensitivity to hyperparameters")
p("Table 6 shows that the regularisation strength mattered most at the extremes of the budget "
  "range. With five images, stronger regularisation helped (LoveDA: 26.9% at λ = 10⁻³ vs 30.2% at "
  "λ = 10⁻¹); with the full pool it hurt (DeepGlobe: 64.1% vs 57.2%). The a priori value λ = 10⁻³ "
  "was the best value at the full pool and within 3.3 points of the best at five images, "
  "so a budget-aware choice of λ could add a few points at small budgets without changing any of "
  "the comparisons. For cluster-then-label, more clusters raised the plateau (DeepGlobe full pool: "
  "32.5% at K = 25 to 38.9% at K = 200; LoveDA: 32.0% to 36.1%), but even K = 200 remained 25 "
  "(DeepGlobe) and 10 (LoveDA) points below the linear probe, so the saturation is not an "
  "artefact of the choice K = 50.")
h2("5.5. Is the picture specific to one model? (RQ4)")
p("The same picture emerged for all four backbones (Table 7, Fig. 5). Every backbone produced the "
  "same shape of label-efficiency curve, and on DeepGlobe the linear probe beat cluster-then-label "
  "significantly for every backbone (from 25 images for the three DINOv2 models and from 50 for "
  "ResNet-50). On LoveDA the difference was significant for all DINOv2 models (from 50–250 "
  "images); for ResNet-50 it was not significant after Holm correction with only three draws, "
  "although the mean gap at the full pool was 11.0 points (41.2% vs 30.2%).")
p("Self-supervised features consistently outperformed supervised ImageNet features. With the full "
  "pool, the DINOv2 models reached 61.8–63.9% on DeepGlobe and 43.7–46.1% on LoveDA, against "
  "57.3% and 41.2% for ResNet-50; with ten images the gap was 5.1–7.7 points on DeepGlobe and 3.1–8.1 points on LoveDA. Model "
  "size mattered little beyond ViT-B: ViT-L, with about 3.5 times as many parameters, stayed "
  "within 2 points of ViT-B at every budget (full pool: DeepGlobe 63.3% vs 63.9%; LoveDA 46.1% vs "
  "45.9%), whereas ViT-S trailed ViT-B by 2.1–2.2 points with the full pool and by up to 3.9 "
  "points with ten images. Zero-label clustering did not separate the backbones in the same way (DeepGlobe: "
  "17.3–21.3%, with ResNet-50 highest), which underlines that clustering quality and linear "
  "separability are different properties of a representation.")
h2("5.6. Frozen probe versus end-to-end fine-tuning (RQ4)")
p("End-to-end fine-tuning of DeepLabV3 on the same labelled images did not outperform the frozen "
  "probe (Table 8). On DeepGlobe, fine-tuning reached 41.4% with ten images and 59.7% with 100, "
  "against 40.9% and 58.2% for the probe (differences of 0.5 and 1.5 points; p = 0.86 and 0.54). "
  "On LoveDA, fine-tuning reached 27.4% and 42.3% against 31.8% and 42.0% (p = 0.10 and 0.78). "
  "Fine-tuning was also less stable at 100 DeepGlobe images (standard deviation 4.7 vs 1.1) and "
  "on LoveDA with ten images, even though its predictions are not limited by the patch ceiling. It needed about 30 minutes of GPU training per run, whereas the "
  "probe is fitted in seconds on cached features. With three pairs per comparison these tests "
  "cannot establish equivalence, and a tuned recipe could do better; but at these budgets a frozen "
  "probe is a strong, cheap baseline that a fine-tuned network must beat to justify its cost.")
h2("5.7. Urban–rural transfer (RQ5)")
p("Transfer between LoveDA domains was strongly asymmetric (Table 9, Fig. 6). Training on rural "
  "images and testing on urban images caused no detectable loss: rural-trained probes matched urban-trained "
  "probes on urban test images with ten images (29.0% vs 28.6%; p = 0.92) and 100 images (41.7% "
  "vs 41.1%; p = 0.52), and with the full rural pool even exceeded the full urban pool (47.3% vs "
  "45.8%), although the rural pool is also larger (1366 vs 1156 images). In the opposite "
  "direction, urban-trained probes lost 9.8 points on rural test images with ten images (20.0% vs "
  "29.9%; p = 0.035) and 5.6 points with 100 images (31.7% vs 37.3%; p = 0.002).")
p("Per-class differences locate the loss (Table 10). On rural test images, urban training cost "
  "15.3 IoU points for agriculture, 10.6 for building, 7.1 for water and 5.6 for forest — classes "
  "whose appearance or prevalence differs most between settings. On urban test images, rural "
  "training cost 5.5 points for road but gained 13.8 for barren. Training on both domains gave "
  "the best urban result (48.2% with the full pool) and matched rural-only training on rural "
  "images (40.8% vs 41.1%).")

h1("6. Discussion")
h2("6.1. Practical guidance for annotation campaigns")
p("Taken together, the results support seven recommendations for projects that map land cover from "
  "RGB VHR imagery with limited annotation budgets. These are drawn from two datasets and should be "
  "validated locally.")
B.append(("bullets", [
    "Start from frozen self-supervised features and a linear probe. On both datasets it "
    "performed on par with a standard fine-tuned segmentation network at 10 and 100 labelled "
    "images (no significant difference), at a small fraction of the compute, and runs on a laptop.",
    "Spread labels rather than concentrating them. Where images are large and spatially "
    "autocorrelated (DeepGlobe), a few hundred random point labels were worth as much as tens of "
    "fully annotated images, and a point design pays off whenever about 20 points take less time "
    "than one complete image (Section 6.3). Point labelling also matches the sample-based design already used "
    "for accuracy assessment (Olofsson et al., 2014), although training and assessment samples "
    "must be kept separate.",
    "Plan for roughly 50–100 annotated images to obtain 80–90% of the accuracy attainable with the "
    "full pools studied here; 1000–3000 well-spread points gave about 80% on both datasets. Beyond "
    "that, returns diminish quickly.",
    "Do not rely on cluster-then-label beyond the first few labels: its accuracy saturates "
    "because the clusters are fixed before any label is seen.",
    "Use class balancing only for very small budgets (up to about 25 images) and increase "
    "regularisation when labels are very few.",
    "A ViT-B-sized model suffices; the larger ViT-L added cost without accuracy, while the small "
    "ViT-S lost two to four points.",
    "When labels from only one setting are affordable, prefer diverse (here, rural) scenes, which "
    "transferred to urban scenes with no detectable loss; labels from urban scenes alone transferred poorly "
    "to rural landscapes.",
]))
h2("6.2. Why does cluster-then-label saturate?")
p("Cluster-then-label commits to a partition of feature space before any label is seen. Once each "
  "cluster has received its majority label, additional labels cannot move a cluster boundary, so "
  "accuracy is capped by how well unsupervised clusters align with land-cover classes. The linear "
  "probe, by contrast, places its decision boundaries wherever the labels require, including "
  "through the middle of visually coherent clusters — for example separating rangeland from "
  "agriculture, which look alike in RGB. Increasing K raises the cap only slowly (Table 6). The "
  "observation that zero-label clustering ranked the backbones differently from the probe "
  "(Table 7) points to the same conclusion: unsupervised cluster structure and class "
  "separability are distinct, and clustering-based evaluation of foundation models should not be "
  "taken as a proxy for their usefulness with labels.")
h2("6.3. Why are points so efficient?")
p("Neighbouring patches of the same image are highly redundant: they share illumination, season, "
  "sensor geometry and landscape context, and land cover is spatially autocorrelated. A fully "
  "annotated image therefore adds many labels but little new information, while randomly placed "
  "points sample the diversity of the whole archive. The effect should scale with image "
  "footprint, and our results are consistent with this: the advantage was large on DeepGlobe, "
  "where one image covers 1.5 km², and small on LoveDA, where each image covers only 0.09 km² and "
  "is itself a small sample. The same spatial dependence is known to inflate accuracy when "
  "training and test samples lie close together (Karasiak et al., 2022); here it shows up as "
  "wasted annotation effort. The finding mirrors arguments from active learning that "
  "informative, diverse samples matter more than sample count (Settles, 2009; Ren et al., 2021), "
  "and suggests that even simple random spreading captures much of that benefit.")
p("The equal-accuracy pairs also give a break-even annotation cost. On DeepGlobe, 1000 points "
  "matched 50 images, so point labelling is the cheaper design whenever an interpreter can label "
  "about 20 random points in less time than it takes to annotate one 2448 × 2448 pixel image "
  "completely; at the largest budget (30,000 points against 250 images) the break-even is about "
  "120 points per image on both datasets. We did not measure annotation times, and points spread "
  "over many images carry an overhead for loading and orienting in each image, but these "
  "thresholds give planners a simple test to apply with their own timing data.")
h2("6.4. Why is urban–rural transfer asymmetric?")
p("Rural LoveDA scenes contain the full range of classes — villages with buildings and roads, "
  "water bodies, forest and farmland — whereas urban scenes contain little agriculture or forest "
  "and their buildings and water bodies look different (large regular structures and channelised "
  "water). A model trained on rural scenes has therefore seen every class, while a model trained "
  "on urban scenes must extrapolate for the classes that dominate rural landscapes; the per-class "
  "losses in Table 10 match this explanation. For planning, this means that class coverage of the "
  "training sample matters more than matching its setting to the target, and that labelling a "
  "diverse sample is a safer default than labelling only the most accessible (often urban) areas. "
  "This explanation is consistent with the per-class results but was not tested directly, for "
  "example by matching class composition between the two training pools.")
h2("6.5. Relation to previous work")
p("Several of our findings agree with earlier work and extend it to dense land-cover mapping with "
  "foundation models. That a linear model on frozen, generic features can rival task-specific "
  "training echoes the MOSAIKS results for image-level prediction from satellite imagery (Rolf et "
  "al., 2021). The absence of a significant gain from fine-tuning at small budgets is consistent "
  "with the finding that fine-tuning can distort good pretrained features when data are scarce "
  "(Kumar et al., 2022), although our baseline also differs in architecture (Section 4.7). "
  "Classical studies showed that land-cover accuracy depends strongly on the size and design of "
  "the training sample (Foody et al., 2006; Ramezan et al., 2021); with a frozen foundation model, "
  "80% of full-pool accuracy was reached with 25–50 annotated images, and the design of the sample "
  "(points versus images) mattered as much as its size. Finally, the mismatch between clustering "
  "quality and linear separability across backbones (Section 5.5) cautions against ranking "
  "foundation models for land-cover use by unsupervised segmentation scores alone, as is common "
  "in that literature (Ji et al., 2019; Hamilton et al., 2022).")
h2("6.6. Limitations")
p("Several limitations bound these conclusions. (i) Scope: both datasets are RGB VHR imagery from "
  "Asia; we did not test multispectral data, other continents — including the West African "
  "landscapes that motivate this work — or remote-sensing-specific foundation models. (ii) "
  "Resolution: images were resampled to 518 pixels (effective GSD 2.36 m for DeepGlobe and 0.59 m "
  "for LoveDA), so DeepGlobe patches cover 33 m on the ground and evaluation is at 518 × 518 "
  "rather than native resolution; narrow features such as roads and small buildings suffer most. The patch ceiling "
  "quantifies this cost; tiled inference at native resolution would raise it. (iii) Test data: "
  "LoveDA's validation split served as the test set because test labels are not public; it was "
  "never used for tuning. (iv) Simulated points assume perfectly accurate annotators and do not "
  "model the different time costs of a point and a mask; we compare regimes per label and per "
  "image, not per hour of effort. (v) Full-pool budgets used a random subset of patches per image "
  "because of the memory cap, which may slightly underestimate full-pool accuracy. (vi) The "
  "zero-label baseline is optimistic because of test-set matching. (vii) The fine-tuning baseline "
  "used a single untuned recipe, a different backbone from the probe and three pairs per "
  "comparison, so it cannot establish equivalence. (viii) Replicates that share test "
  "folds are not independent. (ix) The classifiers predict one label per patch without spatial "
  "context or post-processing, which would likely improve all methods.")
h2("6.7. Future work")
p("Three extensions follow directly. First, a field-validated study in Ghana, combining point "
  "labels from photo-interpretation with ground visits, would test whether the guidance transfers "
  "to West African agricultural and peri-urban landscapes. Second, comparing natural-image and "
  "remote-sensing foundation models under the same budget protocol would show whether in-domain "
  "pretraining changes the required budget. Third, selecting points actively, rather than at "
  "random, and measuring real annotation times would turn the per-label comparison into a "
  "per-hour cost model.")

h1("7. Conclusions")
p("We measured how many labels land-cover mapping needs when it is built on frozen self-supervised "
  "features, using repeated, cross-validated label-budget experiments on DeepGlobe and LoveDA. A "
  "linear probe on DINOv2 features reached 57.2% and 41.9% mIoU with 100 labelled images and "
  "64.1% and 45.9% with the full pools, did not differ significantly from a fine-tuned DeepLabV3 "
  "network at 10 and 100 images, and behaved consistently across four backbones, with no benefit "
  "from the largest model. Cluster-then-label saturated at 32–35% mIoU and is not a substitute "
  "for supervised fitting. The way labels are collected mattered as much as their number: on DeepGlobe, a hundred "
  "random points outperformed five fully annotated images by 11.4 points, and point labelling "
  "pays off whenever about 20 points cost less effort than one complete image. Labels from rural "
  "scenes transferred to urban scenes, but not the reverse. For mapping projects with small budgets, the "
  "message is to label wisely rather than heavily: use a frozen foundation model, spread labels "
  "across many diverse scenes, and validate locally.")

BACK = [
    ("CRediT authorship contribution statement",
     "Ziem Patrick Wellu: Conceptualization, Methodology, Software, Validation, Formal analysis, "
     "Investigation, Data curation, Visualization, Writing – original draft. Solomon Mensah: "
     "Conceptualization, Supervision, Methodology, Writing – review & editing. "
     "[AUTHORS TO CONFIRM ROLES BEFORE SUBMISSION]"),
    ("Declaration of competing interest",
     "The authors declare that they have no known competing financial interests or personal "
     "relationships that could have appeared to influence the work reported in this paper."),
    ("Funding",
     "This research did not receive any specific grant from funding agencies in the public, "
     "commercial, or not-for-profit sectors."),
    ("Data availability",
     "DeepGlobe Land Cover (Demir et al., 2018) and LoveDA (Wang et al., 2021) are publicly "
     "available from their providers. The code, fold assignments, labelled-image orders, random "
     "seeds and all per-run results and confusion matrices are available at [REPOSITORY URL — to "
     "be added before submission]."),
    ("Declaration of generative AI and AI-assisted technologies in the manuscript preparation process",
     "During the preparation of this work the authors used Claude (Anthropic) in order to assist "
     "with writing and debugging the experiment and analysis code and with drafting and editing "
     "the manuscript text. After using this tool, the authors reviewed and edited the content as "
     "needed and take full responsibility for the content of the published article."),
    ("Acknowledgements",
     "[Optional — e.g. thanks to the Department of Computer Science, University of Ghana.]"),
]

REFS = [
    "Amir, S., Gandelsman, Y., Bagon, S., Dekel, T., 2023. On the effectiveness of ViT features as local semantic descriptors, in: Computer Vision – ECCV 2022 Workshops, Lecture Notes in Computer Science, vol. 13804. Springer, Cham, pp. 39–55. https://doi.org/10.1007/978-3-031-25069-9_3",
    "Ayush, K., Uzkent, B., Meng, C., Tanmay, K., Burke, M., Lobell, D., Ermon, S., 2021. Geography-aware self-supervised learning, in: Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV), pp. 10161–10170. https://doi.org/10.1109/ICCV48922.2021.01002",
    "Bastani, F., Wolters, P., Gupta, R., Ferdinando, J., Kembhavi, A., 2023. SatlasPretrain: A large-scale dataset for remote sensing image understanding, in: Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV), pp. 16726–16736. https://doi.org/10.1109/ICCV51070.2023.01538",
    "Bearman, A., Russakovsky, O., Ferrari, V., Fei-Fei, L., 2016. What's the point: Semantic segmentation with point supervision, in: Computer Vision – ECCV 2016, Lecture Notes in Computer Science, vol. 9911. Springer, Cham, pp. 549–565. https://doi.org/10.1007/978-3-319-46478-7_34",
    "Bouthillier, X., Delaunay, P., Bronzi, M., Trofimov, A., Nichyporuk, B., Szeto, J., Mohammadi Sepahvand, N., Raff, E., Madan, K., Voleti, V., Kahou, S.E., Michalski, V., Arbel, T., Pal, C., Varoquaux, G., Vincent, P., 2021. Accounting for variance in machine learning benchmarks. Proceedings of Machine Learning and Systems 3, 747–769.",
    "Brown, C.F., Brumby, S.P., Guzder-Williams, B., Birch, T., Hyde, S.B., Mazzariello, J., Czerwinski, W., Pasquarella, V.J., Haertel, R., Ilyushchenko, S., Schwehr, K., Weisse, M., Stolle, F., Hanson, C., Guinan, O., Moore, R., Tait, A.M., 2022. Dynamic World, Near real-time global 10 m land use land cover mapping. Scientific Data 9, 251. https://doi.org/10.1038/s41597-022-01307-4",
    "Caron, M., Touvron, H., Misra, I., Jégou, H., Mairal, J., Bojanowski, P., Joulin, A., 2021. Emerging properties in self-supervised vision transformers, in: Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV), pp. 9630–9640. https://doi.org/10.1109/ICCV48922.2021.00951",
    "Chen, L.-C., Papandreou, G., Schroff, F., Adam, H., 2017. Rethinking atrous convolution for semantic image segmentation. arXiv preprint arXiv:1706.05587.",
    "Cho, J.H., Mall, U., Bala, K., Hariharan, B., 2021. PiCIE: Unsupervised semantic segmentation using invariance and equivariance in clustering, in: Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), pp. 16789–16799. https://doi.org/10.1109/CVPR46437.2021.01652",
    "Cong, Y., Khanna, S., Meng, C., Liu, P., Rozi, E., He, Y., Burke, M., Lobell, D.B., Ermon, S., 2022. SatMAE: Pre-training transformers for temporal and multi-spectral satellite imagery. Advances in Neural Information Processing Systems 35, 197–211.",
    "Darcet, T., Oquab, M., Mairal, J., Bojanowski, P., 2024. Vision transformers need registers, in: International Conference on Learning Representations (ICLR).",
    "Demir, I., Koperski, K., Lindenbaum, D., Pang, G., Huang, J., Basu, S., Hughes, F., Tuia, D., Raskar, R., 2018. DeepGlobe 2018: A challenge to parse the Earth through satellite images, in: Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition Workshops (CVPRW), pp. 172–181. https://doi.org/10.1109/CVPRW.2018.00031",
    "Dietterich, T.G., 1998. Approximate statistical tests for comparing supervised classification learning algorithms. Neural Computation 10, 1895–1923. https://doi.org/10.1162/089976698300017197",
    "Foody, G.M., Mathur, A., Sanchez-Hernandez, C., Boyd, D.S., 2006. Training set size requirements for the classification of a specific class. Remote Sensing of Environment 104, 1–14. https://doi.org/10.1016/j.rse.2006.03.004",
    "Karasiak, N., Dejoux, J.-F., Monteil, C., Sheeren, D., 2022. Spatial dependence between training and test sets: another pitfall of classification accuracy assessment in remote sensing. Machine Learning 111, 2715–2740. https://doi.org/10.1007/s10994-021-05972-1",
    "Ramezan, C.A., Warner, T.A., Maxwell, A.E., Price, B.S., 2021. Effects of training set size on supervised machine-learning land-cover classification of large-area high-resolution remotely sensed data. Remote Sensing 13, 368. https://doi.org/10.3390/rs13030368",
    "Tolan, J., Yang, H., Nosarzewski, B., Couairon, G., Vo, H.V., Brandt, J., Spore, J., Majumdar, S., Haziza, D., Vamaraju, J., et al., 2024. Very high resolution canopy height maps from RGB imagery using self-supervised vision transformer and convolutional decoder trained on aerial lidar. Remote Sensing of Environment 300, 113888. https://doi.org/10.1016/j.rse.2023.113888",
    "Foody, G.M., 2002. Status of land cover classification accuracy assessment. Remote Sensing of Environment 80, 185–201. https://doi.org/10.1016/S0034-4257(01)00295-4",
    "Hamilton, M., Zhang, Z., Hariharan, B., Snavely, N., Freeman, W.T., 2022. Unsupervised semantic segmentation by distilling feature correspondences, in: International Conference on Learning Representations (ICLR).",
    "He, K., Zhang, X., Ren, S., Sun, J., 2016. Deep residual learning for image recognition, in: Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR), pp. 770–778. https://doi.org/10.1109/CVPR.2016.90",
    "Holm, S., 1979. A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics 6, 65–70.",
    "Hua, Y., Marcos, D., Mou, L., Zhu, X.X., Tuia, D., 2022. Semantic segmentation of remote sensing images with sparse annotations. IEEE Geoscience and Remote Sensing Letters 19, 1–5. https://doi.org/10.1109/LGRS.2021.3051053",
    "Jakubik, J., Roy, S., Phillips, C.E., Fraccaro, P., Godwin, D., Zadrozny, B., Szwarcman, D., Gomes, C., Nyirjesy, G., Edwards, B., et al., 2023. Foundation models for generalist geospatial artificial intelligence. arXiv preprint arXiv:2310.18660.",
    "Ji, X., Vedaldi, A., Henriques, J., 2019. Invariant information clustering for unsupervised image classification and segmentation, in: Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV), pp. 9864–9873. https://doi.org/10.1109/ICCV.2019.00996",
    "Kolesnikov, A., Zhai, X., Beyer, L., 2019. Revisiting self-supervised visual representation learning, in: Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), pp. 1920–1929. https://doi.org/10.1109/CVPR.2019.00202",
    "Kuhn, H.W., 1955. The Hungarian method for the assignment problem. Naval Research Logistics Quarterly 2, 83–97. https://doi.org/10.1002/nav.3800020109",
    "Kumar, A., Raghunathan, A., Jones, R., Ma, T., Liang, P., 2022. Fine-tuning can distort pretrained features and underperform out-of-distribution, in: International Conference on Learning Representations (ICLR).",
    "Lacoste, A., Lehmann, N., Rodriguez, P., Sherwin, E.D., Kerner, H., Lütjens, B., Irvin, J., Dao, D., Alemohammad, H., Drouin, A., et al., 2023. GEO-Bench: Toward foundation models for Earth monitoring. Advances in Neural Information Processing Systems 36 (Datasets and Benchmarks Track).",
    "Lin, T.-Y., Maire, M., Belongie, S., Hays, J., Perona, P., Ramanan, D., Dollár, P., Zitnick, C.L., 2014. Microsoft COCO: Common objects in context, in: Computer Vision – ECCV 2014, Lecture Notes in Computer Science, vol. 8693. Springer, Cham, pp. 740–755. https://doi.org/10.1007/978-3-319-10602-1_48",
    "Liu, D.C., Nocedal, J., 1989. On the limited memory BFGS method for large scale optimization. Mathematical Programming 45, 503–528. https://doi.org/10.1007/BF01589116",
    "Loshchilov, I., Hutter, F., 2019. Decoupled weight decay regularization, in: International Conference on Learning Representations (ICLR).",
    "Ma, L., Liu, Y., Zhang, X., Ye, Y., Yin, G., Johnson, B.A., 2019. Deep learning in remote sensing applications: A meta-analysis and review. ISPRS Journal of Photogrammetry and Remote Sensing 152, 166–177. https://doi.org/10.1016/j.isprsjprs.2019.04.015",
    "Mañas, O., Lacoste, A., Giró-i-Nieto, X., Vazquez, D., Rodríguez, P., 2021. Seasonal Contrast: Unsupervised pre-training from uncurated remote sensing data, in: Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV), pp. 9394–9403. https://doi.org/10.1109/ICCV48922.2021.00928",
    "Neumann, M., Pinto, A.S., Zhai, X., Houlsby, N., 2019. In-domain representation learning for remote sensing. arXiv preprint arXiv:1911.06721.",
    "Oliver, A., Odena, A., Raffel, C.A., Cubuk, E.D., Goodfellow, I., 2018. Realistic evaluation of deep semi-supervised learning algorithms. Advances in Neural Information Processing Systems 31.",
    "Olofsson, P., Foody, G.M., Herold, M., Stehman, S.V., Woodcock, C.E., Wulder, M.A., 2014. Good practices for estimating area and assessing accuracy of land change. Remote Sensing of Environment 148, 42–57. https://doi.org/10.1016/j.rse.2014.02.015",
    "Oquab, M., Darcet, T., Moutakanni, T., Vo, H.V., Szafraniec, M., Khalidov, V., Fernandez, P., Haziza, D., Massa, F., El-Nouby, A., et al., 2024. DINOv2: Learning robust visual features without supervision. Transactions on Machine Learning Research.",
    "Paszke, A., Gross, S., Massa, F., Lerer, A., Bradbury, J., Chanan, G., Killeen, T., Lin, Z., Gimelshein, N., Antiga, L., et al., 2019. PyTorch: An imperative style, high-performance deep learning library. Advances in Neural Information Processing Systems 32.",
    "Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., et al., 2011. Scikit-learn: Machine learning in Python. Journal of Machine Learning Research 12, 2825–2830.",
    "Reed, C.J., Gupta, R., Li, S., Brockman, S., Funk, C., Clipp, B., Keutzer, K., Candido, S., Uyttendaele, M., Darrell, T., 2023. Scale-MAE: A scale-aware masked autoencoder for multiscale geospatial representation learning, in: Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV), pp. 4065–4076. https://doi.org/10.1109/ICCV51070.2023.00378",
    "Ren, P., Xiao, Y., Chang, X., Huang, P.-Y., Li, Z., Gupta, B.B., Chen, X., Wang, X., 2021. A survey of deep active learning. ACM Computing Surveys 54, 1–40. https://doi.org/10.1145/3472291",
    "Rolf, E., Proctor, J., Carleton, T., Bolliger, I., Shankar, V., Ishihara, M., Recht, B., Hsiang, S., 2021. A generalizable and accessible approach to machine learning with global satellite imagery. Nature Communications 12, 4392. https://doi.org/10.1038/s41467-021-24638-z",
    "Sculley, D., 2010. Web-scale k-means clustering, in: Proceedings of the 19th International Conference on World Wide Web, pp. 1177–1178. https://doi.org/10.1145/1772690.1772862",
    "Settles, B., 2009. Active learning literature survey. Computer Sciences Technical Report 1648, University of Wisconsin–Madison.",
    "Stehman, S.V., Foody, G.M., 2019. Key issues in rigorous accuracy assessment of land cover products. Remote Sensing of Environment 231, 111199. https://doi.org/10.1016/j.rse.2019.05.018",
    "Tuia, D., Persello, C., Bruzzone, L., 2016. Domain adaptation for the classification of remote sensing data: An overview of recent advances. IEEE Geoscience and Remote Sensing Magazine 4, 41–57. https://doi.org/10.1109/MGRS.2016.2548504",
    "Wang, D., Zhang, J., Du, B., Xia, G.-S., Tao, D., 2023. An empirical study of remote sensing pretraining. IEEE Transactions on Geoscience and Remote Sensing 61, 1–20. https://doi.org/10.1109/TGRS.2022.3176603",
    "Wang, J., Zheng, Z., Ma, A., Lu, X., Zhong, Y., 2021. LoveDA: A remote sensing land-cover dataset for domain adaptive semantic segmentation, in: Proceedings of the Neural Information Processing Systems Track on Datasets and Benchmarks, vol. 1.",
    "Wang, Y., Albrecht, C.M., Braham, N.A.A., Mou, L., Zhu, X.X., 2022. Self-supervised learning in remote sensing: A review. IEEE Geoscience and Remote Sensing Magazine 10, 213–247. https://doi.org/10.1109/MGRS.2022.3198244",
    "Zanaga, D., Van De Kerchove, R., Daems, D., De Keersmaecker, W., Brockmann, C., Kirches, G., Wevers, J., Cartus, O., Santoro, M., Fritz, S., et al., 2022. ESA WorldCover 10 m 2021 v200. Zenodo. https://doi.org/10.5281/zenodo.7254221",
    "Zhu, X.X., Tuia, D., Mou, L., Xia, G.-S., Zhang, L., Xu, F., Fraundorfer, F., 2017. Deep learning in remote sensing: A comprehensive review and list of resources. IEEE Geoscience and Remote Sensing Magazine 5, 8–36. https://doi.org/10.1109/MGRS.2017.2762307",
    "Ziegler, A., Asano, Y.M., 2022. Self-supervised learning of object parts for semantic segmentation, in: Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR), pp. 14482–14491. https://doi.org/10.1109/CVPR52688.2022.01410",
]

# ── Tables 2–10 (values copied from outputs/final_tables.md) ─────
BUD = ["1", "2", "5", "10", "25", "50", "100", "250", "all"]
T2 = ("Table 2. Experimental design. Replicates are paired across methods (same labelled images).",
      ["Experiment", "Pool → test", "Budgets", "Methods", "Replicates"],
      [["Main, DeepGlobe", "5-fold CV (642–643 → 160–161)", "9 image budgets; 6 point budgets",
        "Probe, balanced probe, cluster-then-label, 0-label, ceiling", "5 folds × 3 draws"],
       ["Main, LoveDA", "Train 2522 → Val 1669", "9 image budgets; 6 point budgets", "As above", "5 draws"],
       ["Urban–rural transfer", "Rural 1366 or urban 1156 → Val rural/urban", "9 image budgets",
        "Probe, balanced probe, cluster-then-label", "5 draws"],
       ["Sensitivity", "As main", "n = 5, 50, all", "λ ∈ {10⁻⁴…10⁻¹}; K ∈ {25…200}", "As main*"],
       ["Backbones", "As main", "9 image budgets", "Probe, cluster-then-label, 0-label; 4 backbones",
        "DG 5 × 1; LD 3"],
       ["Fine-tuning", "As main", "n = 10, 100", "DeepLabV3-ResNet50 vs matched probe", "DG 3; LD 3"]],
      [3.0, 3.6, 2.8, 4.4, 2.2],
      "*K sensitivity on DeepGlobe uses the first draw of each fold (5 replicates).")

T3 = ("Table 3. mIoU (%) of the classifiers on frozen DINOv2 ViT-B/14 features versus the number of "
      "fully annotated images (mean ± SD; DeepGlobe 15 replicates, LoveDA 5). Δ: paired mean "
      "difference with Holm-adjusted p-value (* p_Holm < 0.05).",
      ["Images", "Area km²", "Linear probe", "Balanced", "Cluster K=50", "Δ probe − cluster", "Δ balanced − probe"],
      [["DeepGlobe", "", "", "", "", "", ""],
       ["1", "1.5", "14.5 ± 4.3", "15.4 ± 4.5", "16.2 ± 6.0", "−1.7", "+0.9*"],
       ["2", "3.0", "19.2 ± 5.8", "20.5 ± 5.7", "19.8 ± 6.3", "−0.7", "+1.3*"],
       ["5", "7.5", "27.6 ± 6.7", "29.1 ± 6.6", "25.3 ± 6.0", "+2.4", "+1.4*"],
       ["10", "15.0", "35.6 ± 7.0", "37.5 ± 6.1", "29.2 ± 6.1", "+6.4*", "+1.9*"],
       ["25", "37.5", "45.9 ± 5.2", "46.5 ± 4.1", "32.1 ± 4.5", "+13.8*", "+0.5"],
       ["50", "74.9", "52.5 ± 3.0", "52.0 ± 2.2", "33.9 ± 2.5", "+18.6*", "−0.5"],
       ["100", "149.8", "57.2 ± 1.3", "55.9 ± 1.4", "34.3 ± 2.1", "+23.0*", "−1.3*"],
       ["250", "374.5", "61.9 ± 0.7", "59.9 ± 1.1", "34.3 ± 1.8", "+27.5*", "−2.0*"],
       ["all", "961.8", "64.1 ± 0.9", "61.5 ± 1.0", "34.6 ± 1.8", "+29.5*", "−2.6*"],
       ["LoveDA", "", "", "", "", "", ""],
       ["1", "0.09", "11.0 ± 4.0", "12.4 ± 3.5", "15.1 ± 6.6", "−4.1", "+1.4"],
       ["2", "0.19", "19.7 ± 5.8", "20.8 ± 5.9", "22.0 ± 8.5", "−2.3", "+1.1"],
       ["5", "0.47", "26.9 ± 4.2", "28.4 ± 4.4", "25.9 ± 3.7", "+1.0", "+1.5"],
       ["10", "0.94", "32.9 ± 2.9", "34.1 ± 3.3", "31.1 ± 1.2", "+1.7", "+1.3"],
       ["25", "2.4", "37.6 ± 1.2", "38.4 ± 1.2", "32.2 ± 1.8", "+5.4", "+0.8"],
       ["50", "4.7", "39.0 ± 0.9", "39.9 ± 1.2", "33.0 ± 0.9", "+6.0*", "+0.8"],
       ["100", "9.4", "41.9 ± 0.7", "42.6 ± 0.9", "33.1 ± 0.6", "+8.8*", "+0.7*"],
       ["250", "23.6", "44.1 ± 1.1", "43.6 ± 1.0", "32.8 ± 0.5", "+11.4*", "−0.6"],
       ["all", "238.0", "45.9 ± 0.1", "45.0 ± 0.1", "32.3 ± 1.2", "+13.6*", "−0.9*"]],
      [1.9, 1.5, 2.2, 2.2, 2.2, 2.6, 2.8],
      "Zero labels (k-means, K = number of classes, Hungarian-matched on the test set; optimistic): "
      "DeepGlobe 20.6 ± 2.4, LoveDA 28.6 ± 2.2. Patch-oracle ceiling: DeepGlobe 90.2 ± 0.7, LoveDA 84.0. "
      "DeepGlobe 'all' = 642–643 images; LoveDA 'all' = 2522.")
T3_BOLD_ROWS = {0, 10}

T4 = ("Table 4. Sparse point annotation versus dense image annotation (linear probe, mIoU %, mean ± SD). "
      "Paired differences use the same fold and draw.",
      ["Point labels", "DeepGlobe", "LoveDA"],
      [["100", "39.1 ± 3.7", "29.9 ± 2.6"], ["300", "47.0 ± 1.0", "34.6 ± 1.7"],
       ["1000", "52.4 ± 0.9", "36.1 ± 1.5"], ["3000", "55.1 ± 1.5", "36.4 ± 0.4"],
       ["10,000", "59.1 ± 0.8", "40.7 ± 0.4"], ["30,000", "62.2 ± 0.9", "43.8 ± 0.4"],
       ["100 points − 5 images", "+11.4 (p < 0.001)", "+3.0 (p = 0.14)"],
       ["300 points − 10 images", "+11.4 (p < 0.001)", "+1.8 (p = 0.38)"],
       ["1000 points − 50 images", "−0.1 (p = 0.89)", "−2.9 (p = 0.048)"]],
      [5.0, 5.5, 5.5],
      "After the purity rule a fully annotated image supplies on average 1366 (DeepGlobe) or 1308 "
      "(LoveDA) patch labels (DeepGlobe: 5 images ≈ 6800; 50 images ≈ 68,000). DeepGlobe fold-level "
      "tests (5 fold means): +11.4 (p = 0.001), +11.4 (p = 0.004), −0.1 (p = 0.90).")

T5 = ("Table 5. Per-class IoU (%) for selected budgets (linear probe unless stated; mean over replicates).",
      ["Class", "0 labels", "5 images", "100 points", "50 images", "All images", "Patch ceiling"],
      [["DeepGlobe", "", "", "", "", "", ""],
       ["Urban", "41.4", "39.3", "50.0", "66.2", "71.6", "88.7"],
       ["Agriculture", "36.9", "65.9", "71.9", "78.3", "83.6", "96.3"],
       ["Rangeland", "8.7", "8.4", "8.5", "15.3", "27.0", "82.8"],
       ["Forest", "15.5", "21.8", "47.0", "57.4", "73.9", "95.6"],
       ["Water", "9.4", "24.8", "37.6", "60.6", "70.3", "85.1"],
       ["Barren", "11.6", "5.7", "19.4", "37.3", "58.1", "92.7"],
       ["LoveDA", "", "", "", "", "", ""],
       ["Background", "21.2", "31.5", "32.1", "40.3", "46.7", "86.3"],
       ["Building", "46.3", "31.2", "37.4", "47.6", "54.6", "77.0"],
       ["Road", "30.3", "31.4", "30.6", "44.3", "49.4", "72.6"],
       ["Water", "26.8", "35.4", "37.9", "52.6", "64.6", "90.3"],
       ["Barren", "4.4", "1.2", "6.2", "10.7", "16.2", "86.2"],
       ["Forest", "26.7", "19.5", "18.6", "28.0", "32.9", "81.2"],
       ["Agriculture", "44.6", "38.0", "46.2", "49.7", "56.8", "94.1"]],
      [2.6, 2.1, 2.1, 2.2, 2.2, 2.3, 2.3], None)
T5_BOLD_ROWS = {0, 7}

T6 = ("Table 6. Sensitivity of the linear probe to the L2 strength λ and of cluster-then-label to the "
      "number of clusters K (mIoU %, mean ± SD).",
      ["Setting", "DG n=5", "DG n=50", "DG all", "LD n=5", "LD n=50", "LD all"],
      [["λ = 10⁻⁴", "26.3 ± 5.8", "50.5 ± 2.8", "63.9 ± 0.9", "24.0 ± 4.4", "36.8 ± 0.8", "45.7 ± 0.1"],
       ["λ = 10⁻³ (main)", "27.6 ± 6.7", "52.5 ± 3.0", "64.1 ± 0.9", "26.9 ± 4.2", "39.0 ± 0.9", "45.9 ± 0.1"],
       ["λ = 10⁻²", "28.7 ± 6.8", "53.0 ± 3.3", "62.3 ± 0.7", "29.8 ± 3.7", "40.6 ± 0.9", "45.3 ± 0.1"],
       ["λ = 10⁻¹", "28.3 ± 6.5", "50.5 ± 3.6", "57.2 ± 0.7", "30.2 ± 3.5", "40.1 ± 1.0", "43.4 ± 0.1"],
       ["K = 25", "28.5 ± 3.6", "32.7 ± 1.8", "32.5 ± 2.2", "27.5 ± 4.0", "32.0 ± 1.0", "32.0 ± 1.4"],
       ["K = 50 (main)", "28.5 ± 4.3", "34.6 ± 2.5", "34.4 ± 2.5", "25.9 ± 3.7", "33.0 ± 0.9", "32.3 ± 1.2"],
       ["K = 100", "29.0 ± 3.3", "34.7 ± 1.6", "36.7 ± 1.3", "28.4 ± 3.8", "33.1 ± 0.7", "34.8 ± 0.5"],
       ["K = 200", "29.3 ± 1.8", "38.1 ± 2.6", "38.9 ± 2.3", "27.4 ± 2.6", "33.8 ± 0.9", "36.1 ± 0.8"],
       ["Linear probe (same draws)", "29.9 ± 3.8", "53.7 ± 1.5", "64.1 ± 0.9", "26.9 ± 4.2", "39.0 ± 0.9", "45.9 ± 0.1"]],
      [3.4, 2.1, 2.1, 2.1, 2.1, 2.1, 2.1],
      "K rows on DeepGlobe use the first draw of each fold (5 replicates); the last row gives the probe "
      "on the same draws for comparison.")

T7 = ("Table 7. Backbone comparison under an identical reduced protocol (256 fixed patches per "
      "training image; mIoU %, mean ± SD; DeepGlobe 5 folds, LoveDA 3 draws).",
      ["Backbone", "0 labels", "n = 5", "n = 10", "n = 50", "All", "Cluster K=50, all"],
      [["DeepGlobe", "", "", "", "", "", ""],
       ["DINOv2 ViT-S/14", "17.3 ± 1.4", "26.7 ± 4.0", "36.2 ± 4.1", "51.3 ± 2.6", "61.8 ± 1.3", "35.2 ± 1.3"],
       ["DINOv2 ViT-B/14", "20.7 ± 0.2", "29.8 ± 3.7", "38.8 ± 4.1", "52.2 ± 2.3", "63.9 ± 0.9", "34.0 ± 1.4"],
       ["DINOv2 ViT-L/14", "18.1 ± 1.2", "28.1 ± 4.3", "36.8 ± 4.2", "52.3 ± 0.7", "63.3 ± 1.5", "31.2 ± 1.3"],
       ["ResNet-50 (IN-1k)", "21.3 ± 2.6", "24.9 ± 3.3", "31.1 ± 5.1", "46.5 ± 0.8", "57.3 ± 1.5", "35.1 ± 1.5"],
       ["LoveDA", "", "", "", "", "", ""],
       ["DINOv2 ViT-S/14", "23.5 ± 2.6", "25.3 ± 5.5", "26.9 ± 3.2", "35.7 ± 1.0", "43.7 ± 0.0", "31.5 ± 0.7"],
       ["DINOv2 ViT-B/14", "27.3 ± 2.3", "27.5 ± 4.8", "30.8 ± 2.3", "37.4 ± 1.2", "45.9 ± 0.1", "33.1 ± 0.9"],
       ["DINOv2 ViT-L/14", "25.4 ± 1.3", "28.6 ± 5.1", "31.9 ± 2.0", "38.6 ± 1.0", "46.1 ± 0.0", "31.4 ± 1.1"],
       ["ResNet-50 (IN-1k)", "21.2 ± 3.8", "21.2 ± 4.5", "23.8 ± 3.6", "31.1 ± 2.1", "41.2 ± 0.0", "30.2 ± 1.6"]],
      [3.3, 2.1, 2.1, 2.1, 2.1, 2.1, 2.2],
      "Linear probe columns unless stated. Probe > cluster-then-label (Holm p < 0.05): DeepGlobe — ViT-S/B/L "
      "from 25 images, ResNet-50 from 50; LoveDA — ViT-L from 50, ViT-B from 100, ViT-S from 250, ResNet-50 "
      "not significant (3 draws).")
T7_BOLD_ROWS = {0, 5}

T8 = ("Table 8. End-to-end DeepLabV3-ResNet50 fine-tuning versus the frozen DINOv2-B probe trained on "
      "the identical labelled images (mIoU %, mean ± SD over 3 matched runs).",
      ["Dataset", "Images", "Fine-tuned DeepLabV3", "Linear probe", "Balanced probe", "Probe − fine-tune (p)"],
      [["DeepGlobe", "10", "41.4 ± 2.5", "40.9 ± 2.7", "41.8 ± 2.1", "−0.5 (0.86)"],
       ["DeepGlobe", "100", "59.7 ± 4.7", "58.2 ± 1.1", "56.3 ± 1.1", "−1.5 (0.54)"],
       ["LoveDA", "10", "27.4 ± 3.7", "31.8 ± 1.6", "33.1 ± 2.0", "+4.4 (0.10)"],
       ["LoveDA", "100", "42.3 ± 0.9", "42.0 ± 0.9", "42.8 ± 1.2", "−0.2 (0.78)"]],
      [2.4, 1.6, 3.3, 2.7, 2.7, 3.3],
      "Training cost per run: fine-tuning ≈ 30 min (1500 iterations) on a GTX 1060 Max-Q; probe: seconds "
      "on cached features. DeepGlobe runs use folds 0–2, draw 0; LoveDA runs use draws 0–2.")

T9 = ("Table 9. LoveDA urban–rural transfer: linear-probe mIoU (%) by training domain and test domain "
      "(mean ± SD over 5 draws).",
      ["Training pool", "Images", "Test rural", "Test urban"],
      [["Rural", "10", "29.9 ± 4.3", "29.0 ± 5.1"], ["Rural", "100", "37.3 ± 0.7", "41.7 ± 1.2"],
       ["Rural", "all (1366)", "41.1", "47.3"],
       ["Urban", "10", "20.0 ± 6.2", "28.6 ± 7.9"], ["Urban", "100", "31.7 ± 1.6", "41.1 ± 1.1"],
       ["Urban", "all (1156)", "36.7", "45.8"],
       ["Rural + urban", "10", "29.3 ± 3.3", "35.2 ± 3.0"], ["Rural + urban", "100", "37.5 ± 1.3", "43.4 ± 1.1"],
       ["Rural + urban", "all (2522)", "40.8 ± 0.1", "48.2 ± 0.1"]],
      [4.0, 3.0, 4.5, 4.5],
      "Rural-trained − urban-trained (paired over draws): test rural +9.8 (p = 0.035) at n = 10 and +5.6 "
      "(p = 0.002) at n = 100; test urban +0.4 (p = 0.92) and +0.6 (p = 0.52). Full-pool rows are "
      "deterministic (SD = 0).")

T10 = ("Table 10. Per-class IoU (%) with in-domain and cross-domain training on LoveDA (n = 100 images, "
       "mean over 5 draws).",
       ["Class", "Rural test: rural-trained", "Rural test: urban-trained", "Δ", "Urban test: urban-trained",
        "Urban test: rural-trained", "Δ"],
       [["Background", "41.0", "37.4", "−3.6", "35.9", "32.7", "−3.2"],
        ["Building", "49.4", "38.8", "−10.6", "50.3", "49.1", "−1.2"],
        ["Road", "35.1", "36.8", "+1.7", "52.3", "46.8", "−5.5"],
        ["Water", "56.7", "49.6", "−7.1", "58.7", "55.3", "−3.4"],
        ["Barren", "5.3", "6.8", "+1.5", "13.0", "26.9", "+13.8"],
        ["Forest", "20.3", "14.6", "−5.6", "34.4", "35.2", "+0.8"],
        ["Agriculture", "53.5", "38.1", "−15.3", "43.1", "45.7", "+2.6"]],
       [2.6, 2.5, 2.5, 1.5, 2.5, 2.5, 1.5], None)

FIGS = {
    1: ("fig1", "Fig. 1. Study design. Images are encoded once by a frozen backbone into a 37 × 37 grid of "
        "patch features. Labels are collected either as fully annotated images (dense) or as random "
        "single-pixel points (sparse). Four classifiers are fitted on the features and scored at pixel "
        "level against the reference masks; a patch oracle gives the resolution ceiling."),
    2: ("fig1_label_efficiency", "Fig. 2. Label efficiency on frozen DINOv2 ViT-B/14 features. mIoU versus the "
        "number of fully annotated training images (log scale) for the linear probe, the class-balanced "
        "probe and cluster-then-label (K = 50); the dotted line is the optimistic zero-label k-means "
        "baseline. Lines show means and bands ± 1 SD over 15 (DeepGlobe) or 5 (LoveDA) replicates."),
    3: ("fig2_points_vs_dense", "Fig. 3. Sparse point labels versus dense image annotation, plotted against "
        "the number of labelled locations (one fully annotated image = 1369 patch labels). At equal "
        "numbers of labels, spread-out points are far more accurate on both datasets."),
    5: ("fig4_backbones", "Fig. 5. Linear-probe label efficiency for four frozen backbones under an identical "
        "protocol. The three DINOv2 models (self-supervised) outperform the ImageNet-supervised ResNet-50 "
        "at almost every budget; ViT-L brings no gain over ViT-B."),
    6: ("fig3_domain_transfer", "Fig. 6. LoveDA urban–rural transfer. Linear-probe mIoU on rural (left) and "
        "urban (right) test images for probes trained on rural, urban or both domains. Rural training "
        "transfers to urban scenes with no detectable loss; urban training transfers poorly to rural "
        "scenes."),
    4: ("fig5_per_class", "Fig. 4. Per-class IoU of the linear probe as a function of the number of fully "
        "annotated images. Rangeland (DeepGlobe) and barren (LoveDA) remain poor at every budget."),
}

# insertion points (after the paragraph whose text starts with the key)
PLACE = {
    "Fig. 1 summarises the pipeline": [("fig", 1)],
    "Table 2 summarises all experiments": [("table", T2)],
    "Table 3 and Fig. 2 report": [("table", T3, T3_BOLD_ROWS), ("fig", 2)],
    "Spreading labels was far more efficient": [("table", T4), ("fig", 3)],
    "Per-class IoU (Table 5, Fig. 4)": [("table", T5, T5_BOLD_ROWS), ("fig", 4)],
    "Table 6 shows that": [("table", T6)],
    "The same picture emerged": [("table", T7, T7_BOLD_ROWS), ("fig", 5)],
    "End-to-end fine-tuning of DeepLabV3": [("table", T8)],
    "Transfer between LoveDA domains": [("table", T9), ("fig", 6)],
    "Per-class differences locate the loss": [("table", T10)],
}


# ════════════════════════════════════════════════════════════════
# Rendering helpers
# ════════════════════════════════════════════════════════════════
def set_cell_border(cell, **kw):
    tcPr = cell._tc.get_or_add_tcPr()
    b = tcPr.find(qn("w:tcBorders"))
    if b is None:
        b = OxmlElement("w:tcBorders"); tcPr.append(b)
    for edge, val in kw.items():
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), val); el.set(qn("w:sz"), "6"); el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "000000")
        b.append(el)


def runs(par, text, size=None, bold=False):
    for i, seg in enumerate(re.split(r"\*(.+?)\*", text)):
        if not seg:
            continue
        r = par.add_run(seg)
        r.italic = (i % 2 == 1)
        r.bold = bold
        r.font.name = FONT
        if size:
            r.font.size = Pt(size)
    return par


def para(doc, text, style=None, size=None, bold=False, align=None, before=0, after=6, spacing=1.15,
         indent=False, keep=False):
    par = doc.add_paragraph(style=style)
    runs(par, text, size, bold)
    pf = par.paragraph_format
    pf.space_before, pf.space_after = Pt(before), Pt(after)
    pf.line_spacing = spacing
    if align is not None:
        par.alignment = align
    if indent:
        pf.first_line_indent = Cm(0.6)
    if keep:
        pf.keep_with_next = True
    return par


def add_table(doc, spec, bold_rows=()):
    title, header, rows, widths, note = spec
    para(doc, title, size=10, bold=False, before=8, after=4, spacing=1.0, keep=True)
    t = doc.add_table(rows=1 + len(rows), cols=len(header))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for r_i, row in enumerate([header] + rows):
        for c_i, val in enumerate(row):
            cell = t.cell(r_i, c_i)
            cell.width = Cm(widths[c_i])
            cell.text = ""
            pp = cell.paragraphs[0]
            pp.paragraph_format.space_after = Pt(1); pp.paragraph_format.space_before = Pt(1)
            pp.paragraph_format.line_spacing = 1.0
            isgroup = (r_i - 1) in bold_rows
            r = pp.add_run(val); r.font.size = Pt(8.5); r.font.name = FONT
            r.bold = (r_i == 0) or isgroup
            r.italic = isgroup
            if c_i > 0 and not isgroup:
                pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if r_i == 0:
                set_cell_border(cell, top="single", bottom="single")
            if r_i == len(rows):
                set_cell_border(cell, bottom="single")
            elif r_i < len(rows):
                pp.paragraph_format.keep_with_next = True     # keep the table on one page
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit"); trPr.append(cs)
    if note:
        para(doc, note, size=8.5, before=2, after=8, spacing=1.0)
    else:
        para(doc, "", size=4, after=6, spacing=1.0)


def add_fig(doc, n):
    stem, cap = FIGS[n]
    png = FIG / f"{stem}.png"
    par = doc.add_paragraph(); par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.keep_with_next = True
    par.add_run().add_picture(str(png), width=Cm(14 if n != 1 else 15.5))
    para(doc, cap, size=10, before=2, after=10, spacing=1.0)


def line_numbers(section):
    ln = OxmlElement("w:lnNumType")
    ln.set(qn("w:countBy"), "1"); ln.set(qn("w:restart"), "continuous"); ln.set(qn("w:distance"), "283")
    section._sectPr.append(ln)


def page_number_footer(section):
    fp = section.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run()
    for tag, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        if tag:
            el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), tag)
        else:
            el = OxmlElement("w:instrText"); el.set(qn("xml:space"), "preserve"); el.text = txt
        r._r.append(el)


def base_doc():
    doc = Document()
    st = doc.styles["Normal"]; st.font.name = FONT; st.font.size = Pt(11)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    for m in ("left_margin", "right_margin"):
        setattr(sec, m, Cm(2.5))
    sec.top_margin = sec.bottom_margin = Cm(2.5)
    return doc


# ════════════════════════════════════════════════════════════════
def build_manuscript():
    doc = base_doc()
    sec = doc.sections[0]
    page_number_footer(sec)
    line_numbers(sec)
    # title page
    para(doc, TITLE, size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=12, spacing=1.2)
    pa = doc.add_paragraph(); pa.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for i, (name, aff, corr) in enumerate(AUTHORS):
        r = pa.add_run(name); r.font.size = Pt(12)
        s = pa.add_run(aff + ("*" if corr else "")); s.font.superscript = True
        if i < len(AUTHORS) - 1:
            pa.add_run(", ")
    for k, v in AFFIL.items():
        pp = doc.add_paragraph(); pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        s = pp.add_run(k); s.font.superscript = True; s.font.size = Pt(10)
        r = pp.add_run(" " + v); r.italic = True; r.font.size = Pt(10)
    para(doc, "* " + CORR, size=10, before=10, spacing=1.0)
    para(doc, EMAILS, size=10, spacing=1.0, after=12)
    para(doc, "Highlights", size=12, bold=True, before=6, after=4)
    for h in HIGHLIGHTS:
        para(doc, "• " + h, size=11, spacing=1.15, after=2)
    para(doc, "Abstract", size=12, bold=True, before=12, after=4)
    para(doc, ABSTRACT, spacing=1.15, after=8, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    pk = para(doc, "", after=6)
    r = pk.add_run("Keywords: "); r.bold = True
    pk.add_run(KEYWORDS)
    doc.add_paragraph().add_run().add_break(__import__("docx").enum.text.WD_BREAK.PAGE)

    for kind, *rest in B:
        if kind == "h1":
            para(doc, rest[0], size=13, bold=True, before=14, after=6, keep=True)
        elif kind == "h2":
            par = para(doc, rest[0], size=12, before=8, after=4, keep=True)
            for r in par.runs:
                r.italic = True
        elif kind == "p":
            text = rest[0]
            para(doc, text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True)
            for key, items in PLACE.items():
                if text.startswith(key):
                    for it in items:
                        if it[0] == "fig":
                            add_fig(doc, it[1])
                        else:
                            add_table(doc, it[1], it[2] if len(it) > 2 else ())
        elif kind == "table":
            title, header, rows, widths = rest
            add_table(doc, (title, header, rows, widths, None))
        elif kind == "bullets":
            for btxt in rest[0]:
                par = para(doc, "• " + btxt, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=4)
                par.paragraph_format.left_indent = Cm(0.8)
                par.paragraph_format.first_line_indent = Cm(-0.4)
    for head, txt in BACK:
        para(doc, head, size=12, bold=True, before=12, after=4, keep=True)
        para(doc, txt, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    para(doc, "References", size=13, bold=True, before=14, after=6, keep=True)
    for ref in sorted(REFS, key=lambda s: s.lower().replace("ñ", "n")):
        par = para(doc, ref, size=10, spacing=1.0, after=3, align=WD_ALIGN_PARAGRAPH.LEFT)
        par.paragraph_format.left_indent = Cm(0.6)
        par.paragraph_format.first_line_indent = Cm(-0.6)
    out = OUTDIR / "Wellu_Mensah_LabelBudget_RSASE_manuscript.docx"
    # keep each figure caption on the same page as its figure
    for par in doc.paragraphs:
        if re.match(r"^Fig\. \d+\. ", par.text):
            par.paragraph_format.keep_together = True
    doc.save(out)
    return out


def build_highlights():
    doc = base_doc()
    para(doc, "Highlights", size=14, bold=True, after=8)
    for h in HIGHLIGHTS:
        para(doc, "• " + h, spacing=1.5, after=4)
    out = OUTDIR / "Highlights.docx"
    doc.save(out)
    return out


def checks():
    body = " ".join(x[1] if isinstance(x[1], str) else " ".join(x[1]) for x in B)
    words = len(re.findall(r"\S+", body))
    print(f"abstract words: {len(ABSTRACT.split())}; body words: {words}")
    assert len(ABSTRACT.split()) <= 250, "abstract exceeds the 250-word limit"
    for h in HIGHLIGHTS:
        assert len(h) <= 85, (len(h), h)
    print("highlights ≤ 85 chars:", [len(h) for h in HIGHLIGHTS])
    # every in-text citation (Author, year) has a reference and vice versa
    refkeys = {(re.match(r"([^,]+),", r).group(1).split()[-1].replace("ñ", "n"),
                re.search(r"\b(19|20)\d\d\b", r).group(0)) for r in REFS}
    cites = set()
    for m in re.finditer(r"([A-Z][A-Za-zñé\-]+)(?: et al\.| and [A-Z][A-Za-z\-]+)?,? \(?((?:19|20)\d\d)", body):
        cites.add((m.group(1).replace("ñ", "n"), m.group(2)))
    surnames = {k[0] for k in refkeys}
    missing = sorted(c for c in cites if c[0] in surnames and c not in refkeys)
    unused = sorted(k for k in refkeys if k not in cites)
    print("cited but year mismatch:", missing)
    print("references never cited:", unused)


def order_check():
    """Every table/figure is cited in the text before it is placed, all are present,
    and numbering follows the order of first citation."""
    seq = []   # ("cite"|"place", "T"|"F", n) in document order
    pat = re.compile(r"\b(Table|Fig\.)\s+(\d+)((?:\s*(?:,|and)\s*(?:(?:Table|Fig\.)\s+)?\d+)*)")

    def cites(text):
        for m in pat.finditer(text):
            kind = "T" if m.group(1) == "Table" else "F"
            seq.append(("cite", kind, int(m.group(2))))
            for m2 in re.finditer(r"(?:(Table|Fig\.)\s+)?(\d+)", m.group(3)):
                if m2.group(1):
                    kind = "T" if m2.group(1) == "Table" else "F"
                seq.append(("cite", kind, int(m2.group(2))))

    def tnum(title):
        return int(re.match(r"Table (\d+)", title).group(1))

    for kind, *rest in B:
        if kind == "p":
            cites(rest[0])
            for key, items in PLACE.items():
                if rest[0].startswith(key):
                    for it in items:
                        seq.append(("place", "F", it[1]) if it[0] == "fig" else ("place", "T", tnum(it[1][0])))
        elif kind == "table":
            seq.append(("place", "T", tnum(rest[0])))
        elif kind == "bullets":
            for b in rest[0]:
                cites(b)
    ok = True
    for k, name in (("T", "Table"), ("F", "Fig.")):
        first = []
        for ev, kk, n in seq:
            if kk == k and ev == "cite" and n not in first:
                first.append(n)
        placed = [n for ev, kk, n in seq if kk == k and ev == "place"]
        if first != sorted(first):
            print(f"  ORDER ERROR {name}: first citations in order {first}"); ok = False
        if placed != list(range(1, len(placed) + 1)):
            print(f"  PLACEMENT ORDER/MISSING {name}: {placed}"); ok = False
        for i, (ev, kk, n) in enumerate(seq):
            if ev == "place" and kk == k and ("cite", k, n) not in seq[:i]:
                print(f"  NOT CITED BEFORE PLACEMENT: {name} {n}"); ok = False
        print(f"{name}: first cited in order {first}; placed in order {placed}")
    assert ok, "table/figure order check failed"


def verify_docx(path, n_tables=10, n_figs=6):
    """Check the rendered .docx itself: every caption present once, in order, and cited earlier."""
    doc = Document(str(path))
    paras = [p.text for p in doc.paragraphs]          # body paragraphs in order (table cells excluded)
    cap = re.compile(r"^(Table|Fig\.) (\d+)\. ")
    found, ok = {"Table": [], "Fig.": []}, True
    for i, t in enumerate(paras):
        m = cap.match(t)
        if not m:
            continue
        kind, n = m.group(1), int(m.group(2))
        found[kind].append(n)
        before = " ".join(x for x in paras[:i] if not cap.match(x))
        if not re.search(rf"\b{re.escape(kind)}\s+{n}\b|{re.escape(kind)}\s+\d+(?:,| and) {n}\b", before):
            print(f"  NOT CITED BEFORE CAPTION: {kind} {n}"); ok = False
    for kind, total in (("Table", n_tables), ("Fig.", n_figs)):
        if found[kind] != list(range(1, total + 1)):
            print(f"  CAPTIONS {kind}: {found[kind]} (expected 1..{total})"); ok = False
    print("rendered docx captions:", found)
    assert ok, "rendered document check failed"


if __name__ == "__main__":
    # Fig. 1 schematic must exist
    assert (FIG / "fig1.png").exists(), "run manuscript/make_fig1.py first"
    checks()
    order_check()
    out = build_manuscript()
    verify_docx(out)
    print(out)
    print(build_highlights())
