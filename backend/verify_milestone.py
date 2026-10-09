import json
import time
# pyrefly: ignore [missing-import]
import httpx

def test_communication():
    print("\n--- 1. Testing End-to-End Service Communication ---")
    with httpx.Client(timeout=10.0) as client:
        # Check API ready
        ready_resp = client.get("http://localhost:8000/ready")
        print(f"GET /ready: {ready_resp.status_code} - {ready_resp.json()}")
        assert ready_resp.status_code == 200

        # Execute checkout (API -> Orders -> Payments -> DB)
        checkout_payload = {
            "customer_id": "cust_verify_001",
            "items": [
                {"product_id": "item_headphones", "quantity": 1, "price": 149.99},
                {"product_id": "item_cable", "quantity": 2, "price": 15.00}
            ],
            "currency": "USD"
        }
        checkout_resp = client.post("http://localhost:8000/api/v1/checkout", json=checkout_payload)
        print(f"POST /api/v1/checkout: {checkout_resp.status_code} - {checkout_resp.json()}")
        assert checkout_resp.status_code == 200
        order_data = checkout_resp.json()
        assert order_data["status"] == "COMPLETED"
        assert order_data["total_amount"] == 179.99

        # Verify order retrieval
        order_resp = client.get(f"http://localhost:8000/api/v1/orders/{order_data['order_id']}")
        print(f"GET /api/v1/orders/{order_data['order_id']}: {order_resp.status_code} - {order_resp.json()}")
        assert order_resp.status_code == 200
        print(" Service communication verified successfully!")


def test_prometheus_metrics():
    print("\n--- 2. Testing Prometheus Metric Collection ---")
    with httpx.Client(timeout=10.0) as client:
        # Check prometheus targets
        targets_resp = client.get("http://localhost:9090/api/v1/targets")
        assert targets_resp.status_code == 200
        targets = targets_resp.json()["data"]["activeTargets"]
        print(f"Prometheus active targets count: {len(targets)}")
        for t in targets:
            print(f"  Target: {t['labels']['job']} -> {t['health']}")
            assert t["health"] == "up"

        # Query Prometheus for http_requests_total
        query_resp = client.get("http://localhost:9090/api/v1/query", params={"query": "http_requests_total"})
        assert query_resp.status_code == 200
        results = query_resp.json()["data"]["result"]
        print(f"Prometheus collected metric samples count: {len(results)}")
        assert len(results) > 0
        print(" Prometheus metrics verified successfully!")


def test_loki_logs():
    print("\n--- 3. Testing Loki Structured Logs ---")
    time.sleep(2)  # Give Loki batch queue a moment
    with httpx.Client(timeout=10.0) as client:
        # Query Loki ready
        ready_resp = client.get("http://localhost:3100/ready")
        print(f"Loki status: {ready_resp.text.strip()}")
        assert ready_resp.status_code == 200

        # Query Loki labels
        labels_resp = client.get("http://localhost:3100/loki/api/v1/labels")
        print(f"Loki labels: {labels_resp.json()}")
        assert labels_resp.status_code == 200
        labels = labels_resp.json().get("data", [])
        assert "service" in labels

        # Query Loki streams for service=api
        query_resp = client.get(
            "http://localhost:3100/loki/api/v1/query_range",
            params={"query": '{service=~".+"}', "limit": 10}
        )
        print(f"Loki log query response code: {query_resp.status_code}")
        assert query_resp.status_code == 200
        streams = query_resp.json()["data"]["result"]
        print(f"Loki returned log streams count: {len(streams)}")
        assert len(streams) > 0
        print(" Loki logs verified successfully!")


