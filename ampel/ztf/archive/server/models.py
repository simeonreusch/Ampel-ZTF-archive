
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class AlertChunk(BaseModel):
    resume_token: str
    chunks_remaining: int
    alerts: List[Dict[str, Any]]

class StreamDescription(BaseModel):
    resume_token: str
    chunk_size: int
    chunks: int

class ConeConstraint(BaseModel):
    ra: float = Field(..., description="Right ascension of field center in degrees (J2000)")
    dec: float = Field(..., description="Declination of field center in degrees (J2000)")
    radius: float = Field(..., gt=0, lt=180, description="Radius of search cone in degrees")

class TimeConstraint(BaseModel):
    lt: Optional[float] = Field(None)
    gt: Optional[float] = Field(None)

class AlertQuery(BaseModel):
    cone: Optional[ConeConstraint] = None
    jd: TimeConstraint = TimeConstraint()
    programid: Optional[int] = None
    chunk_size: int = Field(
        100,  gt=0, lte=10000, description="Number of alerts per chunk"
    )