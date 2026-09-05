from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vyapaar.domain import (  # noqa: E402
    CanonicalSku,
    ClarificationContext,
    ClarificationOption,
    ConfirmationInput,
    DomainError,
    DraftCommand,
    DraftCustomer,
    DraftDate,
    DraftItem,
    EntityCandidate,
    PackDefinition,
    PricedLine,
    ResolutionStatus,
    WorkflowState,
    calculate_line,
    calculate_order,
    calculate_updated_balance,
    can_transition,
    create_idempotency_key,
    next_clarification,
    plan_confirmation,
    resolve_entity,
    resolve_relative_date,
    to_base_units,
    transition,
    validate_draft_command,
)


NOW = datetime(2026, 9, 5, 8, tzinfo=timezone.utc)


def valid_payload() -> dict:
    return {
        "intent": "create_sales_order",
        "customer": {"spoken_name": "Ramesh", "candidate_id": "cus_ramesh", "confidence": 0.96, "evidence": "Ramesh ko"},
        "delivery_date": {"value": "2026-09-06", "confidence": 0.99, "evidence": "kal ke liye"},
        "items": [
            {"spoken_name": "Sprite", "candidate_sku_id": "sku_sprite", "quantity": 2, "unit": "peti", "quoted_unit_price": None, "confidence": 0.94, "evidence": "2 peti Sprite"}
        ],
        "mentioned_previous_balance": None,
        "collection_amount": None,
        "collection_evidence": "",
        "currency": "INR",
        "missing_fields": [],
        "warnings": [],
    }


def valid_draft(**changes) -> DraftCommand:
    parsed = validate_draft_command(valid_payload())
    assert parsed.value is not None
    values = {
        "customer": parsed.value.customer,
        "delivery_date": parsed.value.delivery_date,
        "items": parsed.value.items,
        "mentioned_previous_balance": parsed.value.mentioned_previous_balance,
        "collection_amount": parsed.value.collection_amount,
        "collection_evidence": parsed.value.collection_evidence,
        "intent": parsed.value.intent,
        "currency": parsed.value.currency,
        "missing_fields": parsed.value.missing_fields,
        "warnings": parsed.value.warnings,
    }
    values.update(changes)
    return DraftCommand(**values)


class DraftValidationTests(unittest.TestCase):
    def test_valid_and_explicitly_unresolved_drafts_are_typed(self) -> None:
        payload = valid_payload()
        payload["customer"]["candidate_id"] = None
        payload["items"][0]["candidate_sku_id"] = None
        payload["items"][0]["unit"] = None
        payload["delivery_date"]["value"] = None
        payload["missing_fields"] = ["customer.candidate_id", "items.0.unit", "delivery_date.value"]
        result = validate_draft_command(payload)
        self.assertTrue(result.ok)
        self.assertIsNone(result.value.customer.candidate_id if result.value else "missing")

    def test_malformed_extractor_output_collects_stable_errors(self) -> None:
        payload = valid_payload()
        payload["currency"] = "USD"
        payload["items"][0]["quantity"] = -1
        result = validate_draft_command(payload)
        self.assertFalse(result.ok)
        self.assertEqual([error.code for error in result.errors], ["UNSUPPORTED_CURRENCY", "INVALID_QUANTITY"])


class WorkflowTests(unittest.TestCase):
    def test_only_declared_transitions_are_allowed(self) -> None:
        self.assertTrue(can_transition(WorkflowState.UPLOADED, WorkflowState.TRANSCRIBING))
        self.assertTrue(can_transition(WorkflowState.NEEDS_CLARIFICATION, WorkflowState.VALIDATING))
        self.assertFalse(can_transition(WorkflowState.READY_FOR_REVIEW, WorkflowState.COMMITTED))
        with self.assertRaisesRegex(DomainError, "cannot transition") as raised:
            transition(WorkflowState.COMMITTED, WorkflowState.VALIDATING)
        self.assertEqual(raised.exception.code, "INVALID_STATE_TRANSITION")


class ResolutionAndDateTests(unittest.TestCase):
    def test_alias_resolution_is_merchant_scoped_and_close_ties_are_ambiguous(self) -> None:
        candidates = (
            EntityCandidate("small", "mer_1", "Sprite 250ml", ("Sprite peti",), 0.8, 1),
            EntityCandidate("large", "mer_1", "Sprite 750ml", ("Sprite large",), 0.2, 0.1),
            EntityCandidate("foreign", "mer_2", "Sprite", ("Sprite peti",), 1, 1),
        )
        exact = resolve_entity("mer_1", " SPRITE, PETI! ", candidates, extraction_confidence=0.95)
        self.assertEqual(exact.status, ResolutionStatus.RESOLVED)
        self.assertEqual(exact.candidate.entity.id if exact.candidate else None, "small")
        tied = resolve_entity("mer_1", "coke", (
            EntityCandidate("a", "mer_1", "Coke"), EntityCandidate("b", "mer_1", "Coke")
        ))
        self.assertEqual(tied.status, ResolutionStatus.AMBIGUOUS)
        self.assertEqual(resolve_entity("mer_1", "unknown", candidates).status, ResolutionStatus.UNRESOLVED)

    def test_relative_dates_use_merchant_day_and_horizon(self) -> None:
        boundary = datetime(2026, 9, 5, 20, tzinfo=timezone.utc)  # Sep 6 in Kolkata.
        self.assertEqual(resolve_relative_date("kal ke liye", "Asia/Kolkata", now=boundary).isoformat(), "2026-09-07")
        with self.assertRaises(DomainError) as past:
            resolve_relative_date("2026-09-05", "Asia/Kolkata", now=boundary)
        self.assertEqual(past.exception.code, "DATE_OUT_OF_HORIZON")
        with self.assertRaises(DomainError) as invalid:
            resolve_relative_date("someday", "Asia/Kolkata", now=boundary)
        self.assertEqual(invalid.exception.code, "UNSUPPORTED_DATE")


