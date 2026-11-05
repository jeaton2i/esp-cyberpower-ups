"""
Probe a USB HID UPS directly from the host OS, bypassing any ESP32 USB-host
quirks entirely. Prints the model/VID/PID and dumps every candidate HID
FEATURE report's raw bytes.

Why this exists: CyberPower (and other vendors') UPS firmware varies a lot
in how it exposes data over USB HID. Some models populate the standard HID
Power Device usages (Voltage, PercentLoad, etc.) that most ESPHome/NUT
drivers look for; others (like the CP1500PFCLCDa this was built for) don't
populate those at all and instead expose everything at fixed report IDs
with vendor-specific framing. The only reliable way to know which case a
given unit falls into is to probe it directly like this.

Usage:
    pip install hidapi      # one-time, provides the `hid` module + native lib
    python probe_ups.py                 # auto-detect any CyberPower (VID 0x0764) device
    python probe_ups.py 0x0764 0x0601   # probe a specific VID:PID

Workflow for a new/unknown UPS model:
    1. Plug it into this PC via its USB-B monitoring port.
    2. Run this script. Note the model string and which report IDs return
       non-trivial (non-zero / plausible) data.
    3. Run probe_status.py, unplug the UPS from the wall, run it again,
       plug back in, run it again. Diff the two dumps — whichever bytes
       flip are your AC-present/on-battery/charging status bits.
    4. Cross-check voltage/power readings against the unit's own nameplate
       rating sticker (nominal voltage, VA/W) to confirm scale/offset.
    5. Once confident, add the mapping to ups-fork/components/cyberpower_ups/
       cyberpower_ups.h's poll_ups_data_() — branch on get_product_id() if
       supporting multiple models from one firmware image.
"""
import sys
import hid

CYBERPOWER_VID = 0x0764

def find_device(vid=None, pid=None):
    devs = hid.enumerate()
    if vid is not None:
        devs = [d for d in devs if d['vendor_id'] == vid and (pid is None or d['product_id'] == pid)]
    else:
        devs = [d for d in devs if d['vendor_id'] == CYBERPOWER_VID]
    return devs

def main():
    vid = pid = None
    if len(sys.argv) >= 2:
        vid = int(sys.argv[1], 0)
    if len(sys.argv) >= 3:
        pid = int(sys.argv[2], 0)

    devs = find_device(vid, pid)
    if not devs:
        print("No matching device found.")
        print("All connected HID devices:")
        for d in hid.enumerate():
            print(f"  VID={d['vendor_id']:#06x} PID={d['product_id']:#06x} "
                  f"{d.get('manufacturer_string')!r} {d.get('product_string')!r}")
        sys.exit(1)

    info = devs[0]
    print(f"Found: {info.get('manufacturer_string')} {info.get('product_string')}")
    print(f"  VID={info['vendor_id']:#06x} PID={info['product_id']:#06x} "
          f"serial={info.get('serial_number')}")
    print()

    h = hid.device()
    h.open_path(info['path'])
    h.set_nonblocking(0)

    # Broad sweep — real UPS report IDs we've seen so far all land in 1-45.
    candidate_ids = list(range(1, 46))

    for rid in candidate_ids:
        try:
            data = h.get_feature_report(rid, 65)
            if data:
                hexstr = ' '.join(f'{b:02x}' for b in data)
                print(f"report {rid:3d} (0x{rid:02x}): OK  len={len(data):3d}  bytes= {hexstr}")
        except Exception as e:
            pass  # most IDs won't exist on any given device; skip quietly

    h.close()

if __name__ == '__main__':
    main()
