# Data Model Architecture & Rationales

This document outlines the relational database schema designed for the Breathe ESG platform prototype. The schema is engineered to strictly satisfy enterprise requirements: multi-tenancy, immutable audit trails, source-of-truth traceability, and destructive-free unit normalization.

## Entity Relationship Overview
[Client]
│
├──► [Facility] (Plant code lookups)
│
├──► [IngestionBatch] (File metadata tracking)
│       │
│       └──► [RawRow] (As-is unparsed JSON record storage)
│               │
│               └──► [EmissionRecord] (Normalized computed entries)
│                       │
│                       └──► [AuditEvent] (Append-only state logs)

---

## Data Dictionary & Schema Fields

### 1. Client
The core multi-tenancy anchor table. Every transactional table contains a foreign key relation to this model to guarantee complete data isolation across corporate entities.
* `id` (UUID, Primary Key): Secure token identifier.
* `name` (VarChar): Corporate entity name.
* `slug` (SlugField, Unique): URL-safe string identifier utilized in routing selectors.
* `timezone` (VarChar): Regional localized temporal setting (Default: `Asia/Kolkata`) for calendarization.

### 2. Facility
Maps spatial data boundaries and isolates localized operational plants.
* `id` (UUID, Primary Key).
* `client` (ForeignKey -> Client): Relational isolation constraint.
* `name` (VarChar): Localized workspace descriptor.
* `plant_code` (VarChar, Index): Legacy identifier code generated from external ERP systems (e.g., SAP plant codes like `1010`, `2030`).

### 3. IngestionBatch
Tracks files injected into the ecosystem to satisfy source-of-truth compliance regulations.
* `id` (UUID, Primary Key).
* `client` (ForeignKey -> Client).
* `source_type` (VarChar Enum): Constraints restricted to `SAPFUEL`, `UTILITYELECTRICITY`, or `TRAVELCONCUR`.
* `filename` (VarChar): Name of the source file processed.
* `file_hash` (VarChar, Unique): SHA-256 fingerprint utilized to completely prevent duplicate processing.
* `status` (VarChar Enum): Core processing loops: `PENDING`, `PROCESSING`, `DONE`, `FAILED`.
* `ingested_by` (VarChar): Analyst identity tag responsible for the file pipeline execution.

### 4. RawRow
Preserves the raw string input fields exactly as they entered the pipeline before structural mutations occur.
* `id` (UUID, Primary Key).
* `batch` (ForeignKey -> IngestionBatch).
* `row_number` (Integer): Exact index positional coordinate within the source file.
* `raw_data` (JSONField): Complete structured key-value maps preserved precisely as ingested.
* `parse_status` (VarChar Enum): Operational results: `OK`, `FAILED`, `SUSPICIOUS`.
* `parse_error` (TextField): Descriptive string captures anomalies or format errors during parsing.

### 5. EmissionFactor
Houses regulatory emission multipliers separate from transactional computing tables to preserve calculation version history.
* `id` (UUID, Primary Key).
* `source_type` (VarChar): Maps back to the primary structural origin category.
* `category` (VarChar): Underlying material classification (e.g., `diesel`, `grid_electricity`).
* `region` (VarChar): Regional geographic scope determining constraint rules (e.g., `India`).
* `unit` (VarChar): Base dimensional metrics (e.g., `L`, `kWh`, `km`).
* `factor_kgco2e` (Float): Mathematical constant used to convert consumption data to carbon kilograms.
* `source_name` (VarChar): Regulatory body origin declaration (e.g., `MoEFCC`, `DEFRA`).
* `version` (VarChar): Active release sequence control variable.

### 6. EmissionRecord
The operational analytical hub containing computed carbon data and review workflows.
* `id` (UUID, Primary Key).
* `client` (ForeignKey -> Client).
* `raw_row` (OneToOne -> RawRow): Direct line-item linking back to unparsed input parameters.
* `factor` (ForeignKey -> EmissionFactor): Pointer tracking the exact coefficient version used for the calculation.
* `scope` (VarChar Enum): Definitive environmental categories: `SCOPE_1`, `SCOPE_2`, `SCOPE_3`.
* `period_start` / `period_end` (DateField): Temporal boundaries accommodating misaligned utility bill cycles.
* `quantity_raw` / `unit_raw` (Float / VarChar): Input metrics as declared on original documentation (e.g., `2500`, `GAL`).
* `quantity_norm` / `unit_norm` (Float / VarChar): Normalized global metrics computed by engine (e.g., `9463.5`, `L`).
* `co2e_kg` (Float): Computed environmental metric ($Quantity_{norm} \times Factor_{kgCO2e}$).
* `status` (VarChar Enum): Workflow status: `PENDING_REVIEW`, `APPROVED`, `REJECTED`.
* `flagged_reason` (TextField): Narrative string logging automated variance alerts.
* `is_edited` (Boolean): Flag identifying if human adjustments have occurred.
* `edit_history` (JSONField): Complete state history preservation containing value adjustments.

### 7. AuditEvent
Append-only log architecture constructed to provide transparency for security compliance auditors.
* `id` (UUID, Primary Key).
* `record` (ForeignKey -> EmissionRecord).
* `actor` (VarChar): System identity tag triggering state changes.
* `action` (VarChar): Operation tracking tags: `APPROVE`, `REJECT`, `EDIT`.
* `before_state` / `after_state` (JSONField): Captures complete field modifications.

---

## Core Engineering Decisions & Design Justifications

1. **Dual Unit Storage Model**: Retaining `raw` parameters alongside `normalized` properties guarantees calculation auditability. Auditors can easily recalculate and verify conversions from original sheets.
2. **One-to-One Raw Row Linking**: Linking data records to their raw parameters guarantees full operational trace-back capability, satisfying end-to-end lineage requirements.
3. **Double Date Temporal Boundary**: Utilizing distinct start and end date tracking ranges instead of a static month declaration allows the platform to cleanly capture overlapping invoice dates.
4. **Append-Only Event Auditing**: The application code does not implement database `DELETE` instructions. If data is rejected or altered, the adjustments are securely logged in the audit trail tables.

