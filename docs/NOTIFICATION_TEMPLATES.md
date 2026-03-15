# Notification Text Templates

> Customize how devices and events appear in **text** notifications (email previews, push notifications, Apprise messages).

By default, NetAlertX formats each device as a vertical list of `Header: Value` pairs. Text templates let you define a **single-line format per device** using `{FieldName}` placeholders — ideal for mobile notification previews and high-volume alerts.

HTML email tables are **not affected** by these templates.

## Quick Start

1. Go to **Settings → Notification Processing**.
2. Set a template string for the section you want to customize, e.g.:
   - **Text Template: New Devices** → `{devName} ({eve_MAC}) - {eve_IP}`
3. Save. The next notification will use your format.

**Before (default):**
```
🆕 New devices
---------
devName: 	    MyPhone
eve_MAC: 	    aa:bb:cc:dd:ee:ff
devVendor: 	    Apple
eve_IP: 	    192.168.1.42
eve_DateTime: 	2025-01-15 10:30:00
eve_EventType:  New Device
devComments:
```

**After (with template `{devName} ({eve_MAC}) - {eve_IP}`):**
```
🆕 New devices
---------
MyPhone (aa:bb:cc:dd:ee:ff) - 192.168.1.42
```

## Settings Reference

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `NTFPRCS_TEXT_SECTION_HEADERS` | Boolean | `true` | Show/hide section titles (e.g. `🆕 New devices \n---------`). |
| `NTFPRCS_TEXT_TEMPLATE_new_devices` | String | *(empty)* | Template for new device rows. |
| `NTFPRCS_TEXT_TEMPLATE_down_devices` | String | *(empty)* | Template for down device rows. |
| `NTFPRCS_TEXT_TEMPLATE_down_reconnected` | String | *(empty)* | Template for reconnected device rows. |
| `NTFPRCS_TEXT_TEMPLATE_events` | String | *(empty)* | Template for event rows. |
| `NTFPRCS_TEXT_TEMPLATE_plugins` | String | *(empty)* | Template for plugin event rows. |

When a template is **empty**, the section uses the original vertical `Header: Value` format (full backward compatibility).

## Template Syntax

Use `{FieldName}` to insert a value from the notification data. Field names are **case-sensitive** and must match the column names exactly.

```
{devName} ({eve_MAC}) connected at {eve_DateTime}
```

- No loops, conditionals, or nesting — just simple string replacement.
- If a `{FieldName}` does not exist in the data, it is left as-is in the output (safe failure). For example, `{NonExistent}` renders literally as `{NonExistent}`.

## Variable Availability by Section

All four device sections (`new_devices`, `down_devices`, `down_reconnected`, `events`) share the same unified field names.

### `new_devices`, `down_devices`, `down_reconnected`, and `events`

| Variable | Description |
|----------|-------------|
| `{devName}` | Device display name |
| `{eve_MAC}` | Device MAC address |
| `{devVendor}` | Device vendor/manufacturer |
| `{eve_IP}` | Device IP address |
| `{eve_DateTime}` | Event timestamp |
| `{eve_EventType}` | Type of event (e.g. `New Device`, `Connected`, `Device Down`) |
| `{devComments}` | Device comments |

**Example (new_devices/events):** `{devName} ({eve_MAC}) - {eve_IP} [{eve_EventType}]`

**Example (down_devices):** `{devName} ({eve_MAC}) {devVendor} - went down at {eve_DateTime}`

**Example (down_reconnected):** `{devName} ({eve_MAC}) reconnected at {eve_DateTime}`

### `plugins`

| Variable | Description |
|----------|-------------|
| `{Plugin}` | Plugin code name |
| `{Object_PrimaryId}` | Primary identifier of the object |
| `{Object_SecondaryId}` | Secondary identifier |
| `{DateTimeChanged}` | Timestamp of change |
| `{Watched_Value1}` | First watched value |
| `{Watched_Value2}` | Second watched value |
| `{Watched_Value3}` | Third watched value |
| `{Watched_Value4}` | Fourth watched value |
| `{Status}` | Plugin event status |

**Example:** `{Plugin}: {Object_PrimaryId} - {Status}`

## Section Headers Toggle

Set **Text Section Headers** (`NTFPRCS_TEXT_SECTION_HEADERS`) to `false` to remove the section title separators from text notifications. This is useful when you want compact output without the `🆕 New devices \n---------` banners.
