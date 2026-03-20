"""Explainability algorithms for model attribution and counterfactuals."""

from research.explainability.attention_extractor import extract_attention_weights, summarize_attention
from research.explainability.counterfactual import Counterfactual, generate_counterfactuals_linear
from research.explainability.shap_explainer import ShapExplanation, approximate_tree_shap, top_contributors

__all__ = [
	"Counterfactual",
	"ShapExplanation",
	"approximate_tree_shap",
	"extract_attention_weights",
	"generate_counterfactuals_linear",
	"summarize_attention",
	"top_contributors",
]
