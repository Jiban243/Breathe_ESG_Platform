# Strategic Engineering Trade-offs

To deliver a production-ready core platform within the 4-day sprint window, structural boundaries were established[cite: 9]. This document outlines the three items deliberately excluded from the prototype and the architectural rationale for those choices[cite: 44, 57].

### 1. Automated PDF Text Extraction (OCR Ingestion Engine)
* **What was excluded**: An automated PDF scanner to read utility bills directly.
* **Why**: Building a robust OCR processor that handles highly variable billing templates across different utility providers is an extensive task. Relying on an unpolished scanner would introduce dirty data into the ingestion layer. Instead, the prototype focuses on handling structured portal CSV exports, delivering a clean data pipeline.

### 2. Multi-Currency Financial Ledger Ingestion
* **What was excluded**: A live financial exchange-rate engine for cost rows.
* **Why**: Financial values fluctuate daily, but carbon metrics depend strictly on physical quantities (like fuel volumes or distances traveled). Building an automated conversion service would add unnecessary complexity. The system isolates calculations to physical usage statistics, ensuring stable and auditable reporting.

### 3. Automated Emission Factor Matching via LLMs
* **What was excluded**: Using an AI model to guess and map unknown material codes to emission categories.
* **Why**: Environmental auditing requires strict determinism. If an AI misclassifies a material code during an ingestion run, it compromises the integrity of the data handed to the auditors. The platform relies on precise, deterministic dictionary lookups, guaranteeing absolute repeatability.