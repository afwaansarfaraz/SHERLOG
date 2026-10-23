# Runbook: DNS, Network Connectivity, and TLS Failures
- **Runbook ID:** RB-012
- **Category:** DNS, network connectivity, and TLS failures
- **Version:** 1.0.0
- **Applicable Services:** All services, Docker bridge network, reverse proxies, ingress
- **Keywords:** dns failure, cert expired, tls handshake, ssl error, connection refused, network partition, resolve error, eai_again

## Symptoms
- Interservice network calls failing with `NameResolutionError`, `socket.gaierror: [Errno -3] Temporary failure in name resolution`, or `EAI_AGAIN`.
- Client requests rejected with TLS errors: `SSL: CERTIFICATE_VERIFY_FAILED`, `certificate has expired`, or `handshake_failure`.
- Intermittent TCP connection resets (`ECONNRESET`) or connection refused (`ECONNREFUSED`) between Docker bridge network containers.
- Prometheus scraping targets showing state `DOWN` due to dial timeout or resolution failure.

## Required Observability Signals
- **Metrics:** `probe_success{job="blackbox"}`, `dns_resolution_duration_seconds`, `ssl_certificate_expiry_days`
- **Logs:** Loki query `{service=~".*"} |= "CERTIFICATE_VERIFY_FAILED"` or `{service=~".*"} |= "getaddrinfo failed"`
- **Traces:** Traces failing at connection establishment with zero duration on downstream request execution spans.

## Diagnostic Steps
1. Test DNS resolution from within the failing container:
   ```bash
   docker exec -it sherlog-api nslookup postgres
   docker exec -it sherlog-api ping -c 2 payments
   ```
2. Verify TLS certificate validity, chain verification, issuer, and expiration date:
   ```bash
   openssl s_client -connect api.sherlog.local:443 -servername api.sherlog.local -verify_hostname api.sherlog.local -verify_return_error < /dev/null | openssl x509 -noout -issuer -dates -subject
   ```
3. Check Docker network bridge state and inspect subnet IP allocations:
   ```bash
   docker network inspect sherlog_default
   ```
4. Verify host `/etc/resolv.conf` or Docker daemon DNS configuration settings (e.g. `8.8.8.8`, `1.1.1.1` or internal Docker embedded DNS `127.0.0.11`).

## Root-Cause Hypotheses & Validation Evidence
- **Hypothesis 1: Expired or Untrusted TLS/SSL Certificate**
  - *Evidence Needed:* OpenSSL output shows `notAfter` date is in the past, or client trust store lacks the intermediate Certificate Authority (CA) root.
- **Hypothesis 2: Embedded Docker DNS Daemon (`127.0.0.11`) Hang or Network Loop**
  - *Evidence Needed:* Service container cannot resolve other container service names by hostname despite containers residing on the exact same network.
- **Hypothesis 3: Port Exhaustion or Security Group / Firewall Drop**
  - *Evidence Needed:* SYN packets sent but no SYN-ACK returned; `dmesg` reports `nf_conntrack: table full, dropping packet`.

## Contradictory Evidence & Alternative Explanations
- If DNS resolves the correct IP within 5ms and ping succeeds, but HTTP fails with 404 or 500, the network layer is healthy; investigate application routing or errors.
- If TLS certificate is valid for 90 days and matches hostname, verify client clock synchronization (NTP drift causing invalid token or cert validation errors).

## Safe Mitigation & Rollback Guidance
- **Renew Certificate:** Trigger automated renewal; use standard `certbot renew` by default, or scope to the affected certificate if forced renewal is strictly needed:
  ```bash
  # Standard renewal by default:
  certbot renew
  # Only if forced renewal is required for an affected cert (avoid repeated forced attempts):
  # certbot renew --cert-name api.sherlog.local --force-renewal
  ```
- **Restart Docker Network / Daemon:** Recreate the network or restart the container to refresh DNS bindings:
  ```bash
  docker network disconnect sherlog_default sherlog-api
  docker network connect sherlog_default sherlog-api
  docker restart sherlog-api
  ```
- **Explicit Host Mapping:** As a temporary emergency fallback, add static host-to-IP mappings in `docker-compose.yml` (`extra_hosts`).
- **Flush DNS Cache:** Restart CoreDNS or systemd-resolved on host nodes.

## Verification Steps & Escalation Criteria
- **Verification:** DNS resolution returns valid IPs consistently within < 5ms, TLS handshake succeeds without warnings, and interservice connectivity is fully restored.
- **Escalation Criteria:** If the failure is due to upstream cloud provider VPC routing tables or global registrar DNS outage, alert Infrastructure Network Operations (P1).
