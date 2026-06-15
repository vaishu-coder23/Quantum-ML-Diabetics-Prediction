import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import joblib
import os

class DataProcessor:
    def __init__(self, filepath='diabetes.csv'):
        self.filepath = filepath
        self.scaler = StandardScaler()
        self.data = None
        # Pima Indians Diabetes Dataset columns
        self.feature_columns = [
            'Pregnancies', 'Glucose', 'BloodPressure', 
            'SkinThickness', 'Insulin', 'BMI', 
            'DiabetesPedigreeFunction', 'Age'
        ]
        self.target_column = 'Outcome'

    def load_data(self):
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Dataset not found at {self.filepath}")
        
        self.data = pd.read_csv(self.filepath)
        X = self.data[self.feature_columns]
        y = self.data[self.target_column].values
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale
        self.X_train_scaled = self.scaler.fit_transform(X_train)
        self.X_test_scaled = self.scaler.transform(X_test)
        
        return self.X_train_scaled, self.X_test_scaled, y_train, y_test

    def save_processors(self, path='models/'):
        os.makedirs(path, exist_ok=True)
        joblib.dump(self.scaler, os.path.join(path, 'scaler.pkl'))

    def prepare_input(self, input_dict):
        # input_dict should contain real clinical values
        # Ensure correct column order
        values = [[input_dict[col] for col in self.feature_columns]]
        scaled = self.scaler.transform(values)
        return scaled

if __name__ == "__main__":
    dp = DataProcessor()
    X_train, X_test, y_train, y_test = dp.load_data()
    dp.save_processors()
    print(f"Data loaded from {dp.filepath}. Features: {len(dp.feature_columns)}")
