# 🌱 Hybrid Crop Predictor

An AI-driven academic project for predicting hybrid crop characteristics using
both **genomic FASTA sequences** and **manual nucleotide composition**.

This system integrates:
- A modern interactive frontend
- A backend ML inference API
- A trained machine learning model for hybrid crop trait prediction

---

## 🚨 Academic Ownership & Usage Notice (IMPORTANT)

This project is an **original academic work** developed and owned by:

**👤 Kevin K R**  
**👤 Mahasmriti S S**

📅 Year: **2025**

### ❌ Strict Usage Restrictions

This project **MUST NOT** be:
- Used as a **final year project**
- Submitted for **project showcases**
- Re-presented as **someone else’s academic work**
- Modified or redistributed for academic credit

without **explicit written permission** from the original authors.

> Viewing the repository is allowed.  
> Claiming authorship or academic credit is **not**.

---

## 🧠 Project Overview

The Hybrid Crop Predictor supports **two input modes**:

### 1️⃣ Manual Nucleotide Input
Users provide normalized proportions of:
- Adenine (A)
- Thymine (T)
- Guanine (G)
- Cytosine (C)

The backend ML model predicts:
- GC Content
- SNP Count
- Yield Potential
- Drought Resistance
- Disease Resistance

---

### 2️⃣ FASTA-Based Genomic Input
Users upload **two FASTA DNA files** (parent crops).

The backend:
- Parses FASTA using BioPython
- Validates genomic sequences
- Extracts nucleotide features
- Performs ML-based inference

This ensures **scientifically grounded processing**, not client-side simulation.

---

## 🏗️ System Architecture
```bash
Frontend (HTML / JS)
|
| REST API (JSON / FormData)
↓
Backend (Flask)
|
↓
ML Model (.pkl)
```

- **Frontend** → User interaction & visualization  
- **Backend** → Validation, parsing, ML inference  
- **ML Pipeline** → Trained offline for reproducibility  

---

## 🛠️ Technology Stack

### Frontend
- HTML5, CSS3
- Vanilla JavaScript
- Font Awesome, Google Fonts

### Backend
- Python (Flask)
- Flask-CORS
- BioPython

### Machine Learning
- Scikit-learn
- RandomForest (Classifier + Regressor)
- Joblib (model persistence)

---

## 📁 Project Structure
```bash
Hybrid-Crop-Predictor/
├── frontend/
│ └── index.html
├── backend/
│ ├── app.py
│ ├── models/
│ │ └── hybrid_crop_model.pkl
│ └── utils/
│ └── fasta_utils.py
├── ml_pipeline/
│ ├── training.py
│ ├── data_preparation.py
│ └── analysis_visualization.py
├── fasta_files/
├── docs/
├── README.md
└── LICENSE
```
---

## 🧪 Validation & Testing

- Backend API tested independently using **Postman**
- Manual and FASTA prediction flows verified
- Frontend connected only after backend validation

> This ensures correctness, reproducibility, and clean separation of concerns.

---

## 🚀 Future Scope

- Advanced SNP alignment algorithms
- Deep learning on raw genomic sequences
- Multi-crop hybrid classification
- Farmer-oriented dashboards
- Cloud deployment with secure authentication

---

## 📜 Credits

Developed with dedication and ownership by:

**Kevin K R**  
**Mahasmriti S S**

© 2025 — All rights reserved.

