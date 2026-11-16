from sqlalchemy import String, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from datetime import datetime, timezone
class CenterBase(DeclarativeBase): pass
class CenterBatch(CenterBase):
    __tablename__="center_batches"
    id:Mapped[int]=mapped_column(primary_key=True)
    source_id:Mapped[int]=mapped_column(Integer,unique=True,index=True)
    code:Mapped[str]=mapped_column(String(50),unique=True)
    line:Mapped[str]=mapped_column(String(20))
    supplier:Mapped[str]=mapped_column(String(80))
    tonnes:Mapped[float]=mapped_column(Float)
    received_date:Mapped[str]=mapped_column(String(10))
    status:Mapped[str]=mapped_column(String(20),default="synced")
    synced_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class CenterInspection(CenterBase):
    __tablename__="center_inspections"
    id:Mapped[int]=mapped_column(primary_key=True)
    source_id:Mapped[int]=mapped_column(Integer,unique=True,index=True)
    sample_code:Mapped[str]=mapped_column(String(70),unique=True)
    batch_source_id:Mapped[int]=mapped_column(Integer,index=True)
    flour_yield:Mapped[float]=mapped_column(Float)
    moisture:Mapped[float]=mapped_column(Float)
    inspector:Mapped[str]=mapped_column(String(50))
class SyncState(CenterBase):
    __tablename__="sync_state"
    id:Mapped[int]=mapped_column(primary_key=True)
    batch_checkpoint:Mapped[int]=mapped_column(Integer,default=0)
    inspection_checkpoint:Mapped[int]=mapped_column(Integer,default=0)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
