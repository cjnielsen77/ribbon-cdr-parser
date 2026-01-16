#!/usr/bin/python3

"""
    Ribbon SBC CDR condensed and full parser

    description:    Uses Python TK to provide a user GUI to paste in a Ribbon SBC CDR. 
                    Will provide a condensed parsed CDR with Key fields (e.g. CDR Type, Start Date/time, duration, Disconnect Reason, calling/called #, Route label, Route Selected and Ingress TG)

    Version:        1.0 - Initial build
                    1.1 - Added search option
                    1.2 - Updated to parse condensed CDR first and allow to switch to full parsed

"""

import tkinter as tk
from tkinter import ttk
import csv
from io import StringIO
import re

from .cdr_field_mappings import (
    field_mappings,
    subfield_mappings,
    cdr_disconnect_reason,
    sip_cause_code_mapping
)

# set column width
def text_set_tabs(text_widget, col1_chars=48):
    text_widget.configure(tabs=(f"{col1_chars}c",))

def safe_get(seq, idx, default=""):
    """
    Safely get an item from a list/tuple by index.

    Returns `default` if:
      - seq is None
      - idx is out of bounds
      - idx is not an int
    """
    try:
        if seq is None:
            return default
        if not isinstance(idx, int):
            return default
        if idx < 0 or idx >= len(seq):
            return default
        return seq[idx]
    except Exception:
        return default

def get_codec_value(codec):
    if codec == "P:4:0":
        codec_value = "G.729A"
    elif codec == "P:2:1":
        codec_value = "G.711 w/ Silence Suppression"
    elif codec == "P:1:1":
        codec_value = "G.711 u-law"
    elif codec == "P:6:0":
        codec_value = "Fax Relay"
    else:
        codec_value = "N/A"

    return codec_value

def extract_device_name_from_contact(inv_contact_header: str) -> str:
    """
    Extract device identifier from a SIP Contact header-ish string.
    Handles cases where 'transport' shifts the '=' segments.
    Returns 'N/A' if it doesn't look like a phone/softphone/vm endpoint.
    """
    if not inv_contact_header:
        return "N/A"

    h = inv_contact_header.strip()
    hl = h.lower()

    # Only attempt parsing for common Cisco / voice endpoints
    if not any(token in hl for token in ("csf", "sep", "vms")):
        return "N/A"

    parts = h.split("=")
    # Your existing logic: if 'transport' exists, device name is the 3rd '=' segment; else 2nd
    want_index = 2 if "transport" in hl else 1

    return parts[want_index].strip() if len(parts) > want_index and parts[want_index].strip() else "N/A"

def parse_prot_data_side(prot_data: list, side_prefix: str, contact_idx: int) -> dict:
    """
    Parse either ingress or egress protocol data.

    side_prefix: 'ingress' or 'egress'
    contact_idx: which prot_data index holds the INVITE Contact header for that side
    """
    out = {
        f"{side_prefix}_call_id": "N/A",
        f"{side_prefix}_status": "N/A",
    }

    # Need index 18 => length must be at least 19
    if len(prot_data) < 19:
        return out

    call_id = safe_get(prot_data, 1, "").strip()
    status_code = safe_get(prot_data, 18, "").strip()

    if call_id:
        out[f"{side_prefix}_call_id"] = call_id

    # Build sip_<code> key and friendly text
    sip_key = f"sip_{status_code}" if status_code else "sip_UNKNOWN"
    
    if sip_key != "sip_BYE":
        sip_name = sip_cause_code_mapping.get(sip_key, "Unknown Code")
    else:
        sip_name = "BYE"

    # Display just the numeric part + friendly text
    code_display = status_code if status_code else "UNKNOWN"
    out[f"{side_prefix}_status"] = f"{code_display} ({sip_name})"

    inv_contact_header = safe_get(prot_data, contact_idx, "")
    out_key_device = "ing_device_name" if side_prefix == "ingress" else "egr_device_name"
    out[out_key_device] = extract_device_name_from_contact(inv_contact_header)

    return out

