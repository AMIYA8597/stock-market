import optuna
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split


def objective(trial, X, y):
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 50, 300),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.1, log=True),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
    }

    X_train, X_valid, y_train, y_valid = train_test_split(X, y, test_size=0.2, shuffle=False)

    model = xgb.XGBClassifier(**params, random_state=42)
    model.fit(X_train, y_train)

    preds = model.predict(X_valid)
    return accuracy_score(y_valid, preds)

def run_tuning(X: pd.DataFrame, y: pd.Series, n_trials=20):
    study = optuna.create_study(direction="maximize")
    study.optimize(lambda trial: objective(trial, X, y), n_trials=n_trials)

    print("Best trial:")
    print("  Value: ", study.best_trial.value)
    print("  Params: ")
    for key, value in study.best_trial.params.items():
        print(f"    {key}: {value}")

    return study.best_trial.params

