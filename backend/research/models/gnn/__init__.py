"""Graph neural forecasting utilities for cross-asset spillover modeling."""

from research.models.gnn.dataset import DynamicGraphSnapshot, build_dynamic_graph_dataset
from research.models.gnn.graph_builder import CorrelationGraph, build_correlation_graph
from research.models.gnn.inference import infer_spillover
from research.models.gnn.model import GraphSpilloverNet
from research.models.gnn.trainer import GNNTrainConfig, train_gnn

__all__ = [
    "DynamicGraphSnapshot",
    "build_dynamic_graph_dataset",
    "CorrelationGraph",
    "build_correlation_graph",
    "GraphSpilloverNet",
    "GNNTrainConfig",
    "train_gnn",
    "infer_spillover",
]
