import os
import sys

def main():
    print("Starting Thesis Pipeline")
    # Phase 0: Setup
    print("Phase 0: Complete")

    # Phase 1: SLR
    print("Running Phase 1: SLR")
    os.system("python src/run_phase_1.py")
    os.system("python src/plot_prisma.py")

    # Phase 2: Data Collection
    print("Running Phase 2: Data Collection")
    os.system("python src/data_collection.py")

    # Phase 3: Splits and Cost model
    print("Running Phase 3: Cost test and splits")
    os.system("pytest tests/test_costs.py")
    os.system("pytest tests/test_walk_forward.py")
    
    # Phase 4: Baselines
    print("Running Phase 4: Baselines")
    os.system("python src/run_baselines.py")

    # Phase 5: Leakage Audit
    print("Running Phase 5: Leakage Audit")
    os.system("python src/run_leakage_audit.py")

    # Phase 6 & 7: Proposed Model & Stats
    print("Running Phase 6 & 7: RGS-Fusion & Stats")
    os.system("python src/run_model.py")
    
    # Phase 8: Economic Backtest
    print("Running Phase 8: Backtest")
    os.system("python src/run_backtest.py")
    
    # Phase 9: Report Generation
    print("Running Phase 9: Tables and Figures")
    os.system("python src/make_tables.py")
    
    print("Pipeline Finished.")

if __name__ == "__main__":
    main()
