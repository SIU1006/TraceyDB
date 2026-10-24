# Catalogue provenance

TraceyDB is an independent educational project and is not authorised, sponsored or endorsed by Apple Inc. Apple, iPhone, MacBook Air and Apple Vision Pro are trademarks of Apple Inc. Product names identify the referenced products; TraceyDB uses no Apple logos or product photographs.

## Public specifications

Checked on 22 October 2026. This is a selected historical catalogue, not a complete or current Apple retail inventory.

| Product | Configurations represented | Selected components |
| --- | --- | --- |
| [iPhone 17 Pro](https://support.apple.com/en-us/125090) | 256GB, 512GB and 1TB; Silver, Cosmic Orange and Deep Blue | A19 Pro chip, 6.3-inch Super Retina XDR OLED display, lithium-ion battery |
| [MacBook Air (13-inch, M4, 2025)](https://support.apple.com/en-us/122209) | 256GB, 512GB, 1TB and 2TB; Sky Blue, Silver, Starlight and Midnight | M4 chip with 10-core CPU and 8-core GPU, 13.6-inch Liquid Retina display, 53.8Wh lithium-polymer battery |
| [Apple Vision Pro (2024)](https://support.apple.com/en-us/117810) | 256GB, 512GB and 1TB | M2 chip, R1 chip, micro-OLED display system; external battery also registered in the component catalogue |

The original MacBook Air M4 fixtures use the baseline 16GB memory and 8-core GPU option. Additional models distinguish chip families; RAM and CPU/GPU core counts are not exhaustively represented. Apple's cited Vision Pro specification does not list a finish option, so `colour` is NULL; the provenance file retains the original missing-value explanation.

## Synthetic assumptions

All suppliers, retailers, addresses, supplier relationships, internal SKUs, lots, quantities, manufacturing records, orders, allocations and shipments are simulated. They are not evidence of Apple's commercial relationships or manufacturing processes. Supplier countries and Australian warehouse city names provide geographical context only.

The expanded seed has 143 component types. Each existing manufacturing batch records 9–11 inputs, covering chips and family-appropriate assemblies such as displays, batteries, memory, storage, cameras, audio, sensors, enclosures, cooling and input devices. One complete named assembly or set is consumed per finished unit, with zero scrap. These are abstract family-level simulation specifications, not Apple service part numbers or claims that parts are interchangeable between models. Memory and storage are separate accounting inputs even where physically integrated into a package or board. Exact capacities, finishes and revision compatibility of these generic assemblies are outside scope. Vision Pro batches now consume their external battery. Watch and AirPods assemblies have simulated supplier receipts; their products remain catalogue-only without manufacturing stock.

The deterministic data contains 69,533 rows in total across fifteen tables, not 69,533 products or orders. Small isolated fixtures retain shortages, a quality hold, split allocations and a known recall path for repeatable tests; larger operational records cover the remaining configurations. Many registered configurations have no stock or orders. These records support catalogue browsing and queries for inactive products; they do not imply retail unavailability.

## Name usage

[Apple's trademark guidelines](https://www.apple.com/legal/intellectual-property/guidelinesfor3rdparties.html) describe permitted referential uses in publications and noncommercial informational websites, subject to their conditions. Keep TraceyDB as the project's own name, preserve correct product-name spelling, retain attribution and the independence notice, and avoid implying endorsement. Those guidelines are not a blanket licence for logos, images or commercial branding.

## Expanded catalogue sources and scope

The expanded catalogue has 1,512 configurations across 172 model and chip/case variants. Each additional record in `catalogue.json` cites an Apple technical specification or model-identification page. Storage is extracted separately for each Mac chip tier to avoid assigning Max-only capacities to Pro chips. Source pages were checked on 22 October 2026. Public facts describe hardware, while all added supplier lots and stock records remain synthetic.

Apple Watch entries cover the GPS aluminium Series 3–12 and SE families, with case sizes distinguished, plus standard Ultra models. Bands, Hermès editions and additional cellular/material combinations are not exhaustively enumerated. Watch storage and AirPods storage are NULL in the structured schema. The provenance file distinguishes an unstated Watch capacity from storage that is inapplicable to the AirPods catalogue. AirPods finishes follow the official product appearance and Max specifications (https://support.apple.com/en-us/121205 and https://support.apple.com/en-us/126620).

The catalogue includes confirmed iPhone 18 Pro and Pro Max, with no invented standard iPhone 18 or Plus entry. MacBook Pro models use their verified Pro/Max chip tier; Ultra chips appear in supported desktop Macs. No MacBook Ultra, iPad Max or iPad Ultra product family is asserted. New 2026 entries remain catalogue-only; 106 older additional model variants receive illustrative stock and component-provenance records.

## Simplified representation

The source descriptions are consolidated into 146 product models and 1,453 SKU configurations. Chip, storage and colour distinguish configurations. Model name, family, release year describe the shared model; size distinctions remain in the name. Release month, connectivity, material and port options are outside scope. catalogue_sku_aliases.csv retains every source SKU mapping, including 59 aliases consolidated into equivalent configurations. NULL represents unavailable or inapplicable attributes; storage uses decimal GB. Original source labels remain in catalogue.json.

## Component expansion

Checked on 23 October 2026. Public examples motivating the assembly categories include [iPhone 15 Pro specifications](https://support.apple.com/en-au/111829), [MacBook Air specifications](https://www.apple.com/macbook-air/specs/) and [AirPods Pro 2 specifications](https://support.apple.com/en-au/111834). These pages establish examples of hardware categories, not the simulated bills of materials or supplier links. Existing chip names retain their catalogue sources. `component_assumptions.json` describes each additional assembly; `data_manifest.json` lists the planned inputs for every SKU. `tests/check_component_data.py` checks complete recorded input coverage, quantities, receipt dates and selected family exclusions.

Component quantities count individual parts or complete named assemblies, sets or pairs. For example, a quantity of 10 for an audio driver pair means 10 pairs. This fixed counting convention is defined here rather than stored in a per-component measurement column. Synthetic-data provenance applies to the dataset as a whole and is omitted from individual component names.
