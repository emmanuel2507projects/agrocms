from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base


class Grower(Base):
    __tablename__ = "growers"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    licence_no = Column(String, unique=True, nullable=False)
    region = Column(String, nullable=False)
    status = Column(String, default="active")   # active, suspended, inactive
    contact_email = Column(String)
    licence_expiry = Column(Date)

    paddocks = relationship("Paddock", back_populates="grower")
    contracts = relationship("Contract", back_populates="grower")


class Paddock(Base):
    __tablename__ = "paddocks"
    id = Column(Integer, primary_key=True)
    grower_id = Column(Integer, ForeignKey("growers.id"), nullable=False)
    name = Column(String, nullable=False)
    area_ha = Column(Float, nullable=False)
    soil_type = Column(String)
    geojson_coords = Column(Text)   # JSON [[lon,lat], ...]
    lat = Column(Float)
    lon = Column(Float)

    grower = relationship("Grower", back_populates="paddocks")
    sowing_records = relationship("SowingRecord", back_populates="paddock")
    harvest_records = relationship("HarvestRecord", back_populates="paddock")
    pesticide_applications = relationship("PesticideApplication", back_populates="paddock")


class Contract(Base):
    __tablename__ = "contracts"
    id = Column(Integer, primary_key=True)
    grower_id = Column(Integer, ForeignKey("growers.id"), nullable=False)
    season = Column(String, nullable=False)             # "2022-23", "2023-24", "2024-25"
    variety = Column(String, nullable=False)             # "Norman", "Latex"
    area_contracted_ha = Column(Float, nullable=False)
    price_per_kg = Column(Float, nullable=False)

    grower = relationship("Grower", back_populates="contracts")
    sowing_records = relationship("SowingRecord", back_populates="contract")
    harvest_records = relationship("HarvestRecord", back_populates="contract")
    crop_costs = relationship("CropCost", back_populates="contract")


class SowingRecord(Base):
    __tablename__ = "sowing_records"
    id = Column(Integer, primary_key=True)
    paddock_id = Column(Integer, ForeignKey("paddocks.id"), nullable=False)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    sow_date = Column(Date, nullable=False)
    seed_rate_kg_ha = Column(Float)
    status = Column(String, default="harvested")        # sown, growing, harvested
    sowing_declaration_lodged = Column(Integer, default=1)   # 1=yes, 0=no

    paddock = relationship("Paddock", back_populates="sowing_records")
    contract = relationship("Contract", back_populates="sowing_records")


class HarvestRecord(Base):
    __tablename__ = "harvest_records"
    id = Column(Integer, primary_key=True)
    paddock_id = Column(Integer, ForeignKey("paddocks.id"), nullable=False)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    harvest_date = Column(Date, nullable=False)
    yield_kg_ha = Column(Float)
    morphine_content_pct = Column(Float)
    loss_kg = Column(Float, default=0.0)
    loss_reason = Column(String)
    harvest_reconciliation_submitted = Column(Integer, default=1)   # 1=yes, 0=no

    paddock = relationship("Paddock", back_populates="harvest_records")
    contract = relationship("Contract", back_populates="harvest_records")


class PesticideApplication(Base):
    __tablename__ = "pesticide_applications"
    id = Column(Integer, primary_key=True)
    paddock_id = Column(Integer, ForeignKey("paddocks.id"), nullable=False)
    applied_date = Column(Date, nullable=False)
    chemical_name = Column(String, nullable=False)
    rate_L_ha = Column(Float)
    withholding_days = Column(Integer)
    applicator_id = Column(String)

    paddock = relationship("Paddock", back_populates="pesticide_applications")


class CropCost(Base):
    __tablename__ = "crop_costs"
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    cost_type = Column(String)   # seed, fertiliser, pesticide, contractor, irrigation, harvest_levy, admin
    amount = Column(Float)
    recorded_date = Column(Date)

    contract = relationship("Contract", back_populates="crop_costs")
