from sqlalchemy import String, Float, Integer, ForeignKey, JSON, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from src.config.database import Base
class User(Base):
    __tablename__="users"
    id:Mapped[int]=mapped_column(primary_key=True)
    email:Mapped[str]=mapped_column(String(100),unique=True)
    password_hash:Mapped[str]=mapped_column(String(300))
    role:Mapped[str]=mapped_column(String(20))
class Batch(Base):
    __tablename__="batches"
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(50),unique=True)
    line:Mapped[str]=mapped_column(String(20))
    supplier:Mapped[str]=mapped_column(String(80))
    tonnes:Mapped[float]=mapped_column(Float)
    received_date:Mapped[str]=mapped_column(String(10))
class Inspection(Base):
    __tablename__="inspections"
    id:Mapped[int]=mapped_column(primary_key=True)
    sample_code:Mapped[str]=mapped_column(String(70),unique=True)
    batch_id:Mapped[int]=mapped_column(ForeignKey("batches.id"))
    flour_yield:Mapped[float]=mapped_column(Float)
    moisture:Mapped[float]=mapped_column(Float)
    inspector:Mapped[str]=mapped_column(String(50))
class Review(Base):
    __tablename__="reviews"
    id:Mapped[int]=mapped_column(primary_key=True)
    title:Mapped[str]=mapped_column(String(120))
    line:Mapped[str]=mapped_column(String(20))
    status:Mapped[str]=mapped_column(String(20),default="queued")
    result:Mapped[dict]=mapped_column(JSON,default=dict)
    snapshot:Mapped[list]=mapped_column(JSON,default=list)
    note:Mapped[str]=mapped_column(Text,default="")
    source:Mapped[str]=mapped_column(String(10),default="ledger")
    source_meta:Mapped[dict]=mapped_column(JSON,default=dict)
    created_by:Mapped[str]=mapped_column(String(100))
    approved_by:Mapped[str]=mapped_column(String(100),default="")
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class SyncRun(Base):
    __tablename__="sync_runs"
    id:Mapped[int]=mapped_column(primary_key=True)
    status:Mapped[str]=mapped_column(String(20),default="queued")
    phase:Mapped[str]=mapped_column(String(20),default="")
    batches_copied:Mapped[int]=mapped_column(Integer,default=0)
    inspections_copied:Mapped[int]=mapped_column(Integer,default=0)
    batches_scanned:Mapped[int]=mapped_column(Integer,default=0)
    inspections_scanned:Mapped[int]=mapped_column(Integer,default=0)
    checkpoint_batch:Mapped[int]=mapped_column(Integer,default=0)
    checkpoint_inspection:Mapped[int]=mapped_column(Integer,default=0)
    error:Mapped[str]=mapped_column(Text,default="")
    created_by:Mapped[str]=mapped_column(String(100))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    started_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=True)
    finished_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=True)
class ReconcileReport(Base):
    __tablename__="reconcile_reports"
    id:Mapped[int]=mapped_column(primary_key=True)
    kind:Mapped[str]=mapped_column(String(20),default="reconcile")
    status:Mapped[str]=mapped_column(String(20),default="clean")
    summary:Mapped[dict]=mapped_column(JSON,default=dict)
    details:Mapped[list]=mapped_column(JSON,default=list)
    created_by:Mapped[str]=mapped_column(String(100))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class Audit(Base):
    __tablename__="audits"
    id:Mapped[int]=mapped_column(primary_key=True)
    actor:Mapped[str]=mapped_column(String(100))
    action:Mapped[str]=mapped_column(String(200))
    status:Mapped[int]=mapped_column(Integer)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
