from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
import xgboost as xgb
import lightgbm as lgb
import catboost as cb
import pandas as pd

class ClassicalEnsembleTrainers:
    @staticmethod
    def train_random_forest(X: pd.DataFrame, y: pd.Series):
        model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        model.fit(X, y)
        return model

    @staticmethod
    def train_extra_trees(X: pd.DataFrame, y: pd.Series):
        model = ExtraTreesClassifier(n_estimators=100, max_depth=5, random_state=42)
        model.fit(X, y)
        return model

    @staticmethod
    def train_xgboost(X: pd.DataFrame, y: pd.Series):
        model = xgb.XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42)
        model.fit(X, y)
        return model

    @staticmethod
    def train_lightgbm(X: pd.DataFrame, y: pd.Series):
        model = lgb.LGBMClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42)
        model.fit(X, y)
        return model

    @staticmethod
    def train_catboost(X: pd.DataFrame, y: pd.Series):
        model = cb.CatBoostClassifier(n_estimators=100, depth=4, learning_rate=0.05, random_state=42, verbose=0)
        model.fit(X, y)
        return model

