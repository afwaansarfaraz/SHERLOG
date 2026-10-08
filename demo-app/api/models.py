from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CheckoutItem(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0)


class CheckoutRequest(BaseModel):
    customer_id: str
    items: List[CheckoutItem]
    currency: str = Field(default="USD", max_length=3)


class CheckoutResponse(BaseModel):
    order_id: int
    customer_id: str
    total_amount: float
    currency: str
    status: str
    items: List[dict] = []
    message: str


class AlertmanagerAlert(BaseModel):
    status: str
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None


class AlertmanagerWebhookPayload(BaseModel):
    version: Optional[str] = None
    groupKey: Optional[str] = None
    status: str
    receiver: Optional[str] = None
    alerts: List[AlertmanagerAlert] = []
    commonLabels: Dict[str, str] = {}
    commonAnnotations: Dict[str, str] = {}
