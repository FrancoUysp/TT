import joblib
import xgboost as xgb
from base_model import BaseModel

class XGBoostModel(BaseModel):
    def initialize_model(self):
        self.model = xgb.XGBClassifier(**self.params)
        return self.model

    def train(self, training_data, target, num_round=100):
        dtrain = xgb.DMatrix(training_data, label=target)
        
        self.model = xgb.train(
            self.params, 
            dtrain, 
            num_round, 
            evals=[(dtrain, 'train')]
        )
        
        self.save_model()
        print(f"Model trained and saved to {self.model_path}.")


    def save_model(self):
        joblib.dump(self.model, self.model_path)
        print(f"XGBoost model saved to {self.model_path}.")
