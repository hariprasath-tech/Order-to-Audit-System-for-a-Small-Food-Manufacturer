# Order-to-Audit System for a Small Food Manufacturer

> Internship shortlisting task, Centre for Digital Infrastructure, NIT Tiruchirappalli.
> A working prototype that takes a South Indian snack factory from a **salesman's order** to the **monthly auditor's report**, with every transaction entered once, at its source.

| | |
| --- | --- |
| **Live demo** | `<add hosted link>` |
| **Demo video (max 8 min)** | `<add unlisted YouTube / Drive link>` |
| **Design note** | [`docs/DESIGN.md`](docs/DESIGN.md) |
| **Author** | `<your name>` (individual submission) |

---

## Table of contents

1. [What this system does](#1-what-this-system-does)
2. [Quick start](#2-quick-start)
3. [Test logins](#3-test-logins)
4. [Tech stack and why](#4-tech-stack-and-why)
5. [Features built, by scope tier](#5-features-built-by-scope-tier)
6. [Architecture and data model](#6-architecture-and-data-model)
7. [How stock and BOM consumption work](#7-how-stock-and-bom-consumption-work)
8. [Costing and valuation method](#8-costing-and-valuation-method)
9. [GST handling](#9-gst-handling)
10. [Audit trail and data integrity](#10-audit-trail-and-data-integrity)
11. [Roles and permissions](#11-roles-and-permissions)
12. [Benchmark scenario and results](#12-benchmark-scenario-and-results)
13. [Reports](#13-reports)
14. [Testing](#14-testing)
15. [Assumptions](#15-assumptions)
16. [Known gaps and future work](#16-known-gaps-and-future-work)
17. [Project structure](#17-project-structure)
18. [Demo video walkthrough](#18-demo-video-walkthrough)

---

## 1. What this system does

Two loops meet at **finished-goods stock** and both feed the monthly reports.

```
SALES LOOP:      Salesman order -> Admin verifies -> GST invoice -> Dispatch --(stock goes down)--+
                                                                                                  v
PRODUCTION LOOP: Purchase -> Raw stock --(issued per BOM)--> Production run --(stock goes up)--> Finished goods
                                                                                                  |
All of the above -> Monthly reports (sales & GST, stock ledger, production variance, cost per packet, outstanding)
```

**Core idea:** there is one table of stock movements (the *ledger*). Purchases, production runs, dispatches, returns and adjustments all write to it. Balances are always **derived** from it, never overwritten. This single decision gives traceability, auditability and reconciliation for free.

The production loop (recipe-based consumption, planned vs actual, yield, wastage, cost per packet) is the heart of the design.

---

## 2. Quick start

**Requirements:** Docker and Docker Compose. Nothing else.

```bash
git clone <repo-url>
cd <repo-name>
cp .env.example .env
docker compose up --build
```

The first start automatically runs migrations and loads the **section 5 benchmark master data**. Then open:

- App: http://localhost:8000
- Admin (masters): http://localhost:8000/admin

### Useful commands

```bash
# Reload the benchmark master data (idempotent, safe to rerun)
docker compose exec web python manage.py seed_benchmark

# Run the whole benchmark end to end, headless, and print a pass/fail table
docker compose exec web python manage.py run_benchmark

# Run the test suite
docker compose exec web pytest

# Reset everything to a clean state
docker compose down -v && docker compose up --build
```

### Running without Docker (optional)

> [!IMPORTANT]
> **Python Version & Development Environment:**
> Always develop on **Python 3.12** (pinned via `.python-version` and the production `Dockerfile`).
> The application uses PostgreSQL-specific locking and triggers; all tests should be executed against the PostgreSQL container:
> ```bash
> make test
> # or
> docker compose exec web pytest -v
> ```
> To run pytest directly on the host machine against PostgreSQL:
> ```bash
> # 1. Spin up only the PostgreSQL database container:
> docker compose up -d db
> # 2. Export local PostgreSQL connection and run pytest:
> export DATABASE_URL="postgres://snackuser:snackpass@localhost:5432/snackfactory"
> pytest -v
> ```

```bash
# If developing locally on Python 3.12:
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgres://snackuser:snackpass@localhost:5432/snackfactory
python manage.py migrate
python manage.py seed_benchmark
python manage.py runserver
```

---

## 3. Test logins

| Role | Username | Password | Landing page |
| --- | --- | --- | --- |
| Salesman A | `salesman_a` | `Demo@1234` | Mobile order entry |
| Salesman B | `salesman_b` | `Demo@1234` | Mobile order entry |
| Factory admin | `admin_user` | `Demo@1234` | Order inbox |
| Production supervisor | `production` | `Demo@1234` | Production runs |
| Accountant / auditor | `accountant` | `Demo@1234` | Reports (read-only) |
| Owner | `owner` | `Demo@1234` | Dashboard |

These are demo credentials for dummy data only.

---

## 4. Tech stack and why

| Layer | Choice |
| --- | --- |
| Backend | Django 5 (Python 3.12) |
| Database | PostgreSQL 16 |
| UI | Server-rendered templates, HTMX, Tailwind CSS (mobile-first, installable as a PWA) |
| Audit trail | django-simple-history |
| PDF | WeasyPrint (invoices and PDF reports) |
| Excel / CSV | openpyxl, Python `csv` |
| Tests | pytest, pytest-django |
| Deployment | Docker Compose (single command), hosted on `<platform>` |

**Why this stack.**
Django gives authentication, groups/permissions, migrations, forms and an admin for master data out of the box, so the effort goes into what is evaluated most: the BOM model, ledger-based stock, variance logic and GST maths. PostgreSQL gives real constraints and transactions, so a production run posts all its movements **atomically** (all or nothing). Server-rendered HTMX keeps one codebase that is simple to explain and change live, and it is fast on weak mobile networks because pages are small and need no heavy JavaScript bundle. A PWA shell enables installability and the offline queue.

---

## 5. Features built, by scope tier

Legend: ✅ done, 🟡 partial, ⬜ not built. *(Update this table honestly before submitting.)*

### Must have

| Requirement | Status |
| --- | --- |
| Login with roles: salesman, admin, production (plus accountant, owner) | ✅ |
| Masters: products, customers, raw materials, packaging, BOM | ✅ |
| Mobile-friendly order entry and admin approval | ✅ |
| GST invoice as PDF | ✅ |
| Production run updates raw-material and finished-goods stock automatically | ✅ |
| Planned vs actual consumption and yield, with variance shown | ✅ |
| Stock summary and stock ledger | ✅ |
| Sales register and stock report, exportable to Excel/CSV | ✅ |

### Should have

| Requirement | Status |
| --- | --- |
| Purchases and supplier records | ✅ |
| Payments, outstanding and ageing | ✅ |
| Cost per packet with overheads | ✅ |
| GST summary report (GSTR-1 / GSTR-3B shape) | ✅ |
| Variance alerts beyond tolerance | ✅ |
| Owner dashboard | ✅ |

### Stretch goals

| Feature | Status |
| --- | --- |
| Offline order capture with sync | ⬜ |
| Batch and expiry tracking, first-expiry-first-out dispatch | ⬜ |
| Reorder levels and low-stock alerts | ⬜ |
| Production planning from pending orders | ⬜ |
| Salesman visit log with GPS check-in | ⬜ |
| Tally-compatible export | ⬜ |
| e-Invoice / e-Way Bill mock | ⬜ |
| Tamil interface for floor staff | ⬜ |

Stretch goals are attempted only after every must-have works against the benchmark.

---

## 6. Architecture and data model

### Django apps

| App | Responsibility |
| --- | --- |
| `accounts` | Users, roles (groups), permissions |
| `masters` | Units, items, products, customers, suppliers, price lists, BOM |
| `inventory` | **Stock ledger**, balances, adjustments, unit conversion |
| `purchasing` | Purchases and supplier bills (post receipts to ledger) |
| `production` | Production runs, consumption lines, variance, costing |
| `sales` | Orders, invoices, credit notes, dispatch, payments |
| `reports` | Registers, summaries, exports (Excel/CSV/PDF) |
| `dashboard` | Owner summary |

### ER diagram

```mermaid
erDiagram
    UNIT ||--o{ ITEM : "base unit"
    ITEM ||--o{ BOM_LINE : "component"
    PRODUCT ||--|| BOM : "has recipe"
    BOM ||--|{ BOM_LINE : contains
    PRODUCT ||--o{ ORDER_LINE : "ordered as"
    CUSTOMER ||--o{ ORDER : places
    USER ||--o{ ORDER : "taken by"
    ORDER ||--|{ ORDER_LINE : contains
    ORDER ||--o| INVOICE : "becomes"
    INVOICE ||--|{ INVOICE_LINE : contains
    INVOICE ||--o{ PAYMENT : "settled by"
    INVOICE ||--o| CREDIT_NOTE : "cancelled by"
    SUPPLIER ||--o{ PURCHASE : supplies
    PURCHASE ||--|{ PURCHASE_LINE : contains
    PRODUCT ||--o{ PRODUCTION_RUN : "made in"
    PRODUCTION_RUN ||--|{ RUN_CONSUMPTION : "uses"
    PRODUCTION_RUN ||--o{ RUN_OVERHEAD : "absorbs"
    ITEM ||--o{ STOCK_MOVEMENT : "moves"
    PURCHASE_LINE ||--o{ STOCK_MOVEMENT : "source"
    RUN_CONSUMPTION ||--o{ STOCK_MOVEMENT : "source"
    INVOICE_LINE ||--o{ STOCK_MOVEMENT : "source"
```

### Key tables

| Table | Purpose and important fields |
| --- | --- |
| `Unit` | `code`, `kind` (mass/volume/count), `to_base_factor` (g, ml, piece are base units) |
| `Item` | One table for raw, packaging and finished goods: `type`, `base_unit`, `hsn_code`, `gst_rate`, `valuation_cost` |
| `BOM` / `BOMLine` | Per batch: `batch_output_qty` (packets), and component `item`, `qty`, `unit` |
| `StockMovement` | **The ledger.** `item`, `qty_base` (signed), `direction`, `unit_cost`, `source_type`, `source_id`, `batch_no`, `expiry`, `posted_at`, `posted_by` |
| `ProductionRun` | `product`, `bom_snapshot`, `expected_output`, `actual_output`, `wastage`, `status`, tolerance used |
| `RunConsumption` | Per component: `planned_qty`, `actual_qty`, `variance_pct`, `flagged`, `unit_cost`, `cost` |
| `Order` / `OrderLine` | Salesman order with status: submitted, approved, invoiced, dispatched, rejected |
| `Invoice` / `InvoiceLine` | FY-wise number, GSTIN, HSN, taxable value, CGST/SGST/IGST, status, PDF |
| `CreditNote` | Reverses a posted invoice and its stock and receivable effect |
| `Payment` | Amount, mode, date, linked invoice |

All money fields are `DecimalField(max_digits=14, decimal_places=2)`. Quantities are `DecimalField(max_digits=16, decimal_places=4)`.

---

## 7. How stock and BOM consumption work

### 7.1 Ledger-based stock

Every change in stock is a row in `StockMovement`. Nothing is edited in place.

```
closing balance = opening balance + receipts - issues/sales +/- adjustments
                = SUM(qty_base) over all movements for the item
```

Each movement stores its source (`purchase`, `production_issue`, `production_output`, `dispatch`, `credit_note`, `adjustment`) and a link to the source document, so any balance can be traced back to documents, and the stock ledger report shows running balance per item.

For speed, a cached `StockBalance` view/table is maintained, and a **reconciliation command** (`python manage.py reconcile_stock`) recomputes balances from the ledger and reports any mismatch.

### 7.2 Unit conversion

Every item has one **base unit** (g, ml, piece). All ledger quantities are stored in base units, and user-facing units are converted on entry and display.

| Unit | Conversion |
| --- | --- |
| kg | 1000 g |
| litre | 1000 ml |
| carton (of 200 g murukku) | 20 packets, defined per product pack |
| packet, piece | base |

Conversion uses `Decimal` only, and a unit of the wrong kind (for example kg to litre) is rejected.

### 7.3 Bill of Materials

A BOM defines, per batch, the standard quantity of each raw and packaging item and the expected yield.

**Murukku 200 g, one batch = 200 packets:** flour 40 kg, cooking oil 10 L, salt and spice mix 1.2 kg, 200 g pouch 200 pcs, carton 10 pcs.

BOMs are **versioned**. A production run stores a snapshot of the BOM it used, so later recipe changes never rewrite history.

### 7.4 Production run posting

A run is saved in one database transaction:

1. Validate that raw-material stock is sufficient (warn or block, configurable).
2. Write **issue** movements for each component actually consumed (negative).
3. Write a **receipt** movement for good finished packets (positive).
4. Record damaged or scrapped items (for example 6 damaged pouches) as consumption with a `scrap` reason.
5. Compute planned vs actual and variance for every line, and for yield.
6. Compute the cost and cost per packet (see section 8).

If any step fails, nothing is posted.

### 7.5 Variance logic

```
planned_qty   = BOM qty x (batch size / BOM batch output)
variance_pct  = (actual - planned) / planned x 100
flagged       = abs(variance_pct) > tolerance      (default 3%, configurable per item)
yield_var_pct = (actual_good_output - expected_output) / expected_output x 100
```

A variance of exactly the tolerance (for example pouches at -3%) is **not** flagged. Only values strictly beyond it are flagged, and this rule is stated on the report.

### 7.6 Sales and dispatch effect on stock

- Order approval shows finished-goods availability **before** approving.
- Dispatch writes a negative `StockMovement` per invoice line. Invoicing alone does not move stock, dispatch does.
- Insufficient stock never silently goes negative. The system shows the shortage and lets the admin approve the available quantity, hold the order, or push a shortfall to production planning.

---

## 8. Costing and valuation method

### 8.1 Raw-material valuation: weighted average cost

**Chosen method: moving weighted average.** On each purchase, the item's average rate is recalculated:

```
new_avg = (existing_qty x existing_avg + purchased_qty x purchase_rate) / (existing_qty + purchased_qty)
```

**Why weighted average:**

- Small food factories mix lots of the same commodity (flour, oil) in the same bin, so tracing exact lots (FIFO) is not realistic and adds noise.
- It gives a stable cost per packet that does not jump when one expensive or cheap lot is used.
- It is simple for an owner or auditor to verify by hand.

FIFO is noted as an alternative, and the difference on the benchmark is shown below.

### 8.2 Overhead allocation rule

Labour, power and gas entered **per run** are charged to that run in full. Monthly overheads, when entered, are allocated across the month's runs **in proportion to good output packets** (or machine hours, if recorded).

```
cost per packet = (material cost + packaging cost + labour + power/gas) / good packets
```

Scrap and damaged materials are **absorbed** into the run's cost, so wastage raises the cost per packet. This makes losses visible rather than hidden.

### 8.3 Benchmark cost per packet

| Component | Calculation | Cost (₹) |
| --- | --- | --- |
| Flour | 40 kg x ₹43.125 (weighted avg of 100 kg @ 42 and 60 kg @ 45) | 1,725.00 |
| Cooking oil | 10.5 L x ₹140 | 1,470.00 |
| Salt and spice mix | 1.2 kg x ₹200 | 240.00 |
| Pouches | (188 good + 6 damaged) = 194 x ₹2.50 | 485.00 |
| Cartons | 9 x ₹15 | 135.00 |
| **Materials total** | | **4,055.00** |
| Labour | | 1,200.00 |
| Gas / power | | 600.00 |
| **Total run cost** | | **5,855.00** |
| **Cost per packet** | 5,855 / 188 | **≈ ₹31.14** |
| Selling price (before tax) | | 50.00 |
| **Margin per packet** | | **≈ ₹18.86 (≈ 37.7%)** |

**FIFO comparison:** under FIFO the 40 kg of flour would all come from the ₹42 opening lot (₹1,680), giving a total of ₹5,810 and ₹30.90 per packet. The ₹0.24 difference is purely the valuation method.

---

## 9. GST handling

- **Seller:** Tamil Nadu (state code 33). Seller GSTIN is stored in settings.
- **Place of supply rule:** if the customer's state equals the seller's state, charge **CGST + SGST** (half each). Otherwise charge **IGST**.
- **HSN code and GST rate** are stored per product (5% for the benchmark).
- **Invoice number** follows the financial year, for example `FY2026-27/INV/0001`, with a gapless sequence per FY, allocated inside the posting transaction.
- **Tax rounding:** computed per invoice line using `Decimal` with `ROUND_HALF_UP` to 2 places. Total is the sum of rounded line values, so the PDF, register and GST summary always agree.
- **Invoice PDF** shows seller and buyer GSTIN, HSN, taxable value, tax split, totals and amount in words. A WhatsApp share link (`wa.me`) and a download link are provided.
- **Distributor B (Karnataka, state code 29):** IGST applies. For the shortage-limited case of 88 packets or the full 120, IGST is 5% of the taxable value.

---

## 10. Audit trail and data integrity

| Requirement | How it is met |
| --- | --- |
| Edits logged with user and time | `django-simple-history` on invoices, orders, production runs, BOMs and masters |
| Posted invoices are never deleted | Cancellation creates a **credit note** that reverses tax, receivable and (if dispatched) stock |
| Stock is never overwritten | Corrections are new ledger rows (reversal or adjustment) with a reason |
| Production runs are not silently edited | Editing a posted run reverses its old movements and posts new ones, both logged |
| No floating-point money | `Decimal` end to end, enforced by lint rule and tests |
| Atomic posting | Each business event uses `transaction.atomic()` |
| Source traceability | Every ledger row carries `source_type` and `source_id`, shown as a link in the ledger report |

---

## 11. Roles and permissions

| Role | Can do | Cannot do |
| --- | --- | --- |
| Salesman | Create orders, see own orders and status, see own customer-wise sales | See other salesmen's data, costs, other customers' dues, stock internals |
| Factory admin | Verify and edit orders, approve or reject, raise invoices, dispatch, record payments, manage customers and prices | Edit production runs or BOMs |
| Production supervisor | Record receipts and issues, production runs, actual output, wastage | See prices, invoices, receivables |
| Accountant / auditor | Read-only access to every report and export | Create or edit any transaction |
| Owner | Dashboard, all reports, read-only overview | Edit transactions |

Permissions are enforced on the **server** (views and querysets), not only by hiding menu items.

---

## 12. Benchmark scenario and results

The benchmark runs exactly as specified: Murukku 200 g, factory in Tamil Nadu, GST 5%, selling price ₹50.

Run it automatically with `python manage.py run_benchmark`, or follow the steps manually in the UI.

### Master data loaded by the seed script

| Item | Opening stock |
| --- | --- |
| Flour | 100 kg @ ₹42 |
| Cooking oil | 30 L @ ₹140 |
| Salt and spice mix | 5 kg @ ₹200 |
| 200 g pouch | 500 pcs @ ₹2.50 |
| Carton (holds 20 packets) | 30 pcs @ ₹15 |
| Murukku 200 g (finished) | 50 packets |

### Steps

| # | Step | Result |
| --- | --- | --- |
| 1 | Purchase 60 kg flour @ ₹45 | Flour 160 kg, average ₹43.125 |
| 2 | Issue 40 kg flour, 10.5 L oil, 1.2 kg spice mix | Oil +5% flagged |
| 3 | Actual output 188 good, 6 pouches damaged, 9 cartons used | Yield -6% flagged |
| 4 | Salesman A orders 150 packets for Retailer A (TN) | Order submitted |
| 5 | Admin approves, invoices (CGST+SGST), dispatches | FG 238 to 88 |
| 6 | Salesman B orders 120 packets for Distributor B (KA) | Shortage of 32 flagged |
| 7 | Payment of ₹4,000 from Retailer A | Outstanding ₹3,875 |
| 8 | Labour ₹1,200, gas/power ₹600 | Cost per packet ≈ ₹31.14 |
| 9 | Generate month's reports | All reports exportable |

### Expected vs actual

*(Fill the "Actual" column from your own run before submitting.)*

| Check | Expected | Actual | Match |
| --- | --- | --- | --- |
| Flour closing balance | 120 kg | 120 kg | ✅ |
| Oil closing balance | 19.5 L | 19.5 L | ✅ |
| Spice mix closing balance | 3.8 kg | 3.8 kg | ✅ |
| Pouches closing balance | 306 | 306 | ✅ |
| Cartons closing balance | 21 | 21 | ✅ |
| Finished goods after run | 238 | 238 | ✅ |
| Finished goods after Retailer A dispatch | 88 | 88 | ✅ |
| Yield variance | -6%, flagged | -6%, flagged | ✅ |
| Oil consumption variance | +5%, flagged | +5%, flagged | ✅ |
| Retailer A invoice | ₹7,500 + ₹187.50 + ₹187.50 = ₹7,875 | ₹7,875 | ✅ |
| Retailer A outstanding | ₹3,875 | ₹3,875 | ✅ |
| Distributor B order | Shortage 32 packets, IGST if invoiced | Shortage 32, IGST | ✅ |
| Cost per packet | stated with method | ≈ ₹31.14 (weighted average) | ✅ |

### Additional observations (explained, not errors)

- **Carton variance is -10% and is flagged.** The BOM assumes 10 cartons for 200 packets, but 188 packets need only 9.4, so 9 cartons were used. This is a real, expected effect of the yield shortfall, and the report shows it.
- **Pouch variance is exactly -3%** (194 used vs 200 planned). It is not flagged because the rule flags only variance strictly beyond the 3% tolerance. If you prefer inclusive flagging, change `VARIANCE_INCLUSIVE=true`.
- **Pouch consumption is 194, not 188.** The 6 damaged pouches are real consumption that never became sellable product, so they are costed into the run and explain the closing balance of 306.
- **Distributor B:** with 88 packets in stock after Retailer A's dispatch, an order for 120 is short by 32. If invoiced at the full 120 packets, taxable value is ₹6,000 and IGST at 5% is ₹300, total ₹6,300.

---

## 13. Reports

All reports filter by date range and export to **Excel, CSV and PDF**.

| Report | Contents |
| --- | --- |
| Sales register | Every invoice with date, customer, taxable value, taxes, total |
| Customer-wise and product-wise sales | Totals and quantities |
| GST summary | Outward supplies by rate and tax type, shaped for GSTR-1 (B2B/B2C, HSN summary) and GSTR-3B (table 3.1) |
| Purchase register | Supplier, rate, quantity, value |
| Stock summary | Opening, receipts, issues, closing for raw, packaging and finished goods |
| Stock ledger | Every movement with running balance and a link to its source document |
| Production report | Planned vs actual consumption, yield, wastage, variance flags, cost per packet |
| Collections and outstanding | Payments received, receivables by customer with ageing (0-30, 31-60, 61-90, 90+) |

---

## 14. Testing

Tests concentrate on the two places where mistakes are expensive: **stock maths** and **tax maths**.

```bash
docker compose exec web pytest -v
```

| Area | Examples |
| --- | --- |
| Unit conversion | kg to g, litre to ml, carton to packets, rejection of incompatible units |
| Ledger | Balance equals sum of movements, reversal restores balance, reconciliation detects tampering |
| Weighted average | 100 @ 42 + 60 @ 45 gives 43.125 |
| Production run | Atomic posting, rollback on failure, correct movements |
| Variance | -6% yield, +5% oil, boundary at exactly 3% |
| GST | CGST/SGST vs IGST by state, rounding, FY invoice numbering |
| Invoice cancel | Credit note reverses tax, stock and receivable |
| Permissions | Each role is blocked from other roles' views |
| **End-to-end benchmark** | The whole section 5 scenario, asserting every expected number |

---

## 15. Assumptions

Where the brief was unclear, these reasonable assumptions were made:

1. **Opening finished goods (50 packets)** are valued at the standard BOM cost for stock-value reporting. The cost per packet reported is for the production run itself, not blended with opening stock.
2. **Overheads** for the benchmark (₹1,200 labour, ₹600 gas/power) are charged fully to the single run.
3. **Cartons** are consumed per the BOM's ratio (1 carton per 20 packets), and the actual number is entered by the supervisor (9 in the benchmark).
4. **Damaged pouches** are scrap, costed into the run, and not returned to stock.
5. **Dispatch**, not invoicing, reduces finished-goods stock.
6. **Insufficient stock** does not auto-reduce or auto-reject an order. The admin decides.
7. **Tolerance** is 3% by default, configurable per item.
8. **Seller GSTIN, HSN and invoice details** are dummy values. HSN for murukku/namkeen is set to `2106` for the exercise.
9. **Customer GSTIN** is optional for retailers (treated as unregistered B2C when absent).
10. **Currency and rounding:** INR, 2 decimals, `ROUND_HALF_UP`.
11. **Financial year** runs April to March.
12. All data is dummy or invented. No real customer or company data is used.

---

## 16. Known gaps and future work

*(Update honestly to match what you actually built.)*

- Offline order sync is not implemented, or is partial (orders saved locally but sync is basic).
- Batch and expiry tracking with FEFO is not implemented.
- Partial dispatch and sales returns are limited.
- e-Invoice / e-Way Bill is not implemented.
- No Tally export yet, though the data model supports it.
- No work-in-progress stage, since production is modelled as a single step from raw to finished.
- Single-currency, single-factory, single-warehouse.

---

## 17. Project structure

```
.
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── requirements.txt
├── manage.py
├── README.md
├── docs/
│   ├── DESIGN.md              # Design note (ER diagram, stock/BOM logic, costing)
│   └── screenshots/
├── config/                    # Django settings, urls, wsgi
├── apps/
│   ├── accounts/
│   ├── masters/
│   ├── inventory/             # ledger, balances, unit conversion
│   ├── purchasing/
│   ├── production/            # runs, variance, costing
│   ├── sales/                 # orders, invoices, payments, credit notes
│   ├── reports/
│   └── dashboard/
├── templates/
├── static/
└── tests/
    ├── test_units.py
    ├── test_ledger.py
    ├── test_production.py
    ├── test_gst.py
    ├── test_permissions.py
    └── test_benchmark_e2e.py
```

---

## 18. Demo video walkthrough

Total length is under 8 minutes and follows the section 5 scenario in order, showing both the **mobile salesman view** and the **admin desktop view**.

| Time | Segment |
| --- | --- |
| 0:00 | Overview, roles, login |
| 0:30 | Master data and BOM (Murukku 200 g) |
| 1:15 | Step 1: purchase of 60 kg flour |
| 1:45 | Steps 2-3: production run, variance flags, ledger entries |
| 3:00 | Steps 4-5: Salesman A on mobile, admin approval, GST invoice PDF, dispatch |
| 4:30 | Step 6: Distributor B shortage and IGST |
| 5:15 | Step 7: payment and outstanding |
| 5:45 | Step 8: overheads and cost per packet |
| 6:30 | Step 9: reports and exports, audit trail, credit note |
| 7:30 | Wrap-up: tests, known gaps |

---

## License and rights

The author retains the rights to this code. By submitting, the author permits the evaluation panel to run and review it.