def test_jaeger_traces():
    print("\n--- 4. Testing OpenTelemetry Traces via Jaeger ---")
    time.sleep(2)  # Give batch span processor time to flush
    with httpx.Client(timeout=10.0) as client:
        services_resp = client.get("http://localhost:16686/api/services")
        print(f"Jaeger registered services: {services_resp.json()}")
        assert services_resp.status_code == 200
        services = services_resp.json().get("data", [])
        print(f"Traced services: {services}")
        assert "api" in services or "orders" in services or "payments" in services

        # Query traces for api
        service_to_query = "api" if "api" in services else services[0]
        traces_resp = client.get(
            "http://localhost:16686/api/traces",
            params={"service": service_to_query, "limit": 5}
        )
        assert traces_resp.status_code == 200
        traces = traces_resp.json().get("data", [])
        print(f"Traces captured for '{service_to_query}': {len(traces)}")
        assert len(traces) > 0
        print(" OpenTelemetry traces verified successfully!")


def test_fault_injection_lifecycle():
    print("\n--- 5. Testing Fault Injector Lifecycle & Telemetry ---")
    with httpx.Client(timeout=15.0) as client:
        # List faults
        faults_resp = client.get("http://localhost:8003/faults")
        assert faults_resp.status_code == 200
        faults = faults_resp.json()
        print(f"Registered faults count: {len(faults)}")
        assert len(faults) >= 5

        # 1. Activate Dependency Timeout Fault
        print("\n--> Activating Fault: dependency_timeout (delay=5s)")
        act_resp = client.post("http://localhost:8003/faults/dependency_timeout/activate", json={"params": {"delay_sec": 5.0}})
        print(f"Activation response: {act_resp.json()}")
        assert act_resp.status_code == 200

        # Attempt checkout (should fail with 504 Gateway Timeout because payments delays past 2.5s orders timeout)
        checkout_payload = {
            "customer_id": "cust_fault_test",
            "items": [{"product_id": "item_fail", "quantity": 1, "price": 10.0}],
            "currency": "USD"
        }
        fail_resp = client.post("http://localhost:8000/api/v1/checkout", json=checkout_payload)
        print(f"Checkout during dependency_timeout fault: HTTP {fail_resp.status_code}")
        assert fail_resp.status_code in [502, 504]

        # Deactivate dependency timeout
        deact_resp = client.post("http://localhost:8003/faults/dependency_timeout/deactivate")
        print(f"Deactivation response: {deact_resp.json()}")
        assert deact_resp.status_code == 200

        # 2. Activate DB Pool Exhaustion Fault
        print("\n--> Activating Fault: db_pool_exhaustion")
        pool_act = client.post("http://localhost:8003/faults/db_pool_exhaustion/activate")
        print(f"Pool activation response: {pool_act.json()}")
        assert pool_act.status_code == 200

        # Attempt to create or fetch orders (should fail with 503 Service Unavailable / Pool exhausted)
        pool_fail = client.get("http://localhost:8000/api/v1/orders")
        print(f"Orders request during db_pool_exhaustion: HTTP {pool_fail.status_code}")
        assert pool_fail.status_code in [502, 503]

        # Deactivate pool exhaustion
        pool_deact = client.post("http://localhost:8003/faults/db_pool_exhaustion/deactivate")
        print(f"Pool deactivation response: {pool_deact.json()}")
        assert pool_deact.status_code == 200

        # Reset all faults to ensure clean baseline
        reset_resp = client.post("http://localhost:8003/faults/reset")
        print(f"Reset response: {reset_resp.json()}")
        assert reset_resp.status_code == 200

        # Verify service recovered
        recovery_resp = client.get("http://localhost:8000/api/v1/orders")
        print(f"Orders request after deactivation: HTTP {recovery_resp.status_code}")
        assert recovery_resp.status_code == 200
        print(" Fault lifecycle & expected failure telemetry verified successfully!")


if __name__ == "__main__":
    test_communication()
    test_prometheus_metrics()
    test_loki_logs()
    test_jaeger_traces()
    test_fault_injection_lifecycle()
    print("\n ALL VERIFICATION CHECKS PASSED PERFECTLY! \n")
