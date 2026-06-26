import sys
import pathlib

project_root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from tasks.training_tasks import retrain_model

def main():
    print("Starting full model retraining...")
    for model_family in ["xgboost", "lstm_attention", "quantile_forecaster", "online_learner", "meta_learner"]:
        print(f"Retraining {model_family}...")
        res = retrain_model(model_family)
        print(f"Result for {model_family}: {res}")
    print("All model retraining tasks completed!")

if __name__ == "__main__":
    main()
