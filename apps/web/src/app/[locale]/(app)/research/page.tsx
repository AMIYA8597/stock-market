import { Link } from '@/i18n/navigation';

const researchTools = [
  {
    href: "/research/regime-analysis",
    title: "Regime Analysis",
    description: "Hidden Markov Model regime detection — identify bull, bear, and sideways market states with transition probabilities.",
  },
  {
    href: "/research/correlation-graph",
    title: "Correlation Graph",
    description: "Interactive correlation matrix and network graph across Nifty 50 stocks over configurable time windows.",
  },
  {
    href: "/research/factor-exposure",
    title: "Factor Exposure",
    description: "Decompose stock returns into factor betas — momentum, value, size, volatility, and quality factors.",
  },
  {
    href: "/research/model-performance",
    title: "Model Performance",
    description: "Track directional accuracy, Sharpe ratio, and calibration curves across all AI/ML prediction models.",
  },
  {
    href: "/research/explainability",
    title: "Explainability Lab",
    description: "SHAP waterfall plots, attention heatmaps, and counterfactual analysis for model transparency.",
  },
  {
    href: "/research/leakage-lab",
    title: "Leakage Lab",
    description: "Compare predictions against actual subsequent prints using scatter plots to detect data leakage.",
  },
];

export default function ResearchPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Research Lab</h1>
      <p className="text-sm text-[var(--nq-text-secondary)] mb-6">
        Advanced quantitative research tools for market analysis, model evaluation, and signal decomposition.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {researchTools.map((tool) => (
          <Link
            key={tool.href}
            href={tool.href}
            className="block rounded-lg border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-5 transition-all hover:border-[var(--nq-accent-cyan)] hover:shadow-lg hover:shadow-[rgba(0,212,245,0.05)]"
          >
            <h3 className="text-base font-semibold text-[var(--nq-text-primary)] mb-2">{tool.title}</h3>
            <p className="text-xs text-[var(--nq-text-secondary)] leading-relaxed">{tool.description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
