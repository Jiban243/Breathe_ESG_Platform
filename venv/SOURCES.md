# Data Source Implementations & Realism Justifications

This document explains the structural parameters of real-world enterprise environmental data streams, detailing how this prototype ingests them without relying on generic, oversimplified toy structures.

## 1. SAP Fuel & Procurement Invoices (`sap_mb51_export.csv`)

### Real-World Environmental Characteristics
Large corporations extract transactional logistics data using specialized ERP routines (such as SAP transaction `MB51` for Material Movements). These exports present significant parsing challenges:
* **Delimiter Quirks**: European system deployments natively output fields separated by semicolons (`;`) rather than commas.
* **Localized Context Structure**: Column maps contain German terminology (`Buchungsdatum`, `Werk`, `Menge`, `Mengeneinheit`) based on core system localizations.
* **Complex Material Identifiers**: Materials use custom internal string properties (`DIESEL-001`, `FURNACE-OIL`) instead of plain descriptions.
* **Operational Movement Rules**: Movement code keys track exactly why a material moved. Only specific codes signify direct fuel consumption (e.g., `201` for Goods Issue to Cost Center, `261` for Goods Issue to Order). Other codes, like stock transfers, must be systematically filtered out to prevent double-counting.

### Implemented Parser Strategy
The platform uses an automated dictionary tracking array (`SAP_MATERIAL_TO_CATEGORY`) to parse semicolon-delimited datasets. It processes date strings formatted as `DD.MM.YYYY`, checks for valid consumption codes (`201`/`261`), and maps legacy values to standard fuel units.

---

## 2. Power Utility Statements (`utility_portal_export.csv`)

### Real-World Environmental Characteristics
Utility companies output portal consumption statistics as comma-separated values, but with unique operational properties:
* **Misaligned Chronology**: Billing parameters match reading schedules rather than standard calendar months (e.g., January 3rd to February 6th).
* **Multi-Meter Infrastructure**: A single facility often aggregates consumption across multiple distinct meters, meaning data rows cannot be uniquely identified by facility name alone.
* **Complex Tariff Structures**: Energy rates vary based on electrical draw classifications (e.g., High-Tension Industrial vs. Low-Tension Commercial), which can determine the applicable grid emission factors.

### Implemented Parser Strategy
The parser reads distinct meter keys and extracts custom billing windows into standard date parameters. It gracefully handles inactive meters (where consumption is `0` kWh but base system charges still apply) by logging a specialized notification flag instead of skipping the record.

---

## 3. Corporate Travel Data (`concur_travel_export.csv`)

### Real-World Environmental Characteristics
Corporate booking platforms (like SAP Concur) export highly fractured data fields:
* **Missing Distance Tracking**: Airfare rows log starting and ending airport identifiers (IATA code sequences like `DEL` or `BOM`) without calculating mileage.
* **Cabin Class Variance**: Environmental multipliers differ significantly by seat tier; Business Class flights carry nearly triple the carbon footprint of Economy seats per kilometer due to space allocation.
* **Fragmented Accommodation and Transit Data**: Hotel stays provide room-night totals, while car rentals and taxis often log values in mixed regional currencies.

### Implemented Parser Strategy
The pipeline integrates a native mathematical lookup library containing spatial coordinates for key industrial IATA airport codes. When a flight distance field is empty, the parser automatically calculates flight mileage using the **Haversine formula**:

$$d = 2R \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos \phi_1 \cos \phi_2 \sin^2\left(\frac{\Delta \lambda}{2}\right)}\right)$$

If ground transit rows lack mileage data entirely, the platform flags the record as an anomaly rather than failing the execution loop.