"""
Train GPU-Accelerated Model for Massive Datasets
Uses XGBoost with CUDA support.
"""
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os
import time

# Define model path
MODEL_DIR = "backend/ml_models"
MODEL_PATH = os.path.join(MODEL_DIR, "failure_prediction_model.pkl")

def train_gpu_model():
    # 1. Generate HUGE Synthetic Data (1 Million Rows)
    print("🚀 Generating 1,000,000 telemetry records...")
    start_time = time.time()
    
    n_samples = 1_000_000  # Huge dataset
    
    # Using float32 to save GPU memory
    data = {
        'engine_temp': np.random.normal(90, 15, n_samples).astype(np.float32),
        'rpm': np.random.normal(2500, 1000, n_samples).astype(np.float32),
        'battery': np.random.normal(12.6, 1.0, n_samples).astype(np.float32),
        'oil': np.random.normal(70, 20, n_samples).astype(np.float32),
        'vibration': np.random.normal(2, 1.5, n_samples).astype(np.float32),
    }
    
    df = pd.DataFrame(data)
    
    # Define "Failure" Logic (Ground Truth)
    conditions = [
        (df['engine_temp'] > 115) | (df['oil'] < 25) | (df['vibration'] > 6), # CRITICAL (2)
        (df['engine_temp'] > 105) | (df['battery'] < 11.0),                   # WARNING (1)
    ]
    choices = [2, 1] 
    df['risk_level'] = np.select(conditions, choices, default=0) # 0 = HEALTHY
    
    print(f"✅ Data generation complete in {time.time() - start_time:.2f}s")

    # 2. Prepare Data
    X = df[['engine_temp', 'rpm', 'battery', 'oil', 'vibration']]
    y = df['risk_level']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 3. Configure XGBoost for GPU
    print(f"🔥 Training XGBoost on GPU (CUDA)...")
    train_start = time.time()
    
    # XGBoost Classifier with GPU support
    model = xgb.XGBClassifier(
        n_estimators=500,        # Number of trees
        learning_rate=0.05,
        max_depth=10,            # Deep trees for complex patterns
        device="cuda",           # <--- THIS ENABLES GPU
        tree_method="hist",      # Optimized histogram algorithm
        objective="multi:softprob",
        num_class=3,             # Healthy, Warning, Critical
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    duration = time.time() - train_start
    print(f"✅ Training complete in {duration:.2f}s")

    # 4. Evaluate
    print("📊 Evaluating model...")
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    
    print(f"🎯 Accuracy: {acc*100:.2f}%")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Healthy', 'Warning', 'Critical']))

    # 5. Save
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)
    
    # We save using joblib, which handles XGBoost objects correctly
    joblib.dump(model, MODEL_PATH)
    print(f"💾 GPU-trained model saved to: {MODEL_PATH}")

if __name__ == "__main__":
    try:
        train_gpu_model()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Ensure you have NVIDIA Drivers and CUDA installed.")