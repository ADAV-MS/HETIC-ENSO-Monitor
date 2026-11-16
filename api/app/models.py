from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from .db import Base

class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    version = Column(String, nullable=False)
    extracted_at = Column(DateTime, default=lambda: datetime.now(UTC))

    imports = relationship("Import", back_populates="source")

class Indice(Base):
    __tablename__ = "indices"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    label = Column(String, nullable=False)
    unit = Column(String, nullable=False)

    observations = relationship("Observation", back_populates="indice")

class Import(Base):
    __tablename__ = "imports"
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    imported_at = Column(DateTime, default=lambda: datetime.now(UTC))
    row_count = Column(Integer, nullable=False)
    checksum = Column(String, nullable=True)

    source = relationship("Source", back_populates="imports")
    observations = relationship("Observation", back_populates="import_record")

class Observation(Base):
    __tablename__ = "observations"
    id = Column(Integer, primary_key=True, index=True)
    import_id = Column(Integer, ForeignKey("imports.id"), nullable=False)
    index_id = Column(Integer, ForeignKey("indices.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    value = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("index_id", "date", name="uq_observation_index_date"),
    )

    import_record = relationship("Import", back_populates="observations")
    indice = relationship("Indice", back_populates="observations")