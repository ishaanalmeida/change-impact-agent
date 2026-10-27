# Held-out evaluation, seeds 21-30

Mean over seeds (worst seed in brackets).

| Method or check | Scores |
|---|---|
| Ontology + entity resolution | 1.00 (1.00)  0.99 (0.96)  1.00 (1.00)  1.00 (0.99)  1.00 (1.00)  1.00 (1.00)  1.00 (1.00)  1.00 (1.00) |
| Key joins only (baseline) | 0.67 (0.40)  0.58 (0.40)  0.95 (0.92)  0.95 (0.92)  0.94 (0.86)  0.50 (0.32)  0.92 (0.87)  0.89 (0.85) |
| Entity resolution, direct BOM parents only | 1.00 (1.00)  0.99 (0.96)  0.27 (0.15)  0.16 (0.04)  0.27 (0.15)  0.22 (0.10)  1.00 (1.00)  1.00 (1.00) |
| ERP vendor records -> suppliers (pairwise P/R) | 1.00 (1.00)  0.98 (0.90) |
| MES description-only records matched correctly | 1.00 (1.00) |
| CRM installations matched to the right product | 1.00 (1.00) |

## Resolver misses

- seed 23: Vortex Seals GmbH split across ["'Vortex Seal sGmbH'", "'Votrex Seals GmbH'"]
- seed 29: Kempen Electronics B.V. split across ["'Kempen Eelctronics B.V.'", "'Kempen Electronic sB.V.'"]
