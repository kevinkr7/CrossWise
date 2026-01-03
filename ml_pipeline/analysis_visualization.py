import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Step 1: Load the Data
df = pd.read_csv("C:\College\Mini Project\ml_ready_dna_features.csv")

# Step 2: Basic Data Analysis
print("Dataset Overview:")
print(df.head())
print("\nDataset Information:")
print(df.info())
print("\nStatistical Summary:")
print(df.describe())

# Filter numeric columns for correlation
numeric_columns = df.select_dtypes(include=['float64', 'int64']).columns

# Step 3: Create Combined Subplots for Visualizations
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# 3.1: Histogram of Sequence Lengths
axes[0, 0].hist(df['length'], bins=20, color='skyblue', edgecolor='black')
axes[0, 0].set_title("Distribution of Sequence Lengths")
axes[0, 0].set_xlabel("Length (normalized)")
axes[0, 0].set_ylabel("Frequency")

# 3.2: Histogram of GC Content
axes[0, 1].hist(df['gc_content'], bins=20, color='lightgreen', edgecolor='black')
axes[0, 1].set_title("Distribution of GC Content")
axes[0, 1].set_xlabel("GC Content (normalized)")
axes[0, 1].set_ylabel("Frequency")

# 3.3: Scatterplot of Length vs. GC Content
sns.scatterplot(ax=axes[1, 0], x='length', y='gc_content', data=df, hue='file_source', palette='viridis')
axes[1, 0].set_title("Length vs. GC Content")
axes[1, 0].set_xlabel("Length (normalized)")
axes[1, 0].set_ylabel("GC Content (normalized)")

# 3.4: Correlation Heatmap
correlation_matrix = df[numeric_columns].corr()
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', fmt=".2f", ax=axes[1, 1])
axes[1, 1].set_title("Feature Correlation Heatmap")

plt.tight_layout()
plt.show()

# Step 4: Binary Feature Analysis (Optional but not in Subplots)
# Proportion of Sequences with Start Codon
start_codon_counts = df['has_start_codon'].value_counts(normalize=True)
start_codon_counts.plot(kind='bar', color=['lightcoral', 'skyblue'], edgecolor='black')
plt.title("Proportion of Sequences with Start Codon")
plt.xlabel("Has Start Codon (1 = Yes, 0 = No)")
plt.ylabel("Proportion")
plt.show()


