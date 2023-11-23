import joblib
from io import BytesIO
import tensorflow as tf


class BaseModel:
    def __init__(self, model_path, model_params):
        self.model_path = model_path
        self.model = self.load_model(model_path)
        self.params = model_params

    def load_model(self, model_path):
        try:
            with open(model_path, 'rb') as model_file:
                buffer = BytesIO(model_file.read())
            try:
                buffer.seek(0)
                model = tf.keras.models.load_model(buffer)
                print(f"Keras model loaded from {model_path}.")
                return model
            except (tf.errors.NotFoundError, OSError):
                buffer.seek(0)
                model = joblib.load(buffer)
                print(f"Model loaded from {model_path} with joblib.")
                return model
        except FileNotFoundError:
            print(f"Model file not found at {model_path}. A new model needs to be trained.")
            return None
        except Exception as e:
            print(f"An error occurred while loading the model: {e}")
            return None

    def predict(self, data):
        if self.model is not None:
            preprocessed_data = data
            if hasattr(self.model, "predict_proba"):
                probabilities = self.model.predict_proba(preprocessed_data)
                return probabilities
            else:
                probabilities = self.model.predict(preprocessed_data)
                return probabilities
        else:
            raise ValueError("Model has not been loaded or trained.")

    def train(self, data, target):
        self.model.fit(data, target)
        self.save_model()
        print(f"Model trained and saved to {self.model_path}.")

    def save_model(self):
        with BytesIO() as f:
            if isinstance(self.model, tf.keras.Model):
                self.model.save(f, save_format="h5")
                f.seek(0)
            else:
                joblib.dump(self.model, f)
                f.seek(0)
            with open(self.model_path, "wb") as model_file:
                model_file.write(f.read())
        print(f"Model saved to {self.model_path}.")
