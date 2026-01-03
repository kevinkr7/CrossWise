import joblib
import pandas as pd

# Load the saved model
model_data = joblib.load('random_forest_yield_model.pkl')

# Example new data (replace with actual values)
new_data = pd.DataFrame([[
    0.5, 0.1, 0.2, 0.2,  # Parent 1: A, T, G, C
    0.3, 0.3, 0.2, 0.2   # Parent 2: A, T, G, C
]], columns=model_data['features'])

# Make predictions
crop_type_encoded = model_data['classifier'].predict(new_data)
crop_type = model_data['label_encoder'].inverse_transform(crop_type_encoded)
traits = model_data['regressor'].predict(new_data)

print(f"Predicted Hybrid Crop: {crop_type[0]}")
print("Predicted Traits:")
for target, value in zip(model_data['regression_targets'], traits[0]):
    print(f"{target}: {value:.2f}")