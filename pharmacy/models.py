"""SQLAlchemy schema for the pharmacy tracker."""

import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Role(enum.Enum):
    admin = "admin"
    operator = "operator"


class EntryType(enum.Enum):
    receive = "receive"
    dispense = "dispense"
    dispose = "dispose"
    adjust = "adjust"
    count = "count"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(Role), nullable=False, default=Role.operator)
    active = Column(Boolean, nullable=False, default=True)


class Drug(Base):
    __tablename__ = "drugs"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    strength = Column(String)
    form = Column(String)
    code = Column(String)
    schedule = Column(String)  # CII..CV
    unit = Column(String, nullable=False, default="unit")

    lots = relationship("Lot", back_populates="drug")


class Lot(Base):
    __tablename__ = "lots"

    id = Column(Integer, primary_key=True)
    drug_id = Column(Integer, ForeignKey("drugs.id"), nullable=False)
    lot_number = Column(String, nullable=False)
    expiry_date = Column(Date)

    drug = relationship("Drug", back_populates="lots")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=False)
    type = Column(Enum(EntryType), nullable=False)
    quantity_delta = Column(Numeric(12, 3), nullable=False)
    reason = Column(String)
    witness_user_id = Column(Integer, ForeignKey("users.id"))
    reference = Column(String)
    prev_hash = Column(String, nullable=False)
    entry_hash = Column(String, nullable=False)


class Count(Base):
    __tablename__ = "counts"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    counted_qty = Column(Numeric(12, 3), nullable=False)
    expected_qty = Column(Numeric(12, 3), nullable=False)
    discrepancy = Column(Numeric(12, 3), nullable=False)
    adjust_entry_id = Column(Integer, ForeignKey("ledger_entries.id"))
