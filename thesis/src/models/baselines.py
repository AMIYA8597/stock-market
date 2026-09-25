import numpy as np

class NaivePersistence:
    def __init__(self, h_days):
        self.h_days = h_days

    def fit(self, X, y):
        pass

    def predict(self, X):
        # Assume X is an array of shape (N, L) where X[:, -1] is the last 1-day return
        # A simple naive prediction: if the sum of the last h_days return is > 0, predict 1
        # For simplicity in feature shape, we assume X contains the past returns
        past_returns = np.sum(X[:, -self.h_days:], axis=1)
        return (past_returns > 0).astype(int)

class Reversal:
    def __init__(self, h_days):
        self.h_days = h_days

    def fit(self, X, y):
        pass

    def predict(self, X):
        past_returns = np.sum(X[:, -self.h_days:], axis=1)
        return (past_returns <= 0).astype(int)

class MajorityClass:
    def __init__(self):
        self.majority_class = 1

    def fit(self, X, y):
        self.majority_class = 1 if np.mean(y) >= 0.5 else 0

    def predict(self, X):
        return np.full(X.shape[0], self.majority_class)
