from flask import Flask, render_template, request
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from qiskit.circuit.library import ZZFeatureMap
from qiskit.primitives import Sampler
from qiskit_machine_learning.algorithms import VQC
from qiskit.algorithms.optimizers import COBYLA

def build_and_train():
    columns = [
        "Pregnancies",
        "Glucose",
        "BloodPressure",
        "SkinThickness",
        "Insulin",
        "BMI",
        "DiabetesPedigreeFunction",
        "Age",
        "Outcome"
    ]

    data = pd.read_csv("diabetes.csv", names=columns)

    X = data.drop("Outcome", axis=1)
    y = data["Outcome"].to_numpy()

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_scaled = X_scaled[:, :2]

    feature_map = ZZFeatureMap(feature_dimension=2, reps=2)
    optimizer = COBYLA(maxiter=50)
    sampler = Sampler()

    vqc = VQC(
        sampler=sampler,
        feature_map=feature_map,
        optimizer=optimizer,
    )

    vqc.fit(X_scaled, y)
    return vqc, scaler

if __name__ == "__main__":
    build_and_train()