class PolicyAndMoneyTests(unittest.TestCase):
    def test_policy_returns_only_highest_priority_question(self) -> None:
        draft = valid_draft(
            customer=DraftCustomer("Ramesh", None, 0.4, "Ramesh"),
            items=(DraftItem("Coke", "sku_coke", 4, None, 0.9, "4 Coke"),),
        )
        question = next_clarification(draft, ClarificationContext(
            "Asia/Kolkata", NOW,
            customer_options=(ClarificationOption("a", "Ramesh Stores"), ClarificationOption("b", "Ramesh Traders")),
        ))
        self.assertEqual(question.code if question else None, "AMBIGUOUS_CUSTOMER")
        self.assertEqual(question.field_path if question else None, "customer.candidate_id")

        unit_question = next_clarification(
            valid_draft(items=(DraftItem("Coke", "sku_coke", 4, None, 0.9, "4 Coke"),)),
            ClarificationContext("Asia/Kolkata", NOW),
        )
        self.assertEqual(unit_question.code if unit_question else None, "MISSING_UNIT")
        self.assertEqual(len(unit_question.options) if unit_question else 0, 2)

    def test_balance_and_stock_are_clarified(self) -> None:
        balance = next_clarification(
            valid_draft(mentioned_previous_balance=Decimal("12500")),
            ClarificationContext("Asia/Kolkata", NOW, system_balance=Decimal("11000")),
        )
        self.assertEqual(balance.code if balance else None, "BALANCE_MISMATCH")
        stock = next_clarification(
            valid_draft(),
            ClarificationContext(
                "Asia/Kolkata", NOW, stock_by_sku_id={"sku_sprite": 40},
                pack_by_sku_id={"sku_sprite": PackDefinition("bottle", 24)},
            ),
        )
        self.assertEqual(stock.code if stock else None, "INSUFFICIENT_STOCK")

    def test_pack_and_decimal_money_math_reconcile(self) -> None:
        self.assertEqual(to_base_units(2, "peti", PackDefinition("bottle", 24)), 48)
        self.assertEqual(to_base_units(2, "dozen", PackDefinition("piece")), 24)
        line = calculate_line(PricedLine("sku", 2, Decimal("1.01"), tax_basis_points=500))
        self.assertEqual((line.subtotal, line.tax, line.total), (Decimal("2.02"), Decimal("0.10"), Decimal("2.12")))
        totals = calculate_order((PricedLine("a", 1, Decimal("100")), PricedLine("b", 2, Decimal("25"))))
        self.assertEqual(totals.total, Decimal("150.00"))
        self.assertEqual(calculate_updated_balance(Decimal("12500"), totals.total), Decimal("12650.00"))


class ConfirmationTests(unittest.TestCase):
    def input(self, **changes) -> ConfirmationInput:
        values = {
            "merchant_id": "mer_1", "voice_job_id": "job_1", "draft_revision": 3, "confirmed_revision": 3,
            "draft": valid_draft(), "order_id": "ord_1", "invoice_id": "inv_1", "invoice_number": "VL-1042",
            "customer_id": "cus_ramesh", "customer_balance": Decimal("12500"),
            "skus_by_id": {"sku_sprite": CanonicalSku("sku_sprite", "Sprite 250ml", "bottle", Decimal("10"), 100, 24)},
            "time_zone": "Asia/Kolkata", "now": NOW,
        }
        values.update(changes)
        return ConfirmationInput(**values)

    def test_idempotency_is_stable_and_revision_scoped(self) -> None:
        first = create_idempotency_key("merchant", "job", 2)
        self.assertEqual(first, create_idempotency_key("merchant", "job", 2))
        self.assertNotEqual(first, create_idempotency_key("merchant", "job", 3))
        self.assertNotEqual(create_idempotency_key("a:b", "c", 1), create_idempotency_key("a", "b:c", 1))

    def test_plan_contains_one_reconciled_atomic_effect_set(self) -> None:
        plan = plan_confirmation(self.input())
        self.assertEqual(plan.lines[0].base_quantity, 48)
        self.assertEqual(plan.totals.total, Decimal("480.00"))
        self.assertEqual(plan.inventory_movements[0].delta_base_units, -48)
        self.assertEqual(plan.invoice_total, plan.ledger_entry.amount)
        self.assertEqual(plan.ledger_entry.balance_after, Decimal("12980.00"))
        self.assertEqual(plan.outbox_event["idempotency_key"], plan.idempotency_key)

    def test_stale_revision_and_aggregate_stock_shortage_are_rejected(self) -> None:
        with self.assertRaises(DomainError) as stale:
            plan_confirmation(self.input(confirmed_revision=2))
        self.assertEqual(stale.exception.code, "STALE_DRAFT")

        original = valid_draft().items[0]
        repeated = valid_draft(items=(original, original))
        low_stock = {"sku_sprite": CanonicalSku("sku_sprite", "Sprite", "bottle", Decimal("10"), 60, 24)}
        with self.assertRaises(DomainError) as shortage:
            plan_confirmation(self.input(draft=repeated, skus_by_id=low_stock))
        self.assertEqual(shortage.exception.code, "INSUFFICIENT_STOCK")


if __name__ == "__main__":
    unittest.main()
