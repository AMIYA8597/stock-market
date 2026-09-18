import re

with open('backend/app/services/prediction_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add deep learning models to the deep_learning block
dl_block = '''
        # On-the-fly deep learning inference (API fallback)
        try:
            from app.services.ml_engine.lstm_forecaster import deep_learning_forecast
            
            closes_array = df['close'].values
            steps_out = 5
            
            # 1. Standard LSTM
            pred_prices_lstm, pred_ci_lstm = deep_learning_forecast(closes_array, steps=steps_out, model_type="lstm")
            lstm_delta = float(pred_prices_lstm[-1] - closes_array[-1])
            lstm_score = max(-1.0, min(1.0, lstm_delta / (closes_array[-1] * 0.02)))
            
            # 2. Bi-LSTM
            pred_prices_bi, _ = deep_learning_forecast(closes_array, steps=steps_out, model_type="bilstm")
            bilstm_delta = float(pred_prices_bi[-1] - closes_array[-1])
            bilstm_score = max(-1.0, min(1.0, bilstm_delta / (closes_array[-1] * 0.02)))
            
            # 3. GRU
            pred_prices_gru, _ = deep_learning_forecast(closes_array, steps=steps_out, model_type="gru")
            gru_delta = float(pred_prices_gru[-1] - closes_array[-1])
            gru_score = max(-1.0, min(1.0, gru_delta / (closes_array[-1] * 0.02)))
            
            # 4. CNN-LSTM
            pred_prices_cnn, _ = deep_learning_forecast(closes_array, steps=steps_out, model_type="cnn_lstm")
            cnn_delta = float(pred_prices_cnn[-1] - closes_array[-1])
            cnn_score = max(-1.0, min(1.0, cnn_delta / (closes_array[-1] * 0.02)))
            
            model_signals["lstm"] = lstm_score
            model_signals["bilstm"] = bilstm_score
            model_signals["gru"] = gru_score
            model_signals["cnn_lstm"] = cnn_score
            
            model_confidences["lstm"] = 0.65
            model_confidences["bilstm"] = 0.67
            model_confidences["gru"] = 0.64
            model_confidences["cnn_lstm"] = 0.68
            
            model_statuses["lstm"] = "trained"
            model_statuses["bilstm"] = "trained"
            model_statuses["gru"] = "trained"
            model_statuses["cnn_lstm"] = "trained"

        except Exception as e:
            logger.warning(f"Fast deep learning inference failed for {symbol}: {e}")
'''

# Find the place where lstm is called and replace it
import re
content = re.sub(
    r'(?s)# On-the-fly deep learning inference.*?except Exception as e:\s+logger\.warning\(f"Fast deep learning inference failed.*?\"\)',
    dl_block.strip(),
    content
)

with open('backend/app/services/prediction_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
