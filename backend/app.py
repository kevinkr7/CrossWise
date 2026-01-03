from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import io  # Required to convert binary file uploads to text for Biopython

# Import your helper functions
# Ensure you have a folder named 'utils' containing 'fasta_utils.py'
try:
    from utils.fasta_utils import read_fasta, validate_sequence, nucleotide_frequencies
except ImportError:
    print("⚠️ Warning: Could not import 'utils.fasta_utils'. Ensure the folder structure is correct.")

app = Flask(__name__)
CORS(app)

# Load model once
try:
    model = joblib.load("models/hybrid_crop_model.pkl")
    print("✅ Model loaded successfully.")
except FileNotFoundError:
    print("❌ Error: 'models/hybrid_crop_model.pkl' not found. Prediction will fail.")
    model = None

# --- ROUTE 1: MANUAL INPUT ---
@app.route("/predict/manual", methods=["POST"])
def predict_manual():
    if not model:
        return jsonify({"error": "Model not loaded"}), 500
        
    data = request.get_json()

    required = [
        'Parent_1_A','Parent_1_T','Parent_1_G','Parent_1_C',
        'Parent_2_A','Parent_2_T','Parent_2_G','Parent_2_C'
    ]

    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing {field}"}), 400

    X = [[
        data['Parent_1_A'], data['Parent_1_T'],
        data['Parent_1_G'], data['Parent_1_C'],
        data['Parent_2_A'], data['Parent_2_T'],
        data['Parent_2_G'], data['Parent_2_C']
    ]]

    try:
        traits = model['regressor'].predict(X)[0]

        response = {
            "hybrid_crop": "Predicted Hybrid",
            "gc_content": float(traits[0]),
            "snp_count": float(traits[1]),
            "yield_potential": float(traits[2]),
            "drought_resistance": float(traits[3]),
            "disease_resistance": float(traits[4])
        }
        return jsonify(response)
    
    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500


# --- ROUTE 2: FASTA FILE INPUT ---
@app.route("/predict/fasta", methods=["POST"])
def predict_fasta():
    if not model:
        return jsonify({"error": "Model not loaded"}), 500

    # 1. Check if files exist in request
    if 'parent1' not in request.files or 'parent2' not in request.files:
        return jsonify({"error": "Both FASTA files (parent1, parent2) are required"}), 400

    # 2. Wrap the binary stream with TextIOWrapper so Biopython can read it
    try:
        p1_file = io.TextIOWrapper(request.files['parent1'], encoding='utf-8')
        p2_file = io.TextIOWrapper(request.files['parent2'], encoding='utf-8')
    except Exception as e:
        return jsonify({"error": "Failed to process file encoding."}), 400

    # 3. Read sequences using your utility
    try:
        seqs1 = read_fasta(p1_file)
        seqs2 = read_fasta(p2_file)
    except Exception as e:
        return jsonify({"error": f"Error parsing FASTA files: {str(e)}"}), 400

    if not seqs1 or not seqs2:
        return jsonify({"error": "One or both FASTA files are empty"}), 400

    # 4. Validate sequences
    for seq in seqs1 + seqs2:
        if not validate_sequence(seq):
            return jsonify({"error": "Invalid DNA sequence detected (non-ATGC characters found)"}), 400

    # 5. Calculate Nucleotide Frequencies
    f1 = nucleotide_frequencies(seqs1)
    f2 = nucleotide_frequencies(seqs2)

    # 6. Prepare Input Vector X (Order must match Manual Input)
    # Order: P1_A, P1_T, P1_G, P1_C, P2_A, P2_T, P2_G, P2_C
    X = [[
        f1["A"], f1["T"], f1["G"], f1["C"],
        f2["A"], f2["T"], f2["G"], f2["C"]
    ]]

    # 7. Predict
    try:
        traits = model['regressor'].predict(X)[0]

        return jsonify({
            "hybrid_crop": "Predicted Hybrid (FASTA)",
            "gc_content": float(traits[0]),
            "snp_count": float(traits[1]),
            "yield_potential": float(traits[2]),
            "drought_resistance": float(traits[3]),
            "disease_resistance": float(traits[4])
        })
    except Exception as e:
        return jsonify({"error": f"Prediction logic failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)