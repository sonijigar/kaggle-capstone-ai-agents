from pydantic import BaseModel, Field

class FlightContext(BaseModel):
    carrier: str = Field(description='OP_UNIQUE_CARRIER, e.g. "DL"')
    flight_no: str | None = Field(default=None, description="Flight number, if provided")
    origin: str = Field(description='Origin airport code, e.g. "ORD"')
    dest: str = Field(description='Destination airport code, e.g. "ATL"')
    day_of_week: int = Field(description="Day of week (1=Monday ... 7=Sunday)")
    dep_time_blk: str = Field(description='Departure time block, e.g. "0700-0759"')
    distance: float | None = Field(default=None, description="Distance in miles, optional")

class RiskAssessment(BaseModel):
    p_delay15: float = Field(description="Probability of 15+ minute delay (0..1)")
    p_cancel: float = Field(description="Probability of cancellation (0..1)")
    confidence: float = Field(description="Confidence of assessment (0..1)")
    dominant_cause: str = Field(default="historical", description="Primary cause of risk")
    explanation: str = Field(description="Textual explanation of the risk assessment")
