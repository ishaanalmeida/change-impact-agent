# Evaluation

108 change-impact questions (15 supplier losses, 93 part changes), scored against the generator's ground truth. Mean precision / recall per question.

| Method | Supplier parts P / R | Products P / R | Customers P / R | Open issues P / R |
|---|---|---|---|---|
| Ontology + entity resolution | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| Key joins only (baseline) | 0.60 / 0.54 | 0.94 / 0.94 | 0.94 / 0.51 | 0.93 / 0.91 |
| Entity resolution, direct BOM parents only | 1.00 / 1.00 | 0.29 / 0.14 | 0.29 / 0.21 | 1.00 / 1.00 |

## Entity resolution, record level

| Check | Score |
|---|---|
| ERP vendor records -> suppliers (pairwise P/R) | 1.00 / 1.00 |
| MES description-only records matched correctly | 1.00 |
| CRM installations matched to the right product | 1.00 |
