# mindX Security Vulnerabilities

**Source:** GitHub Dependabot  
**Last Audited:** 2026-04-03  
**Total:** 30 vulnerabilities (8 high, 10 medium, 12 low)  

## Summary by Severity

| Severity | Count | Action |
|----------|-------|--------|
| **Critical** | 0 | — |
| **High** | 8 | Upgrade or mitigate |
| **Medium** | 10 | Monitor, upgrade when stable |
| **Low** | 12 | Acceptable risk, track |

## Vulnerabilities by Package

### aiohttp (18 vulnerabilities)

**Installed:** 3.13.5  
**Impact:** Core HTTP client used by Ollama API, vLLM handler, inference discovery, heartbeat  

| Severity | Summary | Mitigation |
|----------|---------|------------|
| **HIGH** | HTTP parser auto_decompress zip bomb | mindX only calls trusted local Ollama — low external exposure |
| **MEDIUM** | Duplicate Host headers accepted | Internal-only connections (localhost) |
| **MEDIUM** | Multipart header size bypass | No file uploads from untrusted sources |
| **MEDIUM** | DoS through chunked messages | Rate limiting via API access gate |
| **MEDIUM** | DoS through large payloads | Apache proxy limits request size |
| **MEDIUM** | DoS when bypassing asserts | Rate limiting active |
| **MEDIUM** | Unlimited trailer headers | Internal connections only |
| **MEDIUM** | UNC SSRF on Windows | N/A — Linux VPS |
| **LOW** | CRLF injection in multipart | No multipart to untrusted endpoints |
| **LOW** | Cookie parser warning storm | No external cookie handling |
| **LOW** | DNS cache unbounded | Short-lived connections |
| **LOW** | Cookie/auth leak on redirect | No cross-origin redirects |
| **LOW** | Late size enforcement multipart | No untrusted multipart uploads |
| **LOW** | Null bytes in response headers | Internal connections only |
| **LOW** | HTTP response splitting via \\r | Internal connections only |
| **LOW** | Unicode match groups in regexes | Internal protocol only |
| **LOW** | Unicode header value parsing | Internal protocol only |
| **LOW** | Brute-force static file path leak | No static file serving via aiohttp |

**Risk Assessment:** LOW — aiohttp is used only for localhost connections to Ollama and internal services. No untrusted external input reaches aiohttp directly. Apache handles all external traffic.

**Action:** Upgrade when 3.14+ is released. Current mitigations (localhost-only, rate limiting, Apache proxy) are sufficient.

### cryptography (2 vulnerabilities)

**Installed:** 46.0.6  

| Severity | Summary | Mitigation |
|----------|---------|------------|
| **HIGH** | Subgroup attack on SECT curves | mindX uses AES-256-GCM + HKDF-SHA512, not SECT curves |
| **LOW** | Incomplete DNS name constraint enforcement | No certificate validation against DNS constraints |

**Risk Assessment:** LOW — BANKON Vault uses AES-256-GCM + HKDF-SHA512, not elliptic curve operations affected by this vulnerability.

**Action:** Monitor. Upgrade if ECDSA operations are added for on-chain signing.

### urllib3 (2 vulnerabilities)

**Installed:** 2.6.3  

| Severity | Summary | Mitigation |
|----------|---------|------------|
| **HIGH** | Decompression-bomb bypass on redirects | No streaming API used with untrusted URLs |
| **HIGH** | Streaming API highly compressed data | No streaming from untrusted sources |

**Risk Assessment:** LOW — urllib3 is used by `requests` library for outbound HTTP only. All outbound calls go to trusted APIs (Gemini, Groq) with known response formats.

**Action:** Upgrade when available.

### pyOpenSSL (2 vulnerabilities)

**Installed:** Not directly installed (transitive dependency)  

