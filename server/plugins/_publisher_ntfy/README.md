## Overview

A plugin to publish a notification via the NTFY gateway. Enable sending notifications via <a target="_blank" href="https://ntfy.sh/">NTFY</a>. Supports authentication. 

### Usage

- Go to settings and fill in relevant details.

## Reverse proxy / tunnel authentication

If your ntfy instance sits behind a reverse proxy or tunnel that authenticates requests itself (Pangolin, Tailscale, Cloudflare Access, ...), the proxy usually expects its own credential *in addition to* any ntfy token. Two optional settings cover this.

Both are independent of `NTFY_TOKEN` / `NTFY_USER` / `NTFY_PASSWORD` — those still control authentication against ntfy itself and are unaffected.

### Custom header

Sends an extra HTTP header with the request. Prefer this over the query string for anything secret.

| Setting | Sample value |
|---|---|
| `NTFY_CUSTOMHEADER_NAME` | `X-Proxy-Token` |
| `NTFY_CUSTOMHEADER_VALUE` | `p_abc123.def456ghi789` |

Other common examples:

| Proxy | Header name | Header value |
|---|---|---|
| Pangolin | `P-Token` | `tokenId.tokenValue` |
| Cloudflare Access | `CF-Access-Client-Id` | `abc123.access` |
| Generic bearer gateway | `X-Auth-Token` | `eyJhbGciOi...` |

Both settings must be filled in — setting only one of them does nothing.

The header value must be a valid HTTP header value: plain ASCII, no newlines, and no leading or trailing whitespace. A trailing newline pasted in from a text file is the most common mistake and the plugin will report it as an invalid custom header.

If the header name collides with one the plugin has already set for this request (`Title`, `Actions`, `Priority`, `Tags`, plus `Authorization` when an ntfy token or username/password is configured), the custom header is skipped and a warning is logged, so it can never clobber your ntfy credentials. With no ntfy credentials configured there is no `Authorization` header to clash with, so you are free to use that name for the proxy.

### URL query string

Appends a query string to the ntfy request URL, for proxies that authenticate via a query parameter instead of a header.

| Setting | Sample value |
|---|---|
| `NTFY_URL_QUERY_STRING` | `p_token=tokenId.tokenValue` |

A leading `?` is optional — both `p_token=...` and `?p_token=...` work. Multiple parameters are supported: `p_token=abc&source=netalertx`.

Note that query strings are commonly recorded in proxy and web-server access logs, so for secrets the custom header above is the safer option. The plugin redacts the query string from any error message it logs.
