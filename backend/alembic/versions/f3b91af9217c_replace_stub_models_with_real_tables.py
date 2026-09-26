"""Replace disconnected stub models with real migrated tables

These 13 tables back models that used to be 7-line placeholder stubs (their
own disconnected declarative_base(), a dummy_* tablename, no migration)
while still being imported and used throughout live API routes, Celery
tasks, and services. See app/models/{blog,csrf_token,email_job,
notification,journal,watchlist,sentiment,signal,feature_vectors,
regime_states,model_artifact,model_metric,prediction}.py for the real
model definitions this migration creates tables for.

Revision ID: f3b91af9217c
Revises: 53aef4df1952
Create Date: 2026-09-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3b91af9217c'
# Was 'a5328e632291' -- that revision's migration file no longer exists in
# the repo (deleted without updating this reference), which broke the
# chain with `KeyError: 'a5328e632291'` on any `alembic upgrade`/`history`.
# '53aef4df1952' (stage_1_init) is the only other migration that exists, so
# it's the real parent.
down_revision: Union[str, None] = '53aef4df1952'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('blog_posts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('slug', sa.String(length=180), nullable=False),
        sa.Column('title', sa.String(length=220), nullable=False),
        sa.Column('excerpt', sa.String(length=400), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('author_id', sa.String(length=64), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_blog_posts')),
        sa.UniqueConstraint('slug', name=op.f('uq_blog_posts_slug')),
    )
    op.create_index(op.f('ix_blog_posts_slug'), 'blog_posts', ['slug'], unique=True)

    op.create_table('csrf_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_csrf_tokens')),
        sa.UniqueConstraint('token', name=op.f('uq_csrf_tokens_token')),
    )
    op.create_index(op.f('ix_csrf_tokens_token'), 'csrf_tokens', ['token'], unique=True)
    op.create_index(op.f('ix_csrf_tokens_user_id'), 'csrf_tokens', ['user_id'], unique=False)

    op.create_table('email_jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('to_email', sa.String(length=255), nullable=False),
        sa.Column('template', sa.String(length=100), nullable=False),
        sa.Column('payload_json', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('last_error', sa.String(length=1024), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_email_jobs')),
    )
    op.create_index(op.f('ix_email_jobs_to_email'), 'email_jobs', ['to_email'], unique=False)

    op.create_table('notifications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=180), nullable=False),
        sa.Column('message', sa.String(length=2000), nullable=False),
        sa.Column('level', sa.String(length=20), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notifications_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications')),
    )
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)

    op.create_table('trade_journals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('tags', sa.String(length=255), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('entry_price', sa.Numeric(18, 6), nullable=True),
        sa.Column('exit_price', sa.Numeric(18, 6), nullable=True),
        sa.Column('quantity', sa.Numeric(18, 6), nullable=True),
        sa.Column('direction', sa.String(length=8), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_trade_journals_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_trade_journals')),
    )
    op.create_index(op.f('ix_trade_journals_user_id'), 'trade_journals', ['user_id'], unique=False)

    op.create_table('user_watchlists',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('list_id', sa.Integer(), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_watchlists_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_watchlists')),
        sa.UniqueConstraint('user_id', 'symbol', 'list_id', name='uq_watchlist_user_symbol_list'),
    )
    op.create_index(op.f('ix_user_watchlists_user_id'), 'user_watchlists', ['user_id'], unique=False)

    op.create_table('news_sentiment',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('symbol_id', sa.UUID(), nullable=True),
        sa.Column('headline', sa.String(length=500), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('url', sa.String(length=1000), nullable=True),
        sa.Column('sentiment_label', sa.String(length=20), nullable=True),
        sa.Column('sentiment_score', sa.Numeric(6, 4), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['symbol_id'], ['instruments.id'], name=op.f('fk_news_sentiment_symbol_id_instruments'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_news_sentiment')),
    )
    op.create_index(op.f('ix_news_sentiment_symbol_id'), 'news_sentiment', ['symbol_id'], unique=False)
    op.create_index(op.f('ix_news_sentiment_published_at'), 'news_sentiment', ['published_at'], unique=False)

    op.create_table('ensemble_signals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('symbol_id', sa.UUID(), nullable=False),
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('signal', sa.Numeric(8, 6), nullable=False),
        sa.Column('kelly_fraction', sa.Numeric(8, 6), nullable=True),
        sa.Column('direction', sa.String(length=20), nullable=True),
        sa.Column('confidence', sa.Numeric(6, 4), nullable=True),
        sa.Column('regime_state', sa.Integer(), nullable=True),
        sa.Column('inputs_used', sa.JSON(), nullable=True),
        sa.Column('outcome', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['symbol_id'], ['instruments.id'], name=op.f('fk_ensemble_signals_symbol_id_instruments'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ensemble_signals')),
    )
    op.create_index(op.f('ix_ensemble_signals_symbol_id'), 'ensemble_signals', ['symbol_id'], unique=False)
    op.create_index(op.f('ix_ensemble_signals_time'), 'ensemble_signals', ['time'], unique=False)

    op.create_table('feature_vectors',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('symbol_id', sa.UUID(), nullable=False),
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('features', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['symbol_id'], ['instruments.id'], name=op.f('fk_feature_vectors_symbol_id_instruments'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_feature_vectors')),
    )
    op.create_index(op.f('ix_feature_vectors_symbol_id'), 'feature_vectors', ['symbol_id'], unique=False)
    op.create_index(op.f('ix_feature_vectors_time'), 'feature_vectors', ['time'], unique=False)

    op.create_table('regime_states',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('symbol_id', sa.UUID(), nullable=False),
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('viterbi_state', sa.Integer(), nullable=False),
        sa.Column('state_probs', sa.JSON(), nullable=False),
        sa.Column('conditional_vol', sa.Numeric(10, 6), nullable=False),
        sa.Column('vol_forecast_5d', sa.Numeric(10, 6), nullable=True),
        sa.Column('vol_forecast_21d', sa.Numeric(10, 6), nullable=True),
        sa.ForeignKeyConstraint(['symbol_id'], ['instruments.id'], name=op.f('fk_regime_states_symbol_id_instruments'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_regime_states')),
    )
    op.create_index(op.f('ix_regime_states_symbol_id'), 'regime_states', ['symbol_id'], unique=False)
    op.create_index(op.f('ix_regime_states_time'), 'regime_states', ['time'], unique=False)

    op.create_table('model_artifacts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('symbol_id', sa.UUID(), nullable=False),
        sa.Column('model_type', sa.String(length=50), nullable=False),
        sa.Column('version_tag', sa.String(length=255), nullable=False),
        sa.Column('artifact_path', sa.String(length=1024), nullable=False),
        sa.Column('hyperparameters', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['symbol_id'], ['instruments.id'], name=op.f('fk_model_artifacts_symbol_id_instruments'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_model_artifacts')),
        sa.UniqueConstraint('version_tag', name=op.f('uq_model_artifacts_version_tag')),
    )
    op.create_index(op.f('ix_model_artifacts_symbol_id'), 'model_artifacts', ['symbol_id'], unique=False)
    op.create_index(op.f('ix_model_artifacts_is_active'), 'model_artifacts', ['is_active'], unique=False)

    op.create_table('model_metrics',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('artifact_id', sa.UUID(), nullable=False),
        sa.Column('accuracy', sa.Numeric(6, 4), nullable=True),
        sa.Column('precision', sa.Numeric(6, 4), nullable=True),
        sa.Column('recall', sa.Numeric(6, 4), nullable=True),
        sa.Column('auc', sa.Numeric(6, 4), nullable=True),
        sa.Column('sharpe', sa.Numeric(8, 4), nullable=True),
        sa.Column('cost_adjusted_sharpe', sa.Numeric(8, 4), nullable=True),
        sa.Column('regime_breakdown', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['artifact_id'], ['model_artifacts.id'], name=op.f('fk_model_metrics_artifact_id_model_artifacts'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_model_metrics')),
    )
    op.create_index(op.f('ix_model_metrics_artifact_id'), 'model_metrics', ['artifact_id'], unique=False)
    op.create_index(op.f('ix_model_metrics_created_at'), 'model_metrics', ['created_at'], unique=False)

    op.create_table('ml_predictions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('symbol_id', sa.UUID(), nullable=True),
        sa.Column('model_name', sa.String(length=50), nullable=False),
        sa.Column('time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('raw_signal', sa.Numeric(8, 6), nullable=True),
        sa.Column('p50_return', sa.Numeric(10, 6), nullable=True),
        sa.Column('actual_return', sa.Numeric(10, 6), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['symbol_id'], ['instruments.id'], name=op.f('fk_ml_predictions_symbol_id_instruments'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ml_predictions')),
    )
    op.create_index(op.f('ix_ml_predictions_symbol_id'), 'ml_predictions', ['symbol_id'], unique=False)
    op.create_index(op.f('ix_ml_predictions_model_name'), 'ml_predictions', ['model_name'], unique=False)
    op.create_index(op.f('ix_ml_predictions_time'), 'ml_predictions', ['time'], unique=False)

    # Row-level security for the three user-owned tables, following the same
    # pattern as the alerts/alert_events tables added in a5328e632291.
    for table in ["notifications", "trade_journals", "user_watchlists"]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(
            f"CREATE POLICY system_all ON {table} FOR ALL "
            f"USING (current_setting('app.is_system', true) = 'true') "
            f"WITH CHECK (current_setting('app.is_system', true) = 'true');"
        )
        op.execute(
            f"CREATE POLICY select_own_{table} ON {table} FOR SELECT "
            f"USING (user_id = NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid);"
        )


def downgrade() -> None:
    op.drop_index(op.f('ix_ml_predictions_time'), table_name='ml_predictions')
    op.drop_index(op.f('ix_ml_predictions_model_name'), table_name='ml_predictions')
    op.drop_index(op.f('ix_ml_predictions_symbol_id'), table_name='ml_predictions')
    op.drop_table('ml_predictions')

    op.drop_index(op.f('ix_model_metrics_created_at'), table_name='model_metrics')
    op.drop_index(op.f('ix_model_metrics_artifact_id'), table_name='model_metrics')
    op.drop_table('model_metrics')

    op.drop_index(op.f('ix_model_artifacts_is_active'), table_name='model_artifacts')
    op.drop_index(op.f('ix_model_artifacts_symbol_id'), table_name='model_artifacts')
    op.drop_table('model_artifacts')

    op.drop_index(op.f('ix_regime_states_time'), table_name='regime_states')
    op.drop_index(op.f('ix_regime_states_symbol_id'), table_name='regime_states')
    op.drop_table('regime_states')

    op.drop_index(op.f('ix_feature_vectors_time'), table_name='feature_vectors')
    op.drop_index(op.f('ix_feature_vectors_symbol_id'), table_name='feature_vectors')
    op.drop_table('feature_vectors')

    op.drop_index(op.f('ix_ensemble_signals_time'), table_name='ensemble_signals')
    op.drop_index(op.f('ix_ensemble_signals_symbol_id'), table_name='ensemble_signals')
    op.drop_table('ensemble_signals')

    op.drop_index(op.f('ix_news_sentiment_published_at'), table_name='news_sentiment')
    op.drop_index(op.f('ix_news_sentiment_symbol_id'), table_name='news_sentiment')
    op.drop_table('news_sentiment')

    op.drop_index(op.f('ix_user_watchlists_user_id'), table_name='user_watchlists')
    op.drop_table('user_watchlists')

    op.drop_index(op.f('ix_trade_journals_user_id'), table_name='trade_journals')
    op.drop_table('trade_journals')

    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_table('notifications')

    op.drop_index(op.f('ix_email_jobs_to_email'), table_name='email_jobs')
    op.drop_table('email_jobs')

    op.drop_index(op.f('ix_csrf_tokens_user_id'), table_name='csrf_tokens')
    op.drop_index(op.f('ix_csrf_tokens_token'), table_name='csrf_tokens')
    op.drop_table('csrf_tokens')

    op.drop_index(op.f('ix_blog_posts_slug'), table_name='blog_posts')
    op.drop_table('blog_posts')