def parse_cdr_to_dict(raw_cdr: str) -> dict:
    """
    Pure parser: takes a raw CDR string and returns a parsed_data dict.
    No GUI side effects. Safe for unit tests.
    """
    raw_cdr_without_protocol_data = re.sub(r'"[^"]*"', '', raw_cdr)     # Find any "cdr,fields" and replace everything with ''
    cdr_fields_without_prot_data = raw_cdr_without_protocol_data.strip().split(",")
    #print(raw_cdr)

    ## Get CDR values
    fields = raw_cdr.strip().split(",")
    cdr_fields_parsed = raw_cdr.strip().split('"')
    
    cdr_type = safe_get(fields, 0)
    ingr_prot_data_ck = ""
    if cdr_type == "ATTEMPT":
        ingr_prot_data_ck = safe_get(fields, 44)
    elif cdr_type == "STOP":
        ingr_prot_data_ck = safe_get(fields, 51)
    elif cdr_type == "START":
        ingr_prot_data_ck = safe_get(fields, 41)
    
    ## Check if ingress protocal variant data is present
    if "SIP" in ingr_prot_data_ck or "GSX2GSX" in ingr_prot_data_ck:
        ingr_raw = safe_get(cdr_fields_parsed, 1, "").strip()
        egr_raw  = safe_get(cdr_fields_parsed, 3, "").strip()

        ingr_prot_data = ingr_raw.split(",") if ingr_raw else []
        egr_prot_data  = egr_raw.split(",") if egr_raw else []
    else:
        ingr_prot_data = []
        egr_raw = safe_get(cdr_fields_parsed, 1, "").strip()
        egr_prot_data = egr_raw.split(",") if egr_raw else []
    
    ## Check if egress protocal variant data is present
    if not any("SIP" in item for item in egr_prot_data):
        egr_prot_data = []
    
    parsed_data = {}
    calling_nm_raw = safe_get(cdr_fields_parsed, 5, "").strip()
    calling_name = calling_nm_raw.split(",") if calling_nm_raw else []
    parsed_data["calling_name"] = calling_name

    ## check for GWGW where ingr/egr protocal data will only contain 2 fields
    parsed_data.update(parse_prot_data_side(ingr_prot_data, "ingress", contact_idx=12))
    parsed_data.update(parse_prot_data_side(egr_prot_data, "egress", contact_idx=13))

    # Ensure device keys exist even if prot-data was short
    parsed_data.setdefault("ing_device_name", "N/A")
    parsed_data.setdefault("egr_device_name", "N/A")

    parsed_data["cdr_type"] = cdr_type
    parsed_data["gateway_name"] = safe_get(fields, 1)
    parsed_data["start_date"] = safe_get(fields, 5)
    parsed_data["start_time"] = safe_get(fields, 6)

    if cdr_type == "ATTEMPT":
        parsed_data["disconnect_time"] = safe_get(fields, 9)
        parsed_data["duration"] = "N/A"

        # Disconnect reason
        dr_code = safe_get(fields, 11)
        disconnect_reason = f"DR{dr_code}" if dr_code else "drUNKNOWN"
        disconnect_name = cdr_disconnect_reason.get(disconnect_reason, "Unknown Code")
        parsed_data["disconnect_reason"] = f"{disconnect_reason} ({disconnect_name})"

        # Service provider
        service_provider = safe_get(fields, 14)
        parsed_data["service_provider"] = service_provider if service_provider else "N/A"

        # Calling number
        calling_number = safe_get(fields, 16)
        if calling_name:
            calling_number = f"{calling_number} ({calling_name})"
        parsed_data["calling_number"] = calling_number

        parsed_data["called_number"] = safe_get(fields, 17)
        parsed_data["billing_number"] = safe_get(fields, 24)

        # Route label
        route_label = safe_get(fields, 25)
        if not route_label:
            parsed_data["route_label"] = "N/A (GW-GW call)"
        else:
            parsed_data["route_label"] = route_label

        parsed_data["route_attempt_num"] = safe_get(fields, 26)
        parsed_data["route_selected"] = safe_get(fields, 27)
        parsed_data["ingress_tg"] = safe_get(fields, 30)

        # Disconnect initiator (from no-prot-data fields)
        disconnect_initiator = safe_get(cdr_fields_without_prot_data, 56)
        if disconnect_initiator == "0":
            disconnect_initiator += " (Internal)"
        elif disconnect_initiator == "1":
            disconnect_initiator += " (Calling Party)"
        elif disconnect_initiator == "2":
            disconnect_initiator += " (Called Party)"
        elif disconnect_initiator:
            disconnect_initiator += " (Invalid value found)"
        else:
            disconnect_initiator = "N/A"

        parsed_data["disconnect_initiator"] = disconnect_initiator
        parsed_data["egress_tg"] = safe_get(cdr_fields_without_prot_data, 57)

        # Codecs
        ingress_codec_code = safe_get(cdr_fields_without_prot_data, 68)
        parsed_data["ingress_codec"] = get_codec_value(ingress_codec_code)

        egress_codec_code = safe_get(cdr_fields_without_prot_data, 69)
        parsed_data["egress_codec"] = get_codec_value(egress_codec_code)

        parsed_data["sbc_call_id"] = safe_get(cdr_fields_without_prot_data, 71)

        # IPs
        parsed_data["ingress_local_ip"] = safe_get(cdr_fields_without_prot_data, 114)
        parsed_data["ingress_remote_ip"] = safe_get(cdr_fields_without_prot_data, 115)

        ingress_rtp_ip_port = safe_get(fields, 32)
        if ingress_rtp_ip_port and "/" in ingress_rtp_ip_port:
            parts = ingress_rtp_ip_port.strip().split("/")
            parsed_data["ingress_local_rtp_ip"] = safe_get(parts, 0)
            parsed_data["ingress_remote_rtp_ip"] = safe_get(parts, 1)

        parsed_data["ingress_audio_packets_sent"] = "N/A"
        parsed_data["ingress_audio_packets_rcvd"] = "N/A"
        parsed_data["ingress_packets_lost"] = "N/A"

        parsed_data["egress_local_ip"] = safe_get(fields, 28)
        parsed_data["egress_remote_ip"] = safe_get(fields, 29)

        egress_rtp_ip_port = safe_get(fields, 34)
        if egress_rtp_ip_port and "/" in egress_rtp_ip_port:
            parts = egress_rtp_ip_port.strip().split("/")
            parsed_data["egress_local_rtp_ip"] = safe_get(parts, 0)
            parsed_data["egress_remote_rtp_ip"] = safe_get(parts, 1)

        parsed_data["egress_audio_packets_sent"] = "N/A"
        parsed_data["egress_audio_packets_rcvd"] = "N/A"
        parsed_data["egress_packets_lost"] = "N/A"

        parsed_data["stop_date"] = safe_get(cdr_fields_without_prot_data, 104)

    if cdr_type == "STOP":
        parsed_data["stop_date"] = safe_get(fields, 10)
        parsed_data["disconnect_time"] = safe_get(fields, 11)

        # Duration (convert to seconds; original appears to be hundredths)
        duration_raw = safe_get(fields, 13)
        try:
            duration_val = int(duration_raw) * 0.01
            parsed_data["duration"] = round(duration_val, 2)
        except (TypeError, ValueError):
            parsed_data["duration"] = "N/A"

        # Disconnect reason
        dr_code = safe_get(fields, 14)
        disconnect_reason = f"DR{dr_code}" if dr_code else "drUNKNOWN"
        disconnect_name = cdr_disconnect_reason.get(disconnect_reason, "Unknown Code")
        parsed_data["disconnect_reason"] = f"{disconnect_reason} ({disconnect_name})"

        sp = safe_get(fields, 17)
        parsed_data["service_provider"] = sp if sp else "N/A"

        calling_number = safe_get(fields, 19)
        if calling_name:
            calling_number = f"{calling_number} ({calling_name})"
        parsed_data["calling_number"] = calling_number

        parsed_data["called_number"] = safe_get(fields, 20)
        parsed_data["billing_number"] = safe_get(fields, 27)

        route_label = safe_get(fields, 28)
        if not route_label:
            parsed_data["route_label"] = "N/A (GW-GW call)"
        else:
            parsed_data["route_label"] = route_label

        parsed_data["route_attempt_num"] = safe_get(fields, 29)
        parsed_data["route_selected"] = safe_get(fields, 30)
        parsed_data["ingress_tg"] = safe_get(fields, 33)

        # Disconnect initiator
        disconnect_initiator = safe_get(cdr_fields_without_prot_data, 63)
        if disconnect_initiator == "0":
            disconnect_initiator += " (Internal)"
        elif disconnect_initiator == "1":
            disconnect_initiator += " (Calling Party)"
        elif disconnect_initiator == "2":
            disconnect_initiator += " (Called Party)"
        elif disconnect_initiator:
            disconnect_initiator += " (Invalid value found)"
        else:
            disconnect_initiator = "N/A"

        parsed_data["disconnect_initiator"] = disconnect_initiator
        parsed_data["egress_tg"] = safe_get(cdr_fields_without_prot_data, 67)

        # Codecs
        ingress_codec_code = safe_get(cdr_fields_without_prot_data, 78)
        parsed_data["ingress_codec"] = get_codec_value(ingress_codec_code)

        egress_codec_code = safe_get(cdr_fields_without_prot_data, 79)
        parsed_data["egress_codec"] = get_codec_value(egress_codec_code)

        parsed_data["sbc_call_id"] = safe_get(cdr_fields_without_prot_data, 81)

        # IPs
        parsed_data["ingress_local_ip"] = safe_get(cdr_fields_without_prot_data, 124)
        parsed_data["ingress_remote_ip"] = safe_get(cdr_fields_without_prot_data, 125)

        ingress_rtp_ip_port = safe_get(fields, 35)
        if ingress_rtp_ip_port and "/" in ingress_rtp_ip_port:
            parts = ingress_rtp_ip_port.strip().split("/")
            parsed_data["ingress_local_rtp_ip"] = safe_get(parts, 0)
            parsed_data["ingress_remote_rtp_ip"] = safe_get(parts, 1)

        parsed_data["ingress_audio_packets_sent"] = safe_get(fields, 39)
        parsed_data["ingress_audio_packets_rcvd"] = safe_get(fields, 41)
        parsed_data["ingress_packets_lost"] = safe_get(cdr_fields_without_prot_data, 64)

        # --- Add packet loss percentage into ingress_packets_lost field ---
        try:
            rcvd = int(parsed_data["ingress_audio_packets_rcvd"])
            lost = int(parsed_data["ingress_packets_lost"])

            # Check >= 0 and avoid divide-by-zero
            if lost >= 0 and rcvd > 0:
                pct = (lost / rcvd) * 100
                parsed_data["ingress_packets_lost"] = f"{lost} ({pct:.1f}%)"
            else:
                # Keep original value if rcvd is 0 or lost is negative
                parsed_data["ingress_packets_lost"] = str(lost)

        except (TypeError, ValueError):
            # If safe_get returned something non-numeric like "" / "N/A"
            pass

        parsed_data["egress_local_ip"] = safe_get(fields, 31)
        parsed_data["egress_remote_ip"] = safe_get(fields, 32)

        egress_rtp_ip_port = safe_get(fields, 37)
        if egress_rtp_ip_port and "/" in egress_rtp_ip_port:
            parts = egress_rtp_ip_port.strip().split("/")
            parsed_data["egress_local_rtp_ip"] = safe_get(parts, 0)
            parsed_data["egress_remote_rtp_ip"] = safe_get(parts, 1)

        parsed_data["egress_audio_packets_sent"] = safe_get(cdr_fields_without_prot_data, 145)
        parsed_data["egress_audio_packets_rcvd"] = safe_get(cdr_fields_without_prot_data, 147)
        parsed_data["egress_packets_lost"] = safe_get(cdr_fields_without_prot_data, 148)

         # --- Add packet loss percentage into ingress_packets_lost field ---
        try:
            rcvd = int(parsed_data["egress_audio_packets_rcvd"])
            lost = int(parsed_data["egress_packets_lost"])

            # Check >= 0 and avoid divide-by-zero
            if lost >= 0 and rcvd > 0:
                pct = (lost / rcvd) * 100
                parsed_data["egress_packets_lost"] = f"{lost} ({pct:.1f}%)"
            else:
                # Keep original value if rcvd is 0 or lost is negative
                parsed_data["egress_packets_lost"] = str(lost)

        except (TypeError, ValueError):
            # If safe_get returned something non-numeric like "" / "N/A"
            pass

    if cdr_type == "START":
        parsed_data["disconnect_time"] = "N/A"
        parsed_data["duration"] = "N/A"
        parsed_data["disconnect_reason"] = "N/A"

        # Service provider (blank => N/A)
        service_provider = safe_get(fields, 12)
        parsed_data["service_provider"] = service_provider if service_provider else "N/A"

        # Calling number
        calling_number = safe_get(fields, 15)
        if calling_name:
            calling_number = f"{calling_number} ({calling_name})"
        parsed_data["calling_number"] = calling_number

        # Called number (keeping your same index, but safe)
        parsed_data["called_number"] = safe_get(fields, 16)

        parsed_data["billing_number"] = safe_get(fields, 22)

        # Route label
        route_label = safe_get(fields, 23)
        if not route_label:
            parsed_data["route_label"] = "N/A (GW-GW call)"
        else:
            parsed_data["route_label"] = route_label

        parsed_data["route_attempt_num"] = safe_get(fields, 24)
        parsed_data["route_selected"] = safe_get(fields, 25)
        parsed_data["ingress_tg"] = safe_get(fields, 28)

        parsed_data["disconnect_initiator"] = "N/A"

        parsed_data["egress_tg"] = safe_get(cdr_fields_without_prot_data, 53)

        parsed_data["ingress_codec"] = "N/A"
        parsed_data["egress_codec"] = "N/A"

        parsed_data["sbc_call_id"] = safe_get(cdr_fields_without_prot_data, 64)

        parsed_data["ingress_local_ip"] = safe_get(cdr_fields_without_prot_data, 101)
        parsed_data["ingress_remote_ip"] = safe_get(cdr_fields_without_prot_data, 102)

        ingress_rtp_ip_port = safe_get(fields, 30)
        if ingress_rtp_ip_port and "/" in ingress_rtp_ip_port:
            parts = ingress_rtp_ip_port.strip().split("/")
            parsed_data["ingress_local_rtp_ip"] = safe_get(parts, 0)
            parsed_data["ingress_remote_rtp_ip"] = safe_get(parts, 1)

        parsed_data["ingress_audio_packets_sent"] = "N/A"
        parsed_data["ingress_audio_packets_rcvd"] = "N/A"
        parsed_data["ingress_packets_lost"] = "N/A"

        parsed_data["egress_local_ip"] = safe_get(fields, 26)
        parsed_data["egress_remote_ip"] = safe_get(fields, 27)

        egress_rtp_ip_port = safe_get(fields, 32)
        if egress_rtp_ip_port and "/" in egress_rtp_ip_port:
            parts = egress_rtp_ip_port.strip().split("/")
            parsed_data["egress_local_rtp_ip"] = safe_get(parts, 0)
            parsed_data["egress_remote_rtp_ip"] = safe_get(parts, 1)

        parsed_data["egress_audio_packets_sent"] = "N/A"
        parsed_data["egress_audio_packets_rcvd"] = "N/A"
        parsed_data["egress_packets_lost"] = "N/A"

    return parsed_data

