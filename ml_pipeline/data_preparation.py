from Bio import SeqIO
from Bio.SeqUtils import gc_fraction
from sklearn.preprocessing import OneHotEncoder
import pandas as pd
import numpy as np

# Step 1: Parse FASTA Files
def parse_fasta(file_path):
    """Parse a FASTA file and return a list of sequences."""
    sequences = []
    for record in SeqIO.parse(file_path, "fasta"):
        sequences.append(str(record.seq))
    return sequences

# Input FASTA files
dna_file_1 = "Fasta_files\Solanum_pimpinellifolium.fasta"
dna_file_2 = "Fasta_files\Solanum_lycopersicum.SL3.0.dna.chromosome.4.fasta"

# Parse sequences from both files
dna_sequences_1 = parse_fasta(dna_file_1)
dna_sequences_2 = parse_fasta(dna_file_2)

# Combine sequences for unified processing
all_dna_sequences = dna_sequences_1 + dna_sequences_2

# Step 2: Validate Sequences
def validate_sequence(seq):
    """Ensure the sequence contains valid DNA bases."""
    valid_bases = set("ACGT")
    return all(base in valid_bases for base in seq)

# Filter out invalid sequences
all_dna_sequences = [seq for seq in all_dna_sequences if validate_sequence(seq)]

# Step 3: Extract Features
def extract_dna_features(dna_seq):
    """Extract features from a DNA sequence."""
    gc_content = gc_fraction(dna_seq) * 100  # Convert GC content to percentage
    return {
        "length": len(dna_seq),
        "gc_content": gc_content,
        "has_start_codon": dna_seq.startswith("ATG"),
        "num_codons": len(dna_seq) // 3,
    }

# Extract features for each DNA sequence
features = [extract_dna_features(seq) for seq in all_dna_sequences]

# Step 4: Convert to One-Hot Encoding (Optional)
def one_hot_encode_sequence(seq):
    """One-hot encode a DNA sequence."""
    encoder = OneHotEncoder(categories=[list("ACGT")], sparse=False, dtype=int)
    seq_array = np.array(list(seq)).reshape(-1, 1)  # Reshape for encoding
    return encoder.fit_transform(seq_array)

# Example one-hot encoding of the first sequence (optional; for demonstration)
if all_dna_sequences:
    example_one_hot = one_hot_encode_sequence(all_dna_sequences[0])
    print("Example One-Hot Encoding (first sequence):")
    print(example_one_hot)

# Step 5: Prepare DataFrame
# Add source file information to features
sources = ["File1"] * len(dna_sequences_1) + ["File2"] * len(dna_sequences_2)
for i, feature in enumerate(features):
    feature["file_source"] = sources[i]

# Create a DataFrame from the features
df = pd.DataFrame(features)

# Step 6: Save Processed Data
output_csv = "processed_dna_features.csv"
df.to_csv(output_csv, index=False)
print(f"Features saved to {output_csv}")

# Step 7: Prepare for Machine Learning
# Normalize numerical columns (if needed)
from sklearn.preprocessing import MinMaxScaler

scaler = MinMaxScaler()
numerical_columns = ["length", "gc_content", "num_codons"]
df[numerical_columns] = scaler.fit_transform(df[numerical_columns])

# Save normalized data for ML
ml_ready_csv = "ml_ready_dna_features.csv"
df.to_csv(ml_ready_csv, index=False)
print(f"ML-ready features saved to {ml_ready_csv}")

# Display final DataFrame
print(df.head())
