"""PDF report generation for backtesting results."""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import base64
import io

try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("WeasyPrint not available. PDF generation disabled.")

logger = logging.getLogger(__name__)


class BacktestReportGenerator:
    """Generate comprehensive PDF reports from backtest results."""

    def __init__(self):
        if not WEASYPRINT_AVAILABLE:
            raise ImportError("WeasyPrint is required for PDF generation")

    def generate_report(self, results: Dict[str, Any], strategy_name: str = "Strategy",
                       author: str = "NeuroQuant", output_path: Optional[str] = None) -> bytes:
        """
        Generate PDF report from backtest results.

        Args:
            results: Backtest results dictionary
            strategy_name: Name of the strategy
            author: Report author
            output_path: Optional path to save PDF file

        Returns:
            PDF content as bytes
        """
        html_content = self._generate_html(results, strategy_name, author)

        # Generate PDF
        font_config = FontConfiguration()
        html_doc = HTML(string=html_content, base_url='.')
        css = self._get_css_styles()

        pdf_bytes = html_doc.write_pdf(stylesheets=[css], font_config=font_config)

        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)

        return pdf_bytes

    def _generate_html(self, results: Dict[str, Any], strategy_name: str, author: str) -> str:
        """Generate HTML content for the report."""
        metrics = results.get('metrics', {})
        trades = results.get('trades', pd.DataFrame())
        portfolio_values = results.get('portfolio_values', pd.Series())

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Backtest Report - {strategy_name}</title>
            <style>
                {self._get_css_styles().serialize()}
            </style>
        </head>
        <body>
            {self._generate_header(strategy_name, author)}
            {self._generate_summary_section(metrics)}
            {self._generate_performance_charts(portfolio_values)}
            {self._generate_trade_analysis(trades)}
            {self._generate_risk_metrics(metrics)}
            {self._generate_monthly_returns(portfolio_values)}
            {self._generate_trade_log(trades)}
        </body>
        </html>
        """

        return html

    def _generate_header(self, strategy_name: str, author: str) -> str:
        """Generate report header."""
        return f"""
        <div class="header">
            <h1>Backtesting Report</h1>
            <h2>{strategy_name}</h2>
            <div class="metadata">
                <p><strong>Author:</strong> {author}</p>
                <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Institution:</strong> NIT Rourkela</p>
            </div>
        </div>
        """

    def _generate_summary_section(self, metrics: Dict[str, Any]) -> str:
        """Generate summary metrics section."""
        return f"""
        <div class="section">
            <h3>Performance Summary</h3>
            <div class="metrics-grid">
                <div class="metric-card">
                    <h4>Total Return</h4>
                    <div class="metric-value {'positive' if metrics.get('total_return', 0) > 0 else 'negative'}">
                        {metrics.get('total_return', 0):.2%}
                    </div>
                </div>
                <div class="metric-card">
                    <h4>Annual Return</h4>
                    <div class="metric-value {'positive' if metrics.get('annual_return', 0) > 0 else 'negative'}">
                        {metrics.get('annual_return', 0):.2%}
                    </div>
                </div>
                <div class="metric-card">
                    <h4>Sharpe Ratio</h4>
                    <div class="metric-value {'positive' if metrics.get('sharpe_ratio', 0) > 1 else 'neutral'}">
                        {metrics.get('sharpe_ratio', 0):.2f}
                    </div>
                </div>
                <div class="metric-card">
                    <h4>Max Drawdown</h4>
                    <div class="metric-value negative">
                        {metrics.get('max_drawdown', 0):.2%}
                    </div>
                </div>
                <div class="metric-card">
                    <h4>Win Rate</h4>
                    <div class="metric-value {'positive' if metrics.get('win_rate', 0) > 0.5 else 'neutral'}">
                        {metrics.get('win_rate', 0):.1%}
                    </div>
                </div>
                <div class="metric-card">
                    <h4>Total Trades</h4>
                    <div class="metric-value neutral">
                        {metrics.get('total_trades', 0)}
                    </div>
                </div>
            </div>
        </div>
        """

    def _generate_performance_charts(self, portfolio_values: pd.Series) -> str:
        """Generate performance charts section."""
        if len(portfolio_values) == 0:
            return "<div class='section'><h3>Performance Charts</h3><p>No data available</p></div>"

        # Create simple ASCII chart (in production, would use matplotlib/seaborn)
        chart_data = self._create_portfolio_chart(portfolio_values)

        return f"""
        <div class="section">
            <h3>Portfolio Performance</h3>
            <div class="chart-container">
                <pre class="ascii-chart">{chart_data}</pre>
            </div>
        </div>
        """

    def _generate_trade_analysis(self, trades: pd.DataFrame) -> str:
        """Generate trade analysis section."""
        if len(trades) == 0:
            return "<div class='section'><h3>Trade Analysis</h3><p>No trades executed</p></div>"

        # Trade statistics
        winning_trades = trades[trades['pnl'] > 0]
        losing_trades = trades[trades['pnl'] < 0]

        return f"""
        <div class="section">
            <h3>Trade Analysis</h3>
            <div class="trade-stats">
                <table class="data-table">
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Total Trades</td><td>{len(trades)}</td></tr>
                    <tr><td>Winning Trades</td><td>{len(winning_trades)}</td></tr>
                    <tr><td>Losing Trades</td><td>{len(losing_trades)}</td></tr>
                    <tr><td>Largest Win</td><td>₹{trades['pnl'].max():,.0f}</td></tr>
                    <tr><td>Largest Loss</td><td>₹{trades['pnl'].min():,.0f}</td></tr>
                    <tr><td>Average Win</td><td>₹{winning_trades['pnl'].mean():,.0f}</td></tr>
                    <tr><td>Average Loss</td><td>₹{losing_trades['pnl'].mean():,.0f}</td></tr>
                    <tr><td>Average Holding Period</td><td>{trades['holding_period'].mean():.1f} days</td></tr>
                </table>
            </div>
        </div>
        """

    def _generate_risk_metrics(self, metrics: Dict[str, Any]) -> str:
        """Generate risk metrics section."""
        return f"""
        <div class="section">
            <h3>Risk Metrics</h3>
            <div class="metrics-grid">
                <div class="metric-card">
                    <h4>Volatility (Annual)</h4>
                    <div class="metric-value neutral">{metrics.get('volatility', 0):.2%}</div>
                </div>
                <div class="metric-card">
                    <h4>Sortino Ratio</h4>
                    <div class="metric-value {'positive' if metrics.get('sortino_ratio', 0) > 1 else 'neutral'}">
                        {metrics.get('sortino_ratio', 0):.2f}
                    </div>
                </div>
                <div class="metric-card">
                    <h4>Calmar Ratio</h4>
                    <div class="metric-value {'positive' if metrics.get('calmar_ratio', 0) > 0.5 else 'neutral'}">
                        {metrics.get('calmar_ratio', 0):.2f}
                    </div>
                </div>
                <div class="metric-card">
                    <h4>Profit Factor</h4>
                    <div class="metric-value {'positive' if metrics.get('profit_factor', 0) > 1.5 else 'neutral'}">
                        {metrics.get('profit_factor', 0):.2f}
                    </div>
                </div>
            </div>
        </div>
        """

    def _generate_monthly_returns(self, portfolio_values: pd.Series) -> str:
        """Generate monthly returns heatmap."""
        if len(portfolio_values) == 0:
            return "<div class='section'><h3>Monthly Returns</h3><p>No data available</p></div>"

        # Calculate monthly returns
        monthly_returns = portfolio_values.resample('M').last().pct_change()

        # Create simple monthly returns table
        monthly_table = self._create_monthly_returns_table(monthly_returns)

        return f"""
        <div class="section">
            <h3>Monthly Returns</h3>
            <div class="monthly-returns">
                {monthly_table}
            </div>
        </div>
        """

    def _generate_trade_log(self, trades: pd.DataFrame) -> str:
        """Generate trade log section."""
        if len(trades) == 0:
            return "<div class='section'><h3>Trade Log</h3><p>No trades executed</p></div>"

        # Show top 20 trades
        top_trades = trades.head(20)

        trade_rows = ""
        for _, trade in top_trades.iterrows():
            pnl_class = "positive" if trade['pnl'] > 0 else "negative"
            trade_rows += f"""
            <tr>
                <td>{trade['symbol']}</td>
                <td>{trade['entry_date'].strftime('%Y-%m-%d')}</td>
                <td>{trade['exit_date'].strftime('%Y-%m-%d')}</td>
                <td>{trade['direction'].title()}</td>
                <td>₹{trade['entry_price']:,.2f}</td>
                <td>₹{trade['exit_price']:,.2f}</td>
                <td class="{pnl_class}">₹{trade['pnl']:,.0f}</td>
                <td>{trade['holding_period']}</td>
            </tr>
            """

        return f"""
        <div class="section">
            <h3>Trade Log (Top 20)</h3>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Entry Date</th>
                        <th>Exit Date</th>
                        <th>Direction</th>
                        <th>Entry Price</th>
                        <th>Exit Price</th>
                        <th>P&L</th>
                        <th>Holding Period</th>
                    </tr>
                </thead>
                <tbody>
                    {trade_rows}
                </tbody>
            </table>
        </div>
        """

    def _create_portfolio_chart(self, portfolio_values: pd.Series) -> str:
        """Create simple ASCII chart of portfolio performance."""
        if len(portfolio_values) == 0:
            return "No data available"

        # Normalize to starting value
        normalized = (portfolio_values / portfolio_values.iloc[0] - 1) * 100

        # Create simple line chart
        min_val = normalized.min()
        max_val = normalized.max()
        height = 20

        chart_lines = []
        for i in range(height, -1, -1):
            line = ""
            for j in range(0, len(normalized), max(1, len(normalized) // 80)):  # Max 80 chars width
                val = normalized.iloc[j]
                normalized_val = (val - min_val) / (max_val - min_val) if max_val > min_val else 0.5
                if normalized_val * height >= i:
                    line += "█"
                else:
                    line += " "
            chart_lines.append(line)

        return "\n".join(chart_lines)

    def _create_monthly_returns_table(self, monthly_returns: pd.Series) -> str:
        """Create monthly returns table."""
        if len(monthly_returns) == 0:
            return "<p>No monthly data available</p>"

        # Group by year and month
        monthly_returns.index = pd.to_datetime(monthly_returns.index)
        monthly_pivot = monthly_returns.groupby([monthly_returns.index.year, monthly_returns.index.month]).first().unstack()

        table_html = '<table class="monthly-table"><thead><tr><th>Year</th>'
        for month in range(1, 13):
            table_html += f'<th>{datetime(2023, month, 1).strftime("%b")}</th>'
        table_html += '</tr></thead><tbody>'

        for year in monthly_pivot.index:
            table_html += f'<tr><td>{year}</td>'
            for month in range(1, 13):
                val = monthly_pivot.loc[year, month]
                if pd.isna(val):
                    table_html += '<td>-</td>'
                else:
                    css_class = "positive" if val > 0 else "negative"
                    table_html += f'<td class="{css_class}">{val:.1%}</td>'
            table_html += '</tr>'

        table_html += '</tbody></table>'
        return table_html

    def _get_css_styles(self) -> CSS:
        """Get CSS styles for the report."""
        css_content = """
        @page {
            size: A4;
            margin: 2cm;
        }

        body {
            font-family: 'Times New Roman', serif;
            font-size: 12pt;
            line-height: 1.4;
            color: #333;
        }

        .header {
            text-align: center;
            border-bottom: 2px solid #333;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }

        .header h1 {
            color: #2c3e50;
            font-size: 24pt;
            margin-bottom: 10px;
        }

        .header h2 {
            color: #34495e;
            font-size: 18pt;
            margin-bottom: 15px;
        }

        .metadata {
            font-size: 10pt;
            color: #666;
        }

        .section {
            margin-bottom: 30px;
            page-break-inside: avoid;
        }

        .section h3 {
            color: #2c3e50;
            font-size: 16pt;
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 5px;
            margin-bottom: 15px;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }

        .metric-card {
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            text-align: center;
            background: #f9f9f9;
        }

        .metric-card h4 {
            margin: 0 0 10px 0;
            font-size: 12pt;
            color: #555;
        }

        .metric-value {
            font-size: 18pt;
            font-weight: bold;
        }

        .metric-value.positive {
            color: #27ae60;
        }

        .metric-value.negative {
            color: #e74c3c;
        }

        .metric-value.neutral {
            color: #3498db;
        }

        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }

        .data-table th,
        .data-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }

        .data-table th {
            background-color: #f2f2f2;
            font-weight: bold;
        }

        .monthly-table {
            width: 100%;
            border-collapse: collapse;
        }

        .monthly-table th,
        .monthly-table td {
            border: 1px solid #ddd;
            padding: 4px;
            text-align: center;
            font-size: 10pt;
        }

        .ascii-chart {
            font-family: monospace;
            font-size: 8pt;
            white-space: pre;
            background: #f8f8f8;
            padding: 10px;
            border: 1px solid #ddd;
        }

        .trade-stats {
            margin: 20px 0;
        }
        """

        return CSS(string=css_content)