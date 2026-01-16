# Ribbon SBC CDR Parser (GUI)

A lightweight **Python / Tkinter GUI tool** for parsing **Ribbon SBC Core Call Detail Records (CDRs)** into a structured, human‑readable format. The tool supports **START**, **ATTEMPT**, and **STOP** CDR types and is designed for day‑to‑day operational troubleshooting, call‑flow validation, and analysis in enterprise voice environments.

This project was intentionally built as a **local‑only utility** suitable for locked‑down Windows servers commonly used in telecom operations.

---

## Supported Platforms

* Ribbon SBC 5400
* Ribbon SBC 7000
* Ribbon SBC SWe
* Ribbon SBC CNe

Developed and validated using **Ribbon SBC Core Release 12.01.06** documentation.

---

## Features

* Tkinter‑based GUI (no external dependencies)
* Paste raw Ribbon SBC CDRs directly into the interface
* **Condensed summary view** for quick triage
* **Full parsed CDR view** with structured sections
* Safe, index‑guarded parsing to handle CDR format variations
* SIP cause‑code decoding
* Codec identification
* Ingress / egress signaling and RTP IP extraction

---

## Screenshots

![Main Input](docs/screenshots/main_input.png?raw=true)

![Condensed View](docs/screenshots/condensed_view.png?raw=true)

![Full Parsed View](docs/screenshots/full_view.png?raw=true)

---

## Installation

### Editable install (recommended)

```bash
pip install -e .
python -m ribbon_cdr_parser
```

### Direct execution (no install)

```bash
python src/ribbon_cdr_parser/Ribbon_SBC_CDR_parser.py
```

---

## Usage

1. Launch the application
2. Paste a raw CDR into the input field
3. Click **Submit** to view the condensed summary
4. Click **View full parsed CDR** for detailed analysis

---

## Design Decisions

This project intentionally favors **clarity, reliability, and portability** over complexity.

* **Tkinter GUI**
  Chosen because it is part of the Python standard library and works well on locked‑down Windows servers without requiring external packages.

* **Index‑guarded parsing (`safe_get`)**
  Ribbon CDR formats vary by call type and release. Guarding index access prevents runtime crashes and ensures missing fields are gracefully displayed as `N/A`.

* **Separation of mappings and logic**
  Large CDR field mappings and SIP/codec lookups are isolated in a separate module to keep parsing logic readable and maintainable.

* **Local‑only execution**
  The tool does not transmit data externally, making it suitable for sensitive operational environments.

---

## Documentation Sources

This tool was built using official Ribbon Communications documentation:

* **Ribbon SBC Core 12.1.6 Documentation**
  [https://doc.rbbn.com/spaces/SBXDOC1216/pages/562564554/SBC+Core+12.1.6+Documentation](https://doc.rbbn.com/spaces/SBXDOC1216/pages/562564554/SBC+Core+12.1.6+Documentation)

* **Ribbon CDR Examples (Raw CDRs)**
  [https://doc.rbbn.com/spaces/SBXDOC1217/pages/596622448/CDR+Examples#CDRExamples-RawCDR.3](https://doc.rbbn.com/spaces/SBXDOC1217/pages/596622448/CDR+Examples#CDRExamples-RawCDR.3)

Sample CDR examples included in this repository were derived from these public documentation sources.

---

## Testing

Basic smoke tests Run: pytest under the `tests/` directory to validate that sample START, ATTEMPT, and STOP CDRs parse without error and return expected fields.

---

## Security & Privacy Notes

* This tool runs **entirely locally**
* Do **not** paste real customer data into public issue trackers
* Mask phone numbers, IPs, and identifiers before sharing screenshots

---

## Disclaimer

This project is **not affiliated with or endorsed by Ribbon Communications**. It is an independent, community‑created utility intended for operational and educational use.
