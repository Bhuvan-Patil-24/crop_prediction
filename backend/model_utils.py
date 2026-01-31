import joblib
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "backend",
    "models",
    "rabi_xgboost_model.pkl"
)

ENCODER_PATH = os.path.join(
    BASE_DIR,
    "backend",
    "models",
    "rabi_label_encoder.pkl"
)

# Load once at startup
model = joblib.load(MODEL_PATH)
label_encoder = joblib.load(ENCODER_PATH)

def predict_crop(features):
    """
    features: list of floats in exact training order
    """
    pred_encoded = model.predict([features])[0]
    pred_label = label_encoder.inverse_transform([pred_encoded])[0]
    return pred_label
