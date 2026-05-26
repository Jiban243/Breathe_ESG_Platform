# Product Architecture & Ambiguity Resolutions

This document records the strategic product engineering choices made during development to resolve real-world data ambiguities.

### 1. Ingestion Interface: Programmatic vs. Manual
* **Ambiguity**: Should data enter through real-time API integrations or batch file uploads?
* **Resolution**: Implemented file-based batch parsing endpoints (`/api/upload/`). In the enterprise landscape, getting third-party IT departments to expose direct SAP or Concur API ports can take months. Providing an instant CSV ingestion layer allows sustainability teams to begin processing data immediately.

### 2. Handing "Zero Consumption" Utility Rows
* **Ambiguity**: How should the system handle a utility statement row where consumption is `0` kWh?
* **Resolution**: The system generates a valid `Scope 2` transaction sheet but marks it with a specialized notification warning. Skipping the entry would create a gap in the audit history, whereas logging it keeps the tracking sequence intact and alerts analysts to potential meter malfunctions.

### 3. Flight Class Footprint Tracking
* **Ambiguity**: How should the system process varying cabin classes on commercial flights?
* **Resolution**: The travel engine checks for specific booking identifiers. If it detects a 'Business' class tag, it automatically applies a higher emission factor (e.g., DEFRA's $0.765\text{ kgCO}_2\text{e/km}$ multiplier vs. the standard $0.255\text{ kgCO}_2\text{e/km}$ Economy rate).

### 4. Handling Currency Discrepancies
* **Ambiguity**: Corporate travel logs contain mixed currency rows (`USD`, `GBP`, `INR`).
* **Resolution**: The prototype tracks raw currency fields for reference while normalizing core carbon calculations strictly against physical metrics (`km`, `nights`). This ensures fluctuations in currency markets do not artificially impact the environmental footprint metrics.

### Proposed Questions for the Product Manager (PM)
1. Do clients expect automated daily exchange rate conversions for financial procurement rows, or should we normalize strictly against raw volumes?
2. Should rejected database records be returned to the client's ERP queue for correction, or should they be handled entirely within our dashboard?