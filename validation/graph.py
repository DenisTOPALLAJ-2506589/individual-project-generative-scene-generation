import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# =========================================================
# Load CSV
# =========================================================

csv_path = "all_validation_metrics.csv"

df = pd.read_csv(csv_path)

# =========================================================
# Style
# =========================================================

sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (18, 6)
plt.rcParams["font.size"] = 11

# =========================================================
# Create Figure
# =========================================================

fig, axes = plt.subplots(1, 3, figsize=(20, 6))

# =========================================================
# PSNR
# =========================================================

sns.boxplot(data=df, x="dataset", y="psnr", palette="Set2", ax=axes[0])

sns.stripplot(
    data=df, x="dataset", y="psnr", color="black", size=4, alpha=0.6, ax=axes[0]
)

axes[0].set_title("PSNR Distribution")
axes[0].set_xlabel("")
axes[0].set_ylabel("PSNR (dB)")
axes[0].tick_params(axis="x", rotation=15)

# =========================================================
# SSIM
# =========================================================

sns.boxplot(data=df, x="dataset", y="ssim", palette="Set2", ax=axes[1])

sns.stripplot(
    data=df, x="dataset", y="ssim", color="black", size=4, alpha=0.6, ax=axes[1]
)

axes[1].set_title("SSIM Distribution")
axes[1].set_xlabel("")
axes[1].set_ylabel("SSIM")
axes[1].tick_params(axis="x", rotation=15)

# =========================================================
# LPIPS
# =========================================================

sns.boxplot(data=df, x="dataset", y="lpips", palette="Set2", ax=axes[2])

sns.stripplot(
    data=df, x="dataset", y="lpips", color="black", size=4, alpha=0.6, ax=axes[2]
)

axes[2].set_title("LPIPS Distribution")
axes[2].set_xlabel("")
axes[2].set_ylabel("LPIPS (Lower is Better)")
axes[2].tick_params(axis="x", rotation=15)

# =========================================================
# Layout
# =========================================================

plt.tight_layout()

# =========================================================
# Save
# =========================================================

plt.savefig("validation_metric_distributions.png", dpi=300, bbox_inches="tight")

# =========================================================
# Show
# =========================================================

plt.show()
