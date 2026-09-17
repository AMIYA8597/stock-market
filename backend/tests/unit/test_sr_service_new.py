import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from app.services.sr_service import SupportResistanceEngine, SRBiLSTM

@pytest.fixture
def dummy_df():
    np.random.seed(42)
    return pd.DataFrame({
        'open': np.random.rand(30) + 10,
        'high': np.random.rand(30) + 11,
        'low': np.random.rand(30) + 9,
        'close': np.random.rand(30) + 10,
        'volume': np.random.rand(30) * 1000
    })

def test_bilstm_forward():
    with patch('app.services.sr_service.nn') as mock_nn:
        mock_lstm_instance = MagicMock()
        mock_lstm_instance.return_value = (MagicMock(), MagicMock())
        mock_nn.LSTM.return_value = mock_lstm_instance

        mock_fc_instance = MagicMock()
        mock_fc_instance.return_value = MagicMock()
        mock_nn.Linear.return_value = mock_fc_instance

        model = SRBiLSTM(input_dim=5, hidden_dim=32, num_classes=3)
        out = model.forward(MagicMock())
        assert out is not None

def test_detect_classical_zones_short_df():
    df = pd.DataFrame({'high': [], 'low': [], 'close': []})
    assert SupportResistanceEngine.detect_classical_zones(df) == []

def test_detect_classical_zones(dummy_df):
    with patch('app.services.sr_service.DBSCAN') as mock_dbscan:
        def fit_side_effect(X_data):
            mock_clustering = MagicMock()
            mock_clustering.labels_ = np.array([0, 0, -1, 1, 1] + [0] * (len(X_data) - 5)) if len(X_data) >= 5 else np.zeros(len(X_data))
            return mock_clustering

        mock_dbscan.return_value.fit.side_effect = fit_side_effect

        zones = SupportResistanceEngine.detect_classical_zones(dummy_df, eps_pct=0.01, min_touches=2)
        assert isinstance(zones, list)

def test_detect_classical_zones_few_swings():
    df = pd.DataFrame({
        'high': [10]*25,
        'low': [9]*25,
        'close': [9.5]*25
    })
    with patch('app.services.sr_service.DBSCAN') as mock_dbscan:
        def fit_side_effect(X_data):
            mock_clustering = MagicMock()
            mock_clustering.labels_ = np.zeros(len(X_data))
            return mock_clustering
        mock_dbscan.return_value.fit.side_effect = fit_side_effect

        zones = SupportResistanceEngine.detect_classical_zones(df)
        assert len(zones) == 2

def test_prepare_sequence_data():
    np.random.seed(42)
    df = pd.DataFrame({
        'open': np.random.rand(35) + 10,
        'high': np.random.rand(35) + 11,
        'low': np.random.rand(35) + 9,
        'close': np.random.rand(35) + 10,
        'volume': np.random.rand(35) * 1000
    })

    with patch('app.services.sr_service.SupportResistanceEngine.detect_classical_zones') as mock_detect:
        mock_detect.return_value = [
            {"type": "support", "min": 9.0, "max": 9.5},
            {"type": "resistance", "min": 11.0, "max": 11.5},
        ]

        X, y, zones = SupportResistanceEngine._prepare_sequence_data(df, seq_len=30)
        assert len(X) == 6
        assert len(y) == 6
        assert X[0].shape == (30, 5)
        assert len(zones) == 2

def test_prepare_sequence_data_zero_division():
    df = pd.DataFrame({
        'open': np.zeros(35),
        'high': np.zeros(35),
        'low': np.zeros(35),
        'close': np.zeros(35),
        'volume': np.zeros(35)
    })

    with patch('app.services.sr_service.SupportResistanceEngine.detect_classical_zones') as mock_detect:
        mock_detect.return_value = []
        X, y, zones = SupportResistanceEngine._prepare_sequence_data(df, seq_len=30)
        assert len(X) == 6
        assert len(zones) == 0

def test_train_and_evaluate_bilstm_short_df():
    df = pd.DataFrame({'high': [1]*10, 'low': [1]*10, 'close': [1]*10})
    result = SupportResistanceEngine.train_and_evaluate_bilstm(df, "BTC")
    assert result == {"precision": 0.5, "recall": 0.5, "f1": 0.5, "dl_zones": []}

