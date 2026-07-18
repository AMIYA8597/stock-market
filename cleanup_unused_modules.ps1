# Cleanup script for unused Python modules identified by audit
$backupPath = 'd:/work/stock-market/unused_backup'
# Ensure backup directory exists
New-Item -ItemType Directory -Force -Path $backupPath | Out-Null

$mods = @(
    'start_server','temp_test_market','__init__','run_uvicorn','test_api','test_prediction',
    'verify_determinism','verify_endpoints','test_api_endpoints','test_indicators',
    'test_market_data','test_sentiment','test_yf','test_yf_news','audit_repository',
    'seed_data','train_models','main','flatted','env','config','data_pipeline',
    'inference_pipeline','retraining_trigger','training_pipeline','compute_features',
    'init_dev_db','model_trainer','run_individual_model_backtests','run_sequential_build',
    'run_walk_forward_backtest','seed_universe','tick_producer','train_all_checkpoints',
    'train_meta_learner','train_quantile_forecaster','verify_schema','backtest_tasks',
    'celery_app','data_tasks','email_tasks','training_tasks','conftest',
    'test_api_auth_compat','test_api_backtest','test_api_journal','test_api_market',
    'test_api_payments','test_api_portfolio_prompt_contract','test_api_signals',
    'test_api_user_journey','test_critical_paths','test_websocket','test_data_ingestion',
    'test_feature_builders','test_feature_pipeline','test_garch','test_meta_learner',
    'test_online_learner','test_paper_trading','test_xgboost_mismatch','analytics',
    'cost_model','engine','monte_carlo','run_walk_forward','statistical_tests',
    'walk_forward','attention_extractor','counterfactual','shap_explainer','base',
    'calendar_effects','chart_patterns','cross_sectional','ff5_betas','microstructure',
    'pipeline','price_factors','sentiment_factors'
)

foreach ($m in $mods) {
    Get-Item -Path "d:/work/stock-market/$m*" -ErrorAction SilentlyContinue |
        Move-Item -Destination $backupPath -Force
}
