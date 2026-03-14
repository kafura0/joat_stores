# Story 3.11 — Restaurant Bill Payment + Split Bill

## Status: done

## Implementation Summary

Adds bill settlement flow to the restaurant module. Customers can pay their
entire bill with a single M-Pesa STK Push, or the waiter can split the bill
across multiple payers. When all shares are settled, the session auto-closes.

## Components

### Model — `BillShare` (migration 0010_add_bill_share.py)
- `session` FK → TableSession; `payer_phone`; `amount`; `items_snapshot` (JSON)
- `status`: PENDING → PAID | CANCELLED
- `payment_transaction` FK → MpesaTransaction (nullable, SET_NULL)
- Composite index: `(store, session, status)`

### Views — TableSessionViewSet actions
| Action | Method | URL |
|--------|--------|-----|
| `bill` | GET | `/sessions/{id}/bill/` |
| `pay_bill` | POST | `/sessions/{id}/pay-bill/` |
| `split_bill` | POST | `/sessions/{id}/split-bill/` |

**bill**: Returns all non-cancelled DineInOrders for session, total, and
existing BillShares. Available at any session status.

**pay_bill**: Accepts `{"phone": "+254..."}`. Calculates total from live
orders, creates one BillShare, calls `initiate_payment()` with reference
`"bill-share-{share.id}"`. Returns 201 + BillShare.

**split_bill**: Accepts `{"shares": [{"payer_phone": "...", "amount": "...",
"items_snapshot": [...]}]}`. Creates one BillShare + one STK Push per entry.
Returns created shares + per-payer errors list (partial success allowed).

### Signal — `_handle_payment_confirmed` (apps.py)
New branch for `"bill-share-"` references:
1. Marks BillShare PAID + links MpesaTransaction
2. Checks if any PENDING shares remain for the session
3. If none remain → calls `session.transition(STATUS_CLOSED)` → session auto-closes

### Serializers
- `BillShareSerializer` — all fields read-only
- `SplitBillInputSerializer` — nested `ShareSerializer` for input validation

### Factories
- `BillShareFactory` added to `tests/factories.py`

## Tests (`test_bill_payment.py`)
- `test_bill_returns_orders_and_total` — 200, correct total
- `test_bill_includes_existing_shares` — shares list populated
- `test_pay_bill_creates_share_and_initiates_stk` — BillShare created, STK reference correct
- `test_pay_bill_missing_phone_returns_400`
- `test_pay_bill_closed_session_returns_400`
- `test_split_bill_creates_one_share_per_payer` — 2 shares, 2 STK Pushes
- `test_split_bill_invalid_payload_returns_400`
- `test_signal_marks_share_paid`
- `test_signal_auto_closes_session_when_all_shares_paid` — partial payment keeps session open
- `test_signal_handles_unknown_share_id_gracefully`

## Acceptance Criteria Verification
- AC1 ✅ GET bill/ returns itemized orders + total + existing shares
- AC2 ✅ pay-bill/ creates BillShare + initiates STK Push; reference = "bill-share-{id}"
- AC3 ✅ split-bill/ creates one share + STK Push per payer; partial success allowed
- AC4 ✅ payment_confirmed signal → PAID; all shares paid → session CLOSED
- AC5 ✅ CLOSED session → 400 on pay-bill
