from datetime import datetime
from pydantic import BaseModel, Field


class PaymentRequest(BaseModel):
    order_id: int
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    payment_method: str = Field(default="credit_card")
    customer_id: str


class PaymentResponse(BaseModel):
    payment_id: str
    order_id: int
    amount: float
    currency: str
    status: str
    transaction_id: str
    timestamp: str


class FaultState(BaseModel):
    fault_id: str
    active: bool
    details: dict = {}
