"""
Re-poll a specific set of HID FEATURE reports on a UPS — meant to be run
once with the UPS on battery (unplugged from the wall) and once on AC
(plugged back in), so you can diff the two dumps and see exactly which
bytes/bits change. That's how we confirmed the CP1500PFCLCDa's status
byte (report 0x0b): 0x04 on battery vs 0x03 on AC -> bit0=AC present,
bit2=on battery, bit1=charging.

Usage:
    python probe_status.py                 # auto-detect any CyberPower (VID 0x0764) device
    python probe_status.py 0x0764 0x0601   # probe a specific VID:PID
    python probe_status.py 0x0764 0x0601 11 15 18 19 10 8   # custom report ID list

Run it, toggle AC, run it again, compare.
"""
import sys
import hid

CYBERPOWER_VID = 0x0764
DEFAULT_REPORT_IDS = [11, 15, 18, 19, 10, 8]  # status, input V, output V, load%, batt V, batt%+runtime

def main():
    args = sys.argv[1:]
    vid = int(args[0], 0) if len(args) >= 1 else None
    pid = int(args[1], 0) if len(args) >= 2 else None
    report_ids = [int(a, 0) for a in args[2:]] if len(args) >= 3 else DEFAULT_REPORT_IDS

    devs = hid.enumerate()
    if vid is not None:
        devs = [d for d in devs if d['vendor_id'] == vid and (pid is None or d['product_id'] == pid)]
    else:
        devs = [d for d in devs if d['vendor_id'] == CYBERPOWER_VID]

    if not devs:
        print("Device not found")
        sys.exit(1)

    h = hid.device()
    h.open_path(devs[0]['path'])
    h.set_nonblocking(0)

    print(f"{devs[0].get('product_string')} — report snapshot:")
    for rid in report_ids:
        try:
            data = h.get_feature_report(rid, 65)
            hexstr = ' '.join(f'{b:02x}' for b in data)
            binstr = f"{data[1]:08b}" if len(data) > 1 else ""
            print(f"  report {rid:3d} (0x{rid:02x}): {hexstr}   [{binstr}]")
        except Exception as e:
            print(f"  report {rid:3d} (0x{rid:02x}): FAILED - {e}")

    h.close()

if __name__ == '__main__':
    main()
