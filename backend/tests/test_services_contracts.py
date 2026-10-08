import importlib.util
import os
import sys
import pytest
from pydantic import ValidationError

def load_module_from_path(module_name: str, file_path: str):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

api_models = load_module_from_path(
    "api_models",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../demo-app/api/models.py")),
)
payments_models = load_module_from_path(
    "payments_models",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../demo-app/payments/models.py")),
)
orders_models = load_module_from_path(
    "orders_models",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../demo-app/orders/models.py")),
)


def test_checkout_request_validation():
    valid = api_models.CheckoutRequest(
        customer_id="cust_test_101",
        items=[
            api_models.CheckoutItem(product_id="prod_01", quantity=2, price=29.99)
        ],
        currency="USD",
    )
    assert valid.customer_id == "cust_test_101"
    assert len(valid.items) == 1
    assert valid.items[0].price == 29.99


def test_checkout_request_invalid_quantity():
    with pytest.raises(ValidationError):
        api_models.CheckoutRequest(
            customer_id="cust_test_102",
            items=[
                api_models.CheckoutItem(product_id="prod_01", quantity=0, price=29.99)  # quantity must be > 0
            ],
            currency="USD",
        )


def test_alertmanager_webhook_payload():
    payload = api_models.AlertmanagerWebhookPayload(
        status="firing",
        receiver="sherlog-webhook",
        alerts=[
            {
                "status": "firing",
                "labels": {
                    "alertname": "DbPoolExhausted",
                    "severity": "critical",
                    "service": "orders",
                },
                "annotations": {
                    "summary": "Database connection pool exhausted",
                },
            }
        ],
    )
    assert payload.status == "firing"
    assert len(payload.alerts) == 1
    assert payload.alerts[0].labels["alertname"] == "DbPoolExhausted"


def test_payment_request_model():
    req = payments_models.PaymentRequest(
        order_id=42,
        amount=199.95,
        currency="USD",
        payment_method="credit_card",
        customer_id="cust_test_42",
    )
    assert req.order_id == 42
    assert req.amount == 199.95


def test_order_create_model():
    order = orders_models.OrderCreate(
        customer_id="cust_500",
        currency="USD",
        items=[
            orders_models.OrderItemCreate(product_id="prod_item_99", quantity=3, price=10.0)
        ],
    )
    assert order.customer_id == "cust_500"
    assert len(order.items) == 1