def parse_cdr(cdr_input, root):

    def block_edit(event):
        # Allow Ctrl+C (copy) and Ctrl+A (select all)
        if (event.state & 0x4) and event.keysym.lower() in ("c", "a"):
            return
        return "break"

    def run_search(find_next=True):
        nonlocal search_matches, search_index
        q = search_entry.get().strip()
        parsed_text.tag_remove("highlight", "1.0", tk.END)
        search_matches = []
        search_index = -1
        
        if not q:
            status_var.set("")
            return
        
        flags = re.IGNORECASE if ignore_case_var.get() else 0
        text = parsed_text.get("1.0", tk.END)
        
        for m in re.finditer(re.escape(q), text, flags):
            start = f"1.0+{m.start()}c"
            end = f"1.0+{m.end()}c"
            parsed_text.tag_add("highlight", start, end)
            search_matches.append((start, end))

        status_var.set(f"{len(search_matches)} match(es)")

        if search_matches and find_next:
            goto_match(0)

    def goto_match(idx):
        nonlocal search_index
        if not search_matches:
            return
        search_index = idx % len(search_matches)
        start, end = search_matches[search_index]
        parsed_text.see(start)
        parsed_text.tag_remove("sel", "1.0", tk.END)
        parsed_text.tag_add("sel", start, end)
        parsed_text.mark_set(tk.INSERT, end)

    def next_match(event=None):
        if search_matches:
            goto_match(search_index + 1)

    def prev_match(event=None):
        if search_matches:
            goto_match(search_index - 1)

    def search_text():
        run_search(find_next=True)

    # --- Setup window ---
    if root is None:
        root = tk.Tk()
        root.withdraw()
    parsed_window = tk.Toplevel(root)
    parsed_window.title("Parsed CDR")
    parsed_window.geometry("1000x700")

    # --- Text widget and scrollbars ---
    frame = ttk.Frame(parsed_window)
    frame.pack(fill="both", expand=True, padx=5, pady=5)

    parsed_text = tk.Text(frame, height=40, width=120, wrap="none", font=("Consolas", 10))    
    vscroll = ttk.Scrollbar(frame, orient="vertical", command=parsed_text.yview)    
    hscroll = ttk.Scrollbar(frame, orient="horizontal", command=parsed_text.xview)
    
    parsed_text.grid(row=0, column=0, sticky="nsew")
    vscroll.grid(row=0, column=1, sticky="ns")
    hscroll.grid(row=1, column=0, sticky="ew")

    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    parsed_text.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)
    
    # --- Prevent editing but allow selection/copy ---
    for seq in ("<Key>", "<Delete>", "<BackSpace>", "<<Paste>>", "<<Cut>>"):
        parsed_text.bind(seq, block_edit)
    
    # --- Insert parsed content ---
    reader = csv.reader(StringIO(cdr_input), delimiter=',', quotechar='"')
    fields = next(reader)

    # Get CDR type and mappings
    cdr_type = fields[0]
    mapping = field_mappings.get(cdr_type, {})
    subfields = subfield_mappings.get(cdr_type, {})

    # Find the max width for field names for alignment
    max_field_len = max((len(name) for name in mapping.values()), default=20)
    col1_width = max(50, max_field_len + 15)

    for i, field in enumerate(fields, start=1):
        field_name = mapping.get(i, f"Field {i}")
        main_label = f"{field_name} ({i})"
        # Check for subfields
        if i in subfields and "," in field:
            # Print main field
            parsed_text.insert("end", f"{main_label:<{col1_width}} : {field}\n", "main_field")
            # Print subfields
            subfield_names = subfields[i]
            subfield_values = list(csv.reader([field], delimiter=',', quotechar='"'))[0]
            for j, value in enumerate(subfield_values, start=1):
                subfield_label = subfield_names[j-1] if j-1 < len(subfield_names) else f"Subfield {i}.{j}"
                parsed_text.insert(
                    "end",
                    f"  {subfield_label} ({i}.{j})".ljust(col1_width - 2) + f": {value}\n",
                    "subfield"
                )
        else:
            parsed_text.insert("end", f"{main_label:<{col1_width}} : {field}\n", "main_field")

    parsed_text.insert("end", "\n")

    parsed_text.tag_configure(
        "main_field",
        background="#e0e7ef",
        foreground="#1e293b",
        font=("Consolas", 10),
        selectbackground="#3399ff",
        selectforeground="#ffffff"
    )
    parsed_text.tag_configure(
        "subfield",
        background="#f1f5f9",
        foreground="#334155",
        font=("Consolas", 10),
        selectbackground="#3399ff",
        selectforeground="#ffffff"
    )
    
    parsed_text.tag_configure("field_name", background="#e0e7ef", foreground="#1e293b", font=("Consolas", 10, "bold"))
    parsed_text.tag_configure("field_value", background="#f8fafc", foreground="#334155", font=("Consolas", 10))
    parsed_text.tag_configure("subfield_name", background="#f1f5f9", foreground="#334155", font=("Consolas", 10, "bold"))
    parsed_text.tag_configure("subfield_value", background="#f8fafc", foreground="#334155", font=("Consolas", 10))

    # --- Search bar ---
    search_frame = ttk.Frame(parsed_window)
    search_frame.pack(fill="x", pady=5)
    search_label = ttk.Label(search_frame, text="Search:")
    search_label.pack(side="left", padx=5)
    search_entry = ttk.Entry(search_frame)
    search_entry.pack(side="left", fill="x", expand=True, padx=5)
    ignore_case_var = tk.BooleanVar(value=True)
    ignore_case_check = ttk.Checkbutton(search_frame, text="Ignore case", variable=ignore_case_var)
    ignore_case_check.pack(side="left", padx=6)
    status_var = tk.StringVar(value="")
    status_label = ttk.Label(search_frame, textvariable=status_var)
    status_label.pack(side="left", padx=8)

    # --- Search logic ---
    search_matches = []
    search_index = -1

    search_button = ttk.Button(search_frame, text="Find", command=search_text)
    search_button.pack(side="left", padx=5)
    prev_button = ttk.Button(search_frame, text="Prev", command=prev_match)
    prev_button.pack(side="left", padx=2)
    next_button = ttk.Button(search_frame, text="Next", command=next_match)
    next_button.pack(side="left", padx=2)
    search_entry.bind("<Return>", lambda e: run_search(find_next=True))
    parsed_window.bind("<F3>", next_match)
    parsed_window.bind("<Shift-F3>", prev_match)

    # --- Close button ---
    close_button = ttk.Button(parsed_window, text="Close", command=parsed_window.destroy)
    close_button.pack(side="left", pady=5, expand=True)

    # --- Focus ---
    parsed_window.lift()
    parsed_window.after(200, parsed_text.focus_set)