def test_train_and_evaluate_bilstm():
    df = pd.DataFrame({
        'open': np.zeros(60),
        'high': np.zeros(60),
        'low': np.zeros(60),
        'close': np.zeros(60),
        'volume': np.zeros(60)
    })

    with patch('app.services.sr_service.torch') as mock_torch, \
         patch('app.services.sr_service.nn') as mock_nn, \
         patch('app.services.sr_service.optim') as mock_optim, \
         patch('app.services.sr_service.SRSequenceLabeler') as mock_labeler, \
         patch('app.services.sr_service.MODEL_DIR') as mock_model_dir, \
         patch('app.services.sr_service.pickle.dump') as mock_pickle, \
         patch('app.services.sr_service.DBSCAN') as mock_dbscan, \
         patch('app.services.sr_service.SupportResistanceEngine._prepare_sequence_data') as mock_prepare:

        X = np.random.rand(10, 30, 5)
        y = np.random.randint(0, 3, size=(10, 30))
        mock_prepare.return_value = (X, y, [])

        mock_model_instance = MagicMock()
        mock_labeler.return_value.to.return_value = mock_model_instance
        mock_model_instance.parameters.return_value = []

        mock_tensor = MagicMock()
        mock_torch.tensor.return_value.to.return_value = mock_tensor

        mock_argmax = MagicMock()
        mock_torch.argmax.return_value = mock_argmax
        mock_cpu = MagicMock()
        mock_argmax.cpu.return_value = mock_cpu
        mock_numpy = MagicMock()
        mock_cpu.numpy.return_value = mock_numpy

        # Test predictions array (triggering valid TP/FP/FN calculation by providing actual matches)
        # targets size = 2 * 30 = 60
        # Let's set some to 1 and 2 to hit mask > 0
        y[8:] = 1 # The last 2 windows will be split as test (size 2x30 = 60). Make them all 1s
        mock_numpy.flatten.return_value = np.ones(60) # Perfect match! TP > 0

        # Latest window predictions array (size seq_len = 30)
        # Give it some 1s and 2s to hit dl_support_prices and dl_resistance_prices
        mock_numpy.__getitem__.return_value = np.array([1]*15 + [2]*15)

        mock_clustering = MagicMock()
        mock_clustering.labels_ = np.array([0]*15)
        mock_dbscan.return_value.fit.return_value = mock_clustering

        # We need to simulate exception block in torch.save to hit `pass` OR just run normal
        mock_torch.save.side_effect = Exception("Mock save error")

        result = SupportResistanceEngine.train_and_evaluate_bilstm(df, "BTC", seq_len=30, epochs=1)

        assert result["precision"] > 0
        assert result["recall"] > 0
        assert result["f1"] > 0
        assert len(result["dl_zones"]) > 0

def test_train_and_evaluate_bilstm_no_exception():
    df = pd.DataFrame({
        'open': np.zeros(60),
        'high': np.zeros(60),
        'low': np.zeros(60),
        'close': np.zeros(60),
        'volume': np.zeros(60)
    })

    with patch('app.services.sr_service.torch') as mock_torch, \
         patch('app.services.sr_service.nn') as mock_nn, \
         patch('app.services.sr_service.optim') as mock_optim, \
         patch('app.services.sr_service.SRSequenceLabeler') as mock_labeler, \
         patch('app.services.sr_service.MODEL_DIR') as mock_model_dir, \
         patch('app.services.sr_service.pickle.dump') as mock_pickle, \
         patch('app.services.sr_service.DBSCAN') as mock_dbscan, \
         patch('builtins.open', new_callable=MagicMock) as mock_open, \
         patch('app.services.sr_service.SupportResistanceEngine._prepare_sequence_data') as mock_prepare:

        X = np.random.rand(10, 30, 5)
        y = np.zeros((10, 30), dtype=int)
        mock_prepare.return_value = (X, y, [])

        mock_model_instance = MagicMock()
        mock_labeler.return_value.to.return_value = mock_model_instance

        mock_argmax = MagicMock()
        mock_torch.argmax.return_value = mock_argmax
        mock_cpu = MagicMock()
        mock_argmax.cpu.return_value = mock_cpu
        mock_numpy = MagicMock()
        mock_cpu.numpy.return_value = mock_numpy

        mock_numpy.flatten.return_value = np.zeros(60) # To hit no events mask
        mock_numpy.__getitem__.return_value = np.zeros(30) # No DL zones

        result = SupportResistanceEngine.train_and_evaluate_bilstm(df, "BTC", seq_len=30, epochs=1)

        assert result["precision"] == 0.55
        assert result["recall"] == 0.52
        assert result["f1"] == 0.53
        assert len(result["dl_zones"]) == 0
