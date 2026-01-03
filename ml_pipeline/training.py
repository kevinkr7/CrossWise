import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import LabelEncoder
import joblib

# Load the dataset
df = pd.read_csv('focused_orphan_crops.csv')

# Data Preprocessing
label_encoder = LabelEncoder()
df['Hybrid_Crop_encoded'] = label_encoder.fit_transform(df['Hybrid_Crop'])

# Define features and targets
features = [
    'Parent_1_A', 'Parent_1_T', 'Parent_1_G', 'Parent_1_C',
    'Parent_2_A', 'Parent_2_T', 'Parent_2_G', 'Parent_2_C'
]

classification_target = 'Hybrid_Crop_encoded'
regression_targets = [
    'GC_Content (%)', 'SNP_Count', 'Yield_Potential (kg/ha)',
    'Drought_Resistance_Score', 'Disease_Resistance_Score'
]

# Split data
X = df[features]
y_class = df[classification_target]
y_reg = df[regression_targets]

X_train, X_test, y_class_train, y_class_test, y_reg_train, y_reg_test = train_test_split(
    X, y_class, y_reg, test_size=0.2, random_state=42
)

# Train models
classifier = RandomForestClassifier(n_estimators=100, random_state=42)
classifier.fit(X_train, y_class_train)

regressor = MultiOutputRegressor(RandomForestRegressor(n_estimators=100, random_state=42))
regressor.fit(X_train, y_reg_train)

# Save models and encoders properly
model_dict = {
    'classifier': classifier,
    'regressor': regressor,
    'label_encoder': label_encoder,
    'features': features,
    'regression_targets': regression_targets,
    'classes': label_encoder.classes_  # Save the classes for inverse transform
}

# Save with protocol=4 for broader compatibility
joblib.dump(model_dict, 'hybrid_crop_model.pkl', protocol=4)

print("Model saved successfully as hybrid_crop_model.pkl")