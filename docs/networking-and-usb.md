# Printers: networking and USB

Set the printer in the add-on's **Printer URI** option. The transport is inferred from the scheme.

## Network printers (recommended)

```
tcp://<printer-ip>:9100
```

Give the printer a **static IP or a DHCP reservation** so the URI stays valid across reboots.
labelito also queries the printer over **SNMP** for live status — loaded media (which backs the
pre-flight media-mismatch guard), errors, and the lifetime label counter. No extra configuration
is needed; SNMP is read-only and never touches the print path.

## USB printers

```
usb://<vendorId>:<productId>
```

For a Brother QL-810W that is typically `usb://0x04f9:0x209c`. Find your ids one of these ways:

- **Home Assistant**: Settings → System → Hardware → (⋮) All Hardware, look for the Brother device.
- **Shell** (SSH/Terminal add-on): `lsusb` — the Brother line shows `ID <vendorId>:<productId>`.

The add-on requests USB device access automatically (`usb: true` in the manifest). Live status
over USB is more limited than SNMP and briefly claims the single USB handle, so Home Assistant
polls it less aggressively. See the upstream
[known limitations](https://github.com/chiva/labelito/blob/main/docs/known-limitations.md).

## Model mismatch

labelito cross-checks the configured `model` against what the printer reports and flags a mismatch
(surfaced as a fault in Home Assistant). If you change printers, update `model` to match.