| Severity | Summary | Mitigation |
|----------|---------|------------|
| **HIGH** | DTLS cookie callback buffer overflow | DTLS not used |
| **LOW** | TLS connection bypass via callback exception | Apache handles TLS, not Python |

**Risk Assessment:** NEGLIGIBLE — pyOpenSSL is a transitive dependency not directly used. Apache handles all TLS termination.

### PyJWT (1 vulnerability)

**Installed:** 2.12.1  

| Severity | Summary | Mitigation |
|----------|---------|------------|
| **HIGH** | Accepts unknown `crit` header extensions | mindX uses wallet signatures, not JWT for auth |

**Risk Assessment:** NEGLIGIBLE — JWT is not used for authentication. Session tokens are UUID-based, stored in vault.

### orjson (1 vulnerability)

**Installed:** Not directly installed (transitive)  

| Severity | Summary | Mitigation |
|----------|---------|------------|
| **HIGH** | No recursion limit for deeply nested JSON | Not used for untrusted input parsing |

**Risk Assessment:** LOW — orjson is optional/transitive. Standard `json` library is the primary parser.

### python-multipart (1 vulnerability)

**Installed:** 0.0.22  

| Severity | Summary | Mitigation |
|----------|---------|------------|
| **HIGH** | Arbitrary file write via non-default config | Default config used. No custom file write paths. |

**Risk Assessment:** LOW — Default configuration. API access gate blocks unauthenticated file uploads.

### requests (1 vulnerability)

**Installed:** 2.33.1  

| Severity | Summary | Mitigation |
|----------|---------|------------|
| **MEDIUM** | Insecure temp file reuse in extract_zipped_paths | No ZIP extraction from untrusted sources |

**Risk Assessment:** NEGLIGIBLE — No ZIP processing in mindX.

### diskcache (1 vulnerability)

**Installed:** Transitive dependency  

| Severity | Summary | Mitigation |
|----------|---------|------------|
| **MEDIUM** | Unsafe pickle deserialization | No diskcache usage with untrusted data |

**Risk Assessment:** NEGLIGIBLE — Not directly used.

### PyNaCl (1 vulnerability)

**Installed:** Transitive dependency  

| Severity | Summary | Mitigation |
|----------|---------|------------|
| **MEDIUM** | libsodium incomplete disallowed inputs | No direct libsodium usage |

**Risk Assessment:** NEGLIGIBLE — Transitive dependency.

## Architecture Mitigations

mindX's production architecture provides defense-in-depth:

1. **Apache reverse proxy** — handles all external traffic, TLS termination, request size limits
2. **API access gate** — all non-public routes require `X-Session-Token` or `Authorization: Bearer`
3. **Localhost-only binding** — uvicorn listens on `127.0.0.1:8000`, not exposed to internet
4. **BANKON Vault** — credentials encrypted AES-256-GCM, never in plaintext
5. **Tool access control** — BDI agent checks `allowed_agents` before tool execution
6. **Guardian ECDSA** — real wallet signature challenge-response for agent verification
7. **Rate limiting** — per-endpoint rate limits via security middleware
8. **Resource Governor** — prevents OOM by auto-adjusting resource appetite
9. **PostgreSQL** — pgvector data isolated from web-facing code

## Recommended Upgrades

| Package | Current | Action | Priority |
|---------|---------|--------|----------|
| aiohttp | 3.13.5 | Upgrade when 3.14+ available | Medium |
| cryptography | 46.0.6 | Monitor for 47.x | Low |
| urllib3 | 2.6.3 | Upgrade when patch available | Low |
| python-multipart | 0.0.22 | Upgrade to 0.0.23+ if available | Low |

## Conclusion

**Overall risk: LOW.** The 8 high-severity vulnerabilities are all in packages used only for internal localhost connections or as transitive dependencies not directly invoked. Apache proxy, API access gate, and localhost-only binding provide effective mitigation. No critical vulnerabilities exist. The most impactful upgrade path is aiohttp when 3.14+ is released.
