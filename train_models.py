from backend.data_processor import DataProcessor
from backend.quantum_engine import QuantumEngine
from backend.classical_engine import ClassicalEngine
from backend.scripts.debug_models import list_generate_models
import os

def main():
    print("--- System Pre-training and Initialization ---")
    
    # 1. Process Data
    dp = DataProcessor()
    print("Loading dataset...")
    X_train, X_test, y_train, y_test = dp.load_data()
    dp.save_processors()
    print(f"Data processed. PCA reduced to {X_train.shape[1]} features.")

    # 2. Train Classical Model (Fast)
    ce = ClassicalEngine()
    print("Training Classical model...")
    metrics = ce.train(X_train, y_train, X_test, y_test)
    ce.save_model()
    print(f"Classical Model Metrics: {metrics}")

    # 3. Train Quantum Model (Slow - using small subset for demo)
    qe = QuantumEngine(num_qubits=8)
    print("Training Quantum model (subset of 20 samples)...")
    # Small subset for quick 8-qubit training
    qe.train(X_train[:20], y_train[:20])
    qe.save_model()
    print("Quantum Model pre-trained and saved.")

    print("\nSystem ready for deployment!")

if __name__ == "__main__":
    main()