def condensed_parse_cdr(raw_cdr, root):
    
    def add_section(title, last_line, fields, key_w):
        text_widget.insert(tk.END, border_line)
        text_widget.insert(tk.END, f"| {title:<60}\n")
        text_widget.insert(tk.END, border_line)

        visible_items = []
        for k, v in fields.items():
            if (("CUCM Device Name" in k or "DSP Audio Packets" in k or "Number Packets Lost" in k
                or k == "Call Service Duration") and v == "N/A"):
                continue
            visible_items.append((k, v))

        for key, value in visible_items:
            text_widget.insert(tk.END, f"| {key:<{key_w}} | {value}\n")

        if last_line == 1:
            text_widget.insert(tk.END, border_line)
    
    def block_edit(event):
        return "break"

    def copy_parsed_cdr_to_clipboard():
        parsed_window.clipboard_clear()
        parsed_window.clipboard_append(text_widget.get("1.0", tk.END))
        parsed_window.update()  # stays in clipboard after the window is closed
    
    #
    parsed_data = parse_cdr_to_dict(raw_cdr)

    parsed_window = tk.Toplevel(root)
    parsed_window.title("Parsed CDR")

    # set the initial window size
    parsed_window.geometry("675x800")

    # Main frame to hold text widget and scrollbar
    main_frame = ttk.Frame(parsed_window)
    main_frame.pack(fill="both", expand=True)

    # Create a text widget and configure it to wrap and expand
    text_widget = tk.Text(main_frame, wrap="none", padx=5, pady=5)
    text_widget.pack(side="left", fill="both", expand=True)

    # Create a scrollbar and link it to the text widget
    scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=text_widget.yview)
    scrollbar.pack(side="right", fill="y")
    text_widget.configure(yscrollcommand=scrollbar.set)

    # define the border line and section titles
    border_line = "|---------------------------------------------------------\n"
  
    # Define sections and their respective fields from parsed_data
    parsed_cdr_sections = [
        {
            "CDR Type": parsed_data.get("cdr_type", "N/A"),
            "Gateway Name": parsed_data.get("gateway_name", "N/A"),
            "Disconnect Date": parsed_data.get("stop_date", "N/A"),
            "Start Time": parsed_data.get("start_time", "N/A"),
            "Disconnect Time": parsed_data.get("disconnect_time", "N/A"),
            "Call Service Duration": parsed_data.get("duration", "N/A"),
            "Calling Number": parsed_data.get("calling_number", "N/A"),
            "Called Number": parsed_data.get("called_number", "N/A"),
            "Billing Number": parsed_data.get("billing_number", "N/A"),
        },
        {
            "Route Label": parsed_data.get("route_label", "N/A"),
            "Route Attempt Number": parsed_data.get("route_attempt_num", "N/A"),
            "Route Selected": parsed_data.get("route_selected", "N/A"),
            "Service Provider": parsed_data.get("service_provider", "N/A"),
            "GSX Call ID (GCID)": parsed_data.get("sbc_call_id", "N/A"),
        },
        {
            "Call Disconnect Reason": parsed_data.get("disconnect_reason", "N/A"),
            "Disconnect Initiator": parsed_data.get("disconnect_initiator", "N/A"),
            "ING Status Msg for Call Release": parsed_data.get("ingress_status", "N/A"),
            "EGR Status Msg for Call Release": parsed_data.get("egress_status", "N/A"),
        },
        {
            "Ingress Trunk Group Name": parsed_data.get("ingress_tg", "N/A"),
            "Ingress Call ID": parsed_data.get("ingress_call_id", "N/A"),
            "Ingress Codec Type": parsed_data.get("ingress_codec", "N/A"),
            "Ingress CUCM Device Name": parsed_data.get("ing_device_name", "N/A"),
            "Ingress Local Signaling IP Addr": parsed_data.get("ingress_local_ip", "N/A"),
            "Ingress Remote Signaling IP Addr": parsed_data.get("ingress_remote_ip", "N/A"),
            "Ingress Local RTP IP Addr": parsed_data.get("ingress_local_rtp_ip", "N/A"),
            "Ingress Remote RTP IP Addr": parsed_data.get("ingress_remote_rtp_ip", "N/A"),
            "Ingress DSP Audio Packets Sent": parsed_data.get("ingress_audio_packets_sent", "N/A"),
            "Ingress DSP Audio Packets Rcvd": parsed_data.get("ingress_audio_packets_rcvd", "N/A"),
            "Ingress Number Packets Lost": parsed_data.get("ingress_packets_lost", "N/A"),
        },
        {
            "Egress Trunk Group Name": parsed_data.get("egress_tg", "N/A"),
            "Egress Call ID": parsed_data.get("egress_call_id", "N/A"),
            "Egress Codec Type": parsed_data.get("egress_codec", "N/A"),
            "Egress CUCM Device Name": parsed_data.get("egr_device_name", "N/A"),
            "Egress Local Signaling IP Addr": parsed_data.get("egress_local_ip", "N/A"),
            "Egress Remote Signaling IP Addr": parsed_data.get("egress_remote_ip", "N/A"),
            "Egress Local RTP IP Addr": parsed_data.get("egress_local_rtp_ip", "N/A"),
            "Egress Remote RTP IP Addr": parsed_data.get("egress_remote_rtp_ip", "N/A"),
            "Egress DSP Audio Packets Sent": parsed_data.get("egress_audio_packets_sent", "N/A"),
            "Egress DSP Audio Packets Rcvd": parsed_data.get("egress_audio_packets_rcvd", "N/A"),
            "Egress Number Packets Lost": parsed_data.get("egress_packets_lost", "N/A"),
        }
    ]
    
    # Find the max key length across all sections
    key_w = min(46, max(22, max(len(k) for section in parsed_cdr_sections for k in section)))

    # --- USE THE SHARED key_w FOR ALL SECTIONS ---
    add_section("Overall Call Data", 0, parsed_cdr_sections[0], key_w)
    add_section("Call Routing Details", 0, parsed_cdr_sections[1], key_w)
    add_section("Call Disconnect Details", 0, parsed_cdr_sections[2], key_w)
    add_section("Ingress Call Data", 0, parsed_cdr_sections[3], key_w)
    add_section("Egress Call Data", 0, parsed_cdr_sections[4], key_w)
    text_widget.insert(tk.END, border_line)

    text_widget.config(state="normal")
    
    # Prevent editing but allow selection/copy
    for seq in ("<Key>", "<Delete>", "<<Paste>>", "<<Cut>>"):
        text_widget.bind(seq, block_edit)

    # Create a frame for the buttons on the bottom
    button_frame = ttk.Frame(parsed_window)
    button_frame.pack(padx=10, pady=(0, 10), anchor="center")

    # Configure the grid to center the buttons
    button_frame.grid_columnconfigure(0, weight=1)
    button_frame.grid_columnconfigure(4, weight=1)

    # Add link to fully parsed CDR window
    full_cdr_parse = ttk.Button(
        button_frame,
        text="View full parsed CDR",
        command=lambda: parse_cdr(raw_cdr, root)
    )
    full_cdr_parse.grid(row=0, column=1, padx=10, pady=5)

    # Add the copy button
    copy_button = ttk.Button(button_frame, text="Copy Parsed CDR", command=copy_parsed_cdr_to_clipboard)
    copy_button.grid(row=0, column=2, padx=10, pady=5)

    # Add the close button at the bottom
    close_button = ttk.Button(button_frame, text="Close", command=parsed_window.destroy)
    close_button.grid(row=0, column=3, padx=10, pady=5)

