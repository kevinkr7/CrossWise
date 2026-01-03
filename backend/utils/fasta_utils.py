from Bio import SeqIO

def read_fasta(file_stream):
    sequences = []
    for record in SeqIO.parse(file_stream, "fasta"):
        sequences.append(str(record.seq).upper())
    return sequences

def validate_sequence(seq):
    return all(base in "ATGC" for base in seq)

def nucleotide_frequencies(seqs):
    total_len = sum(len(s) for s in seqs)
    counts = {"A":0,"T":0,"G":0,"C":0}

    for seq in seqs:
        for base in seq:
            counts[base] += 1

    return {k: counts[k]/total_len for k in counts}
