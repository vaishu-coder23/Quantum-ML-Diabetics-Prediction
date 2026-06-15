from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib
import os
import numpy as np
from lime import lime_tabular

class ClassicalEngine:
    def __init__(self):
        self.model = LogisticRegression(max_iter=1000)
        self.is_trained = False
        self.metrics = {}
        self.explainer = None
        self._training_sample = None  # stored to reconstruct explainer on load
        self.feature_names = [
            'Pregnancies', 'Glucose', 'BloodPressure', 'SkinThickness', 
            'Insulin', 'BMI', 'DiabetesPedigreeFunction', 'Age'
        ]

    def _build_explainer(self, X_train_sample):
        """Build (or rebuild) the LIME explainer from training samples."""
        self.explainer = lime_tabular.LimeTabularExplainer(
            training_data=np.array(X_train_sample),
            feature_names=self.feature_names,
            class_names=['No Diabetes', 'Diabetes'],
            mode='classification'
        )

    def train(self, X_train, y_train, X_test, y_test):
        print("Training Classical Logistic Regression...")
        self.model.fit(X_train, y_train)

        # Store a sample of training data for post-load explainer reconstruction
        self._training_sample = np.array(X_train[:200])
        self._build_explainer(self._training_sample)

        # Evaluate
        y_pred = self.model.predict(X_test)
        self.metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1': f1_score(y_test, y_pred)
        }
        self.is_trained = True
        return self.metrics

    def predict(self, X_input):
        if not self.is_trained:
            raise Exception("Classical model not trained.")
        prob = self.model.predict_proba(X_input)[0][1]
        label = int(self.model.predict(X_input)[0])
        return label, prob

    def explain(self, X_input):
        if not self.explainer:
            return {}
        try:
            exp = self.explainer.explain_instance(
                X_input[0],
                self.model.predict_proba,
                num_features=len(self.feature_names)
            )
            return {name: float(weight) for name, weight in exp.as_list()}
        except Exception as e:
            print(f"XAI explanation failed: {e}")
            return {}

    def analyze_condition(self, input_dict, risk_prob):
        """Estimate diabetes type or alternative conditions based on clinical indicators."""
        glucose = float(input_dict.get('Glucose', 0))
        bmi = float(input_dict.get('BMI', 0))
        age = float(input_dict.get('Age', 0))
        bp = float(input_dict.get('BloodPressure', 0))
        
        analysis = {
            'type': "Normal",
            'suggestion': "Maintain a healthy diet and regular exercise.",
            'exercise': "30-minute brisk walk or light swimming 5 days a week.",
            'alternatives': []
        }
        
        if risk_prob > 0.5:
            if age < 30 and bmi < 25:
                analysis['type'] = "Potential Type 1 Diabetes"
                analysis['suggestion'] = "Consult an endocrinologist for Type 1 screening and insulin evaluation."
            else:
                analysis['type'] = "Type 2 Diabetes Risk"
                analysis['suggestion'] = "Focus on low-carb diet, weight management, and regular glucose monitoring."
                analysis['exercise'] = "45-minute aerobic workout (brisk walking, cycling) combined with light resistance training."
        else:
            if glucose > 100 and glucose < 125:
                analysis['type'] = "Pre-diabetes Warning"
                analysis['suggestion'] = "Lifestyle changes can reverse this. Increase activity and reduce refined sugars."
                analysis['exercise'] = "Increase daily step count to 10,000+ and include HIIT sessions twice weekly."
            
            # Check for alternative conditions if diabetes risk is low
            if bp > 140:
                analysis['alternatives'].append("Hypertension (High Blood Pressure)")
            if bmi > 30:
                analysis['alternatives'].append("Obesity / Metabolic Syndrome")
            
        return analysis

    def save_model(self, path='models/classical_model.pkl'):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Do NOT pickle the explainer — only pickle model, metrics, training sample
        joblib.dump({
            'model': self.model,
            'metrics': self.metrics,
            'training_sample': self._training_sample
        }, path)

    def load_model(self, path='models/classical_model.pkl'):
        if os.path.exists(path):
            data = joblib.load(path)
            self.model = data['model']
            self.metrics = data['metrics']
            self._training_sample = data.get('training_sample')
            if self._training_sample is not None:
                self._build_explainer(self._training_sample)
            self.is_trained = True
            return True
        return False