def main():
    def get_cdr():
        cdr_input = cdr_text.get("1.0", tk.END).strip()
        condensed_parse_cdr(cdr_input, root)
    
    def clear_text_box():
        cdr_text.delete("1.0", tk.END)
    
    def on_close_main_window():
        root.destroy()

    # Create the main tkinter window
    root = tk.Tk()
    root.title("CDR Parser")
    root.geometry("600x400")    

    # Bind the close event to ensure proper cleanup
    root.protocol("WM_DELETE_WINDOW", on_close_main_window)

    label = ttk.Label(root, text="Enter CDR (comma-separated):")
    label.pack(pady=5)

    cdr_text = tk.Text(root, height=20, width=80,
        font=("Consolas", 10),
        bg="#0b1220", fg="#e2e8f0",
        insertbackground="#e2e8f0")
    cdr_text.pack(pady=5)

    button_frame = ttk.Frame(root)
    button_frame.pack(pady=5, anchor="center")

    submit_button = ttk.Button(button_frame, text="Submit", command=get_cdr)
    submit_button.pack(side="left", padx=15, pady=5, expand=True)

    clear_button = ttk.Button(button_frame, text="Clear", command=clear_text_box)
    clear_button.pack(side="left", padx=15, pady=5, expand=True)

    close_button = ttk.Button(button_frame, text="Close", command=on_close_main_window)
    close_button.pack(side="left", padx=15, pady=5, expand=True)

    root.mainloop()

# Only run the tkinter GUI if the script is execute directly
if __name__ == "__main__":
    main()
