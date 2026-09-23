from sqlalchemy import Column, Integer
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import declarative_base
Base = declarative_base()
class PaymentTransaction(Base):
    __tablename__ = 'dummy_paymenttransaction'
    id = Column(Integer, primary_key=True)

from .billing import OrganizationSubscription as Subscription
from .billing import Plan

class BillingAuditLog(Base):
    __tablename__ = 'dummy_billing_audit_log'
    id = Column(Integer, primary_key=True)
class WalletLedger(Base):
    __tablename__ = 'dummy_wallet_ledger'
    id = Column(Integer, primary_key=True)
