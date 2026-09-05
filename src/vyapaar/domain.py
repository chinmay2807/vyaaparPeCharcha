"""Dependency-free business rules for the VyapaarPeCharcha MVP.

AI output is treated as untrusted proposal data.  The functions here validate
that proposal, decide whether clarification is needed, and produce a pure plan
of effects.  Persistence adapters remain responsible for executing that plan in
one transaction and looking up an existing result by its idempotency key.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from difflib import SequenceMatcher
from enum import StrEnum
from hashlib import sha256
import json
import re
import unicodedata
from typing import Any, Generic, Mapping, Sequence, TypeVar
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


T = TypeVar("T")
PAISE = Decimal("0.01")


class DomainError(ValueError):
    """A stable, client-safe domain failure."""

    def __init__(self, code: str, message: str, **details: object) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    path: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ValidationResult(Generic[T]):
    value: T | None = None
    errors: tuple[ValidationIssue, ...] = ()

    @property
    def ok(self) -> bool:
        return self.value is not None and not self.errors


@dataclass(frozen=True, slots=True)
class DraftCustomer:
    spoken_name: str
    candidate_id: str | None
    confidence: float
    evidence: str


@dataclass(frozen=True, slots=True)
class DraftItem:
    spoken_name: str
    candidate_sku_id: str | None
    quantity: int | None
    unit: str | None
    confidence: float
    evidence: str
    quoted_unit_price: Decimal | None = None


@dataclass(frozen=True, slots=True)
class DraftDate:
    value: date | None
    confidence: float
    evidence: str


@dataclass(frozen=True, slots=True)
class DraftCommand:
    customer: DraftCustomer
    delivery_date: DraftDate
    items: tuple[DraftItem, ...]
    mentioned_previous_balance: Decimal | None = None
    collection_amount: Decimal | None = None
    collection_evidence: str = ""
    intent: str = "create_sales_order"
    currency: str = "INR"
    missing_fields: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _mapping(value: object) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _text(value: object, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    return value.strip() if isinstance(value, str) and value.strip() else None


def _confidence(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if 0 <= number <= 1 else None


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def _string_tuple(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return tuple(value)


def validate_draft_command(payload: object) -> ValidationResult[DraftCommand]:
    """Validate untrusted JSON-like extractor output without coercing guesses."""

    root = _mapping(payload)
    if root is None:
        return ValidationResult(errors=(ValidationIssue("$", "INVALID_TYPE", "draft must be an object"),))
    errors: list[ValidationIssue] = []

    def issue(path: str, code: str, message: str) -> None:
        errors.append(ValidationIssue(path, code, message))

    if root.get("intent") != "create_sales_order":
        issue("intent", "UNSUPPORTED_INTENT", "only create_sales_order is supported")
    if root.get("currency") != "INR":
        issue("currency", "UNSUPPORTED_CURRENCY", "MVP supports INR only")

    customer_raw = _mapping(root.get("customer"))
    customer: DraftCustomer | None = None
    if customer_raw is None:
        issue("customer", "INVALID_TYPE", "customer must be an object")
    else:
        spoken = _text(customer_raw.get("spoken_name"))
        candidate = _text(customer_raw.get("candidate_id"), nullable=True)
        confidence = _confidence(customer_raw.get("confidence"))
        evidence = customer_raw.get("evidence")
        if spoken is None:
            issue("customer.spoken_name", "REQUIRED", "spoken_name is required")
        if customer_raw.get("candidate_id") is not None and candidate is None:
            issue("customer.candidate_id", "INVALID_TYPE", "candidate_id must be a non-empty string or null")
        if confidence is None:
            issue("customer.confidence", "INVALID_CONFIDENCE", "confidence must be between 0 and 1")
        if not isinstance(evidence, str):
            issue("customer.evidence", "INVALID_TYPE", "evidence must be a string")
        if spoken is not None and confidence is not None and isinstance(evidence, str):
            customer = DraftCustomer(spoken, candidate, confidence, evidence)

    delivery_raw = _mapping(root.get("delivery_date"))
    delivery: DraftDate | None = None
    if delivery_raw is None:
        issue("delivery_date", "INVALID_TYPE", "delivery_date must be an object")
    else:
        raw_value = delivery_raw.get("value")
        parsed_date: date | None = None
        if raw_value is not None:
            if isinstance(raw_value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_value):
                try:
                    parsed_date = date.fromisoformat(raw_value)
                except ValueError:
                    pass
            if parsed_date is None:
                issue("delivery_date.value", "INVALID_DATE", "delivery date must be YYYY-MM-DD or null")
        confidence = _confidence(delivery_raw.get("confidence"))
        evidence = delivery_raw.get("evidence")
        if confidence is None:
            issue("delivery_date.confidence", "INVALID_CONFIDENCE", "confidence must be between 0 and 1")
        if not isinstance(evidence, str):
            issue("delivery_date.evidence", "INVALID_TYPE", "evidence must be a string")
        if confidence is not None and isinstance(evidence, str):
            delivery = DraftDate(parsed_date, confidence, evidence)

    items: list[DraftItem] = []
    raw_items = root.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        issue("items", "REQUIRED", "at least one item is required")
    else:
        for index, raw_item in enumerate(raw_items):
            item = _mapping(raw_item)
            path = f"items.{index}"
            if item is None:
                issue(path, "INVALID_TYPE", "item must be an object")
                continue
            spoken = _text(item.get("spoken_name"))
            sku_id = _text(item.get("candidate_sku_id"), nullable=True)
            quantity = item.get("quantity")
            unit = _text(item.get("unit"), nullable=True)
            price_raw = item.get("quoted_unit_price")
            quoted_price = _decimal(price_raw) if price_raw is not None else None
            confidence = _confidence(item.get("confidence"))
            evidence = item.get("evidence")
            if spoken is None:
                issue(f"{path}.spoken_name", "REQUIRED", "spoken_name is required")
            if item.get("candidate_sku_id") is not None and sku_id is None:
                issue(f"{path}.candidate_sku_id", "INVALID_TYPE", "candidate_sku_id must be a non-empty string or null")
            if quantity is not None and (isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0):
                issue(f"{path}.quantity", "INVALID_QUANTITY", "quantity must be a positive whole number or null")
            if item.get("unit") is not None and unit is None:
                issue(f"{path}.unit", "INVALID_TYPE", "unit must be a non-empty string or null")
            if price_raw is not None and (quoted_price is None or quoted_price < 0):
                issue(f"{path}.quoted_unit_price", "INVALID_MONEY", "quoted price must be non-negative")
            if confidence is None:
                issue(f"{path}.confidence", "INVALID_CONFIDENCE", "confidence must be between 0 and 1")
            if not isinstance(evidence, str):
                issue(f"{path}.evidence", "INVALID_TYPE", "evidence must be a string")
            if spoken is not None and (quantity is None or isinstance(quantity, int)) and confidence is not None and isinstance(evidence, str):
                items.append(DraftItem(spoken, sku_id, quantity, unit, confidence, evidence, quoted_price))

    balance_raw = root.get("mentioned_previous_balance")
    balance = _decimal(balance_raw) if balance_raw is not None else None
    if balance_raw is not None and (balance is None or balance < 0):
        issue("mentioned_previous_balance", "INVALID_MONEY", "mentioned balance must be non-negative")
    collection_raw = root.get("collection_amount")
    collection = _decimal(collection_raw) if collection_raw is not None else None
    if collection_raw is not None and (collection is None or collection < 0):
        issue("collection_amount", "INVALID_MONEY", "collection amount must be non-negative")
    collection_evidence = root.get("collection_evidence")
    if not isinstance(collection_evidence, str):
        issue("collection_evidence", "INVALID_TYPE", "collection evidence must be a string")
    missing = _string_tuple(root.get("missing_fields"))
    warnings = _string_tuple(root.get("warnings"))
    if missing is None:
        issue("missing_fields", "INVALID_TYPE", "missing_fields must be a string list")
    if warnings is None:
        issue("warnings", "INVALID_TYPE", "warnings must be a string list")

    if errors or customer is None or delivery is None or missing is None or warnings is None:
        return ValidationResult(errors=tuple(errors))
    return ValidationResult(
        DraftCommand(customer, delivery, tuple(items), balance, collection, collection_evidence,
                     missing_fields=missing, warnings=warnings)
    )


def parse_draft_command(payload: object) -> DraftCommand:
    result = validate_draft_command(payload)
    if not result.ok:
        raise DomainError("INVALID_DRAFT", "draft failed schema validation", errors=result.errors)
    assert result.value is not None
    return result.value


class WorkflowState(StrEnum):
    UPLOADED = "UPLOADED"
    TRANSCRIBING = "TRANSCRIBING"
    EXTRACTING = "EXTRACTING"
    VALIDATING = "VALIDATING"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    CONFIRMED = "CONFIRMED"
    COMMITTED = "COMMITTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


_TRANSITIONS: Mapping[WorkflowState, frozenset[WorkflowState]] = {
    WorkflowState.UPLOADED: frozenset({WorkflowState.TRANSCRIBING, WorkflowState.FAILED, WorkflowState.CANCELLED}),
    WorkflowState.TRANSCRIBING: frozenset({WorkflowState.EXTRACTING, WorkflowState.FAILED, WorkflowState.CANCELLED}),
    WorkflowState.EXTRACTING: frozenset({WorkflowState.VALIDATING, WorkflowState.FAILED, WorkflowState.CANCELLED}),
    WorkflowState.VALIDATING: frozenset({WorkflowState.NEEDS_CLARIFICATION, WorkflowState.READY_FOR_REVIEW, WorkflowState.FAILED, WorkflowState.CANCELLED}),
    WorkflowState.NEEDS_CLARIFICATION: frozenset({WorkflowState.VALIDATING, WorkflowState.CANCELLED}),
    WorkflowState.READY_FOR_REVIEW: frozenset({WorkflowState.CONFIRMED, WorkflowState.CANCELLED}),
    WorkflowState.CONFIRMED: frozenset({WorkflowState.COMMITTED, WorkflowState.FAILED}),
    WorkflowState.COMMITTED: frozenset(),
    WorkflowState.FAILED: frozenset(),
    WorkflowState.CANCELLED: frozenset(),
}


def can_transition(current: WorkflowState, target: WorkflowState) -> bool:
    return target in _TRANSITIONS[current]


def transition(current: WorkflowState, target: WorkflowState) -> WorkflowState:
    if not can_transition(current, target):
        raise DomainError("INVALID_STATE_TRANSITION", f"cannot transition from {current} to {target}", current=current, target=target)
    return target


@dataclass(frozen=True, slots=True)
class EntityCandidate:
    id: str
    merchant_id: str
    canonical_name: str
    aliases: tuple[str, ...] = ()
    recency_score: float = 0
    order_history_score: float = 0


@dataclass(frozen=True, slots=True)
class ScoredCandidate:
    entity: EntityCandidate
    score: float
    lexical_score: float
    exact_alias: bool


class ResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class EntityResolution:
    status: ResolutionStatus
    candidates: tuple[ScoredCandidate, ...]

    @property
    def candidate(self) -> ScoredCandidate | None:
        return self.candidates[0] if self.status == ResolutionStatus.RESOLVED else None


def normalize_spoken_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    cleaned = "".join(" " if unicodedata.category(char)[0] in {"P", "S"} else char for char in normalized)
    return " ".join(cleaned.split())


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))


def resolve_entity(
    merchant_id: str,
    spoken_name: str,
    candidates: Sequence[EntityCandidate],
    *,
    extraction_confidence: float = 1,
    evidence_score: float | None = None,
    threshold: float = 0.72,
    ambiguity_margin: float = 0.08,
) -> EntityResolution:
    """Resolve only among the requesting merchant's aliases and canonical names."""

    query = normalize_spoken_name(spoken_name)
    evidence = extraction_confidence if evidence_score is None else evidence_score
    scored: list[ScoredCandidate] = []
    for candidate in candidates:
        if candidate.merchant_id != merchant_id:
            continue
        names = tuple(normalize_spoken_name(name) for name in (candidate.canonical_name, *candidate.aliases))
        exact = query in names
        lexical = 1.0 if exact else max((SequenceMatcher(None, query, name).ratio() for name in names), default=0)
        score = round(
            lexical * 0.7
            + _clamp(candidate.recency_score) * 0.1
            + _clamp(candidate.order_history_score) * 0.1
            + _clamp(evidence) * 0.05
            + _clamp(extraction_confidence) * 0.05,
            6,
        )
        scored.append(ScoredCandidate(candidate, score, lexical, exact))
    scored.sort(key=lambda item: (-item.score, item.entity.id))
    top = tuple(scored[:3])
    if not top or top[0].score < threshold:
        return EntityResolution(ResolutionStatus.UNRESOLVED, top)
    if len(top) > 1 and top[0].score - top[1].score < ambiguity_margin:
        return EntityResolution(ResolutionStatus.AMBIGUOUS, top)
    return EntityResolution(ResolutionStatus.RESOLVED, top)


_RELATIVE_DAYS: Mapping[str, int] = {
    "today": 0, "aaj": 0, "aaj ke liye": 0, "आज": 0, "आज के लिए": 0,
    "tomorrow": 1, "for tomorrow": 1, "kal": 1, "kal ke liye": 1, "कल": 1, "कल के लिए": 1,
    "day after tomorrow": 2, "parso": 2, "parso ke liye": 2, "parson": 2, "परसों": 2, "परसों के लिए": 2,
}


def merchant_today(time_zone: str, now: datetime | None = None) -> date:
    try:
        zone = ZoneInfo(time_zone)
    except ZoneInfoNotFoundError as exc:
        # Some minimal Windows Python distributions do not bundle the IANA
        # database. India has no DST, so this is exact for the seeded MVP.
        if time_zone in {"Asia/Kolkata", "Asia/Calcutta"}:
            zone = timezone(timedelta(hours=5, minutes=30), "Asia/Kolkata")
        else:
            raise DomainError("INVALID_TIMEZONE", f"unknown timezone: {time_zone}") from exc
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(zone).date()


def resolve_relative_date(
    expression: str,
    time_zone: str,
    *,
    now: datetime | None = None,
    supported_horizon_days: int = 90,
) -> date:
    """Resolve a delivery expression against the merchant's calendar date.

    In an order-delivery context, the Hindi word ``kal`` means tomorrow.
    """

    today = merchant_today(time_zone, now)
    normalized = " ".join(unicodedata.normalize("NFKC", expression).casefold().split())
    if normalized in _RELATIVE_DAYS:
        result = today + timedelta(days=_RELATIVE_DAYS[normalized])
    else:
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
                raise ValueError
            result = date.fromisoformat(normalized)
        except ValueError as exc:
            raise DomainError("UNSUPPORTED_DATE", f"unsupported delivery date: {expression}") from exc
    offset = (result - today).days
    if offset < 0 or offset > supported_horizon_days:
        raise DomainError("DATE_OUT_OF_HORIZON", f"delivery date must be within {supported_horizon_days} days", offset_days=offset)
    return result


@dataclass(frozen=True, slots=True)
class PackDefinition:
    base_unit: str
    units_per_case: int | None = None


_BASE_UNITS = frozenset({"piece", "pieces", "pc", "pcs", "bottle", "bottles", "pouch", "pouches", "kg", "kilo", "kilos"})
_CASE_UNITS = frozenset({"case", "cases", "peti", "पेटी", "crate", "crates", "carton", "cartons"})
_DOZEN_UNITS = frozenset({"dozen", "dozens", "darjan", "दर्जन"})


def normalize_unit(unit: str) -> str | None:
    normalized = unicodedata.normalize("NFKC", unit).casefold().strip()
    if normalized in _BASE_UNITS:
        return "base"
    if normalized in _CASE_UNITS:
        return "case"
    if normalized in _DOZEN_UNITS:
        return "dozen"
    return None


def to_base_units(quantity: int, unit: str, pack: PackDefinition) -> int:
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise DomainError("INVALID_QUANTITY", "quantity must be a positive whole number")
    normalized = normalize_unit(unit)
    if normalized is None:
        raise DomainError("UNSUPPORTED_UNIT", f"unsupported unit: {unit}")
    multiplier = 1
    if normalized == "dozen":
        multiplier = 12
    elif normalized == "case":
        if isinstance(pack.units_per_case, bool) or not isinstance(pack.units_per_case, int) or pack.units_per_case <= 0:
            raise DomainError("MISSING_PACK_SIZE", "SKU does not define units per case")
        multiplier = pack.units_per_case
    return quantity * multiplier


def money(value: Decimal | str | int) -> Decimal:
    amount = _decimal(value)
    if amount is None or amount < 0:
        raise DomainError("INVALID_MONEY", "money must be a finite non-negative amount")
    return amount.quantize(PAISE, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class PricedLine:
    sku_id: str
    quantity: int
    unit_price: Decimal
    discount_basis_points: int = 0
    tax_basis_points: int = 0


@dataclass(frozen=True, slots=True)
class CalculatedLine:
    sku_id: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    discount: Decimal
    taxable: Decimal
    tax: Decimal
    total: Decimal


@dataclass(frozen=True, slots=True)
class OrderTotals:
    lines: tuple[CalculatedLine, ...]
    subtotal: Decimal
    discount: Decimal
    taxable: Decimal
    tax: Decimal
    total: Decimal


def _basis_points(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 10_000:
        raise DomainError("INVALID_RATE", f"{name} must be between 0 and 10000")
    return value


def calculate_line(line: PricedLine) -> CalculatedLine:
    if isinstance(line.quantity, bool) or not isinstance(line.quantity, int) or line.quantity <= 0:
        raise DomainError("INVALID_QUANTITY", "quantity must be a positive whole number")
    unit_price = money(line.unit_price)
    discount_rate = _basis_points(line.discount_basis_points, "discount_basis_points")
    tax_rate = _basis_points(line.tax_basis_points, "tax_basis_points")
    subtotal = money(unit_price * line.quantity)
    discount = money(subtotal * Decimal(discount_rate) / Decimal(10_000))
    taxable = money(subtotal - discount)
    tax = money(taxable * Decimal(tax_rate) / Decimal(10_000))
    return CalculatedLine(line.sku_id, line.quantity, unit_price, subtotal, discount, taxable, tax, money(taxable + tax))


def calculate_order(lines: Sequence[PricedLine]) -> OrderTotals:
    if not lines:
        raise DomainError("EMPTY_ORDER", "an order must contain at least one line")
    calculated = tuple(calculate_line(line) for line in lines)
    total_for = lambda name: money(sum((getattr(line, name) for line in calculated), Decimal(0)))
    return OrderTotals(calculated, total_for("subtotal"), total_for("discount"), total_for("taxable"), total_for("tax"), total_for("total"))


def calculate_updated_balance(current_balance: Decimal, debit: Decimal, credit: Decimal = Decimal(0)) -> Decimal:
    current, debit_amount, credit_amount = money(current_balance), money(debit), money(credit)
    result = current + debit_amount - credit_amount
    if result < 0:
        raise DomainError("NEGATIVE_BALANCE", "credit exceeds the outstanding balance")
    return money(result)


@dataclass(frozen=True, slots=True)
class ClarificationOption:
    id: str
    label: str


@dataclass(frozen=True, slots=True)
class Clarification:
    code: str
    field_path: str
    question: str
    options: tuple[ClarificationOption, ...] = ()


@dataclass(frozen=True, slots=True)
class ClarificationContext:
    time_zone: str
    now: datetime | None = None
    confidence_threshold: float = 0.75
    customer_options: tuple[ClarificationOption, ...] = ()
    sku_options_by_item: Mapping[int, tuple[ClarificationOption, ...]] = field(default_factory=dict)
    stock_by_sku_id: Mapping[str, int] = field(default_factory=dict)
    pack_by_sku_id: Mapping[str, PackDefinition] = field(default_factory=dict)
    backorders_allowed: bool = False
    system_balance: Decimal | None = None
    balance_tolerance: Decimal = Decimal("100.00")
    supported_date_horizon_days: int = 90


def next_clarification(draft: DraftCommand, context: ClarificationContext) -> Clarification | None:
    """Return only the highest-priority question that changes money or fulfillment."""

    customer_options = tuple(context.customer_options)
    if not draft.customer.candidate_id or draft.customer.confidence < context.confidence_threshold or len(customer_options) > 1:
        return Clarification("AMBIGUOUS_CUSTOMER", "customer.candidate_id", f"Which customer did you mean by “{draft.customer.spoken_name}”?", customer_options)
    for index, item in enumerate(draft.items):
        options = tuple(context.sku_options_by_item.get(index, ()))
        if not item.candidate_sku_id or item.confidence < context.confidence_threshold or len(options) > 1:
            return Clarification("AMBIGUOUS_PRODUCT", f"items.{index}.candidate_sku_id", f"Which product did you mean by “{item.spoken_name}”?", options)
        if item.quantity is None:
            return Clarification("MISSING_QUANTITY", f"items.{index}.quantity", f"How many {item.spoken_name}?")
        if item.unit is None or normalize_unit(item.unit) is None:
            return Clarification(
                "MISSING_UNIT", f"items.{index}.unit", f"{item.spoken_name}: is {item.quantity} cases or pieces?",
                (ClarificationOption("case", "Cases / peti"), ClarificationOption("piece", "Pieces")),
            )
    if draft.delivery_date.value is None:
        return Clarification("INVALID_DELIVERY_DATE", "delivery_date.value", "When should this order be delivered?")
    try:
        resolve_relative_date(draft.delivery_date.value.isoformat(), context.time_zone, now=context.now, supported_horizon_days=context.supported_date_horizon_days)
    except DomainError:
        return Clarification("INVALID_DELIVERY_DATE", "delivery_date.value", "That delivery date is not supported. Which date should I use?")
    if draft.mentioned_previous_balance is not None and context.system_balance is not None:
        if abs(money(draft.mentioned_previous_balance) - money(context.system_balance)) > money(context.balance_tolerance):
            return Clarification(
                "BALANCE_MISMATCH", "mentioned_previous_balance",
                f"You mentioned ₹{money(draft.mentioned_previous_balance)}, but the ledger shows ₹{money(context.system_balance)}. Which is correct?",
                (ClarificationOption("system", f"Ledger ₹{money(context.system_balance)}"), ClarificationOption("spoken", f"Spoken ₹{money(draft.mentioned_previous_balance)}")),
            )
    if not context.backorders_allowed:
        for index, item in enumerate(draft.items):
            sku_id = item.candidate_sku_id
            if not sku_id or sku_id not in context.stock_by_sku_id or item.quantity is None or item.unit is None:
                continue
            try:
                requested = to_base_units(item.quantity, item.unit, context.pack_by_sku_id.get(sku_id, PackDefinition("piece")))
            except DomainError:
                return Clarification("MISSING_UNIT", f"items.{index}.unit", f"What pack size should I use for {item.spoken_name}?")
            available = context.stock_by_sku_id[sku_id]
            if requested > available:
                return Clarification(
                    "INSUFFICIENT_STOCK", f"items.{index}.quantity",
                    f"Only {available} base units of {item.spoken_name} are in stock. Reduce the quantity?",
                    (ClarificationOption(str(available), f"Use available {available}"),),
                )
    return None


def create_idempotency_key(merchant_id: str, voice_job_id: str, confirmed_revision: int) -> str:
    if not merchant_id or not voice_job_id or isinstance(confirmed_revision, bool) or not isinstance(confirmed_revision, int) or confirmed_revision < 1:
        raise DomainError("INVALID_IDEMPOTENCY_INPUT", "merchant, voice job, and positive revision are required")
    canonical = json.dumps([merchant_id, voice_job_id, confirmed_revision], ensure_ascii=False, separators=(",", ":"))
    return f"vpc_{sha256(canonical.encode()).hexdigest()[:32]}"


@dataclass(frozen=True, slots=True)
class CanonicalSku:
    id: str
    label: str
    base_unit: str
    selling_price: Decimal
    stock_base_units: int
    units_per_case: int | None = None
    tax_basis_points: int = 0


@dataclass(frozen=True, slots=True)
class ConfirmationInput:
    merchant_id: str
    voice_job_id: str
    draft_revision: int
    confirmed_revision: int
    draft: DraftCommand
    order_id: str
    invoice_id: str
    invoice_number: str
    customer_id: str
    customer_balance: Decimal
    skus_by_id: Mapping[str, CanonicalSku]
    time_zone: str
    backorders_allowed: bool = False
    now: datetime | None = None


@dataclass(frozen=True, slots=True)
class PlannedOrderLine:
    sku_id: str
    sku_label: str
    spoken_quantity: int
    spoken_unit: str
    base_quantity: int
    unit_price: Decimal
    subtotal: Decimal
    tax: Decimal
    total: Decimal


@dataclass(frozen=True, slots=True)
class InventoryMovementPlan:
    sku_id: str
    delta_base_units: int
    source_order_id: str


@dataclass(frozen=True, slots=True)
class LedgerEntryPlan:
    customer_id: str
    order_id: str
    direction: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal


@dataclass(frozen=True, slots=True)
class ConfirmationPlan:
    idempotency_key: str
    order_id: str
    customer_id: str
    delivery_date: date
    lines: tuple[PlannedOrderLine, ...]
    totals: OrderTotals
    inventory_movements: tuple[InventoryMovementPlan, ...]
    invoice_id: str
    invoice_number: str
    invoice_total: Decimal
    ledger_entry: LedgerEntryPlan
    outbox_event: Mapping[str, str]


def plan_confirmation(command: ConfirmationInput) -> ConfirmationPlan:
    """Return the immutable effects that an adapter must commit atomically."""

    for name in ("merchant_id", "voice_job_id", "order_id", "invoice_id", "invoice_number", "customer_id"):
        if not getattr(command, name).strip():
            raise DomainError("INVALID_CONFIRMATION_INPUT", f"{name} is required", field=name)
    if command.confirmed_revision != command.draft_revision:
        raise DomainError("STALE_DRAFT", "confirmed revision does not match current draft", confirmed=command.confirmed_revision, current=command.draft_revision)
    if command.draft.missing_fields:
        raise DomainError("DRAFT_NOT_READY", "draft still contains missing fields", fields=command.draft.missing_fields)
    if command.draft.customer.candidate_id != command.customer_id:
        raise DomainError("CUSTOMER_MISMATCH", "resolved customer differs from current canonical customer")
    packs = {sku.id: PackDefinition(sku.base_unit, sku.units_per_case) for sku in command.skus_by_id.values()}
    stock = {sku.id: sku.stock_base_units for sku in command.skus_by_id.values()}
    question = next_clarification(
        command.draft,
        ClarificationContext(command.time_zone, command.now, stock_by_sku_id=stock, pack_by_sku_id=packs,
                             backorders_allowed=command.backorders_allowed, system_balance=command.customer_balance),
    )
    if question:
        raise DomainError(question.code, question.question, field_path=question.field_path)

    prepared: list[tuple[DraftItem, CanonicalSku, int]] = []
    demand: dict[str, int] = {}
    for item in command.draft.items:
        sku = command.skus_by_id.get(item.candidate_sku_id or "")
        if sku is None:
            raise DomainError("UNKNOWN_SKU", f"no canonical SKU for {item.spoken_name}")
        assert item.quantity is not None and item.unit is not None
        base_quantity = to_base_units(item.quantity, item.unit, packs[sku.id])
        prepared.append((item, sku, base_quantity))
        demand[sku.id] = demand.get(sku.id, 0) + base_quantity
    if not command.backorders_allowed:
        for sku_id, requested in demand.items():
            available = command.skus_by_id[sku_id].stock_base_units
            if requested > available:
                raise DomainError("INSUFFICIENT_STOCK", f"requested {requested}; only {available} available", sku_id=sku_id)

    totals = calculate_order(tuple(
        PricedLine(sku.id, base_quantity, sku.selling_price, tax_basis_points=sku.tax_basis_points)
        for _, sku, base_quantity in prepared
    ))
    lines = tuple(
        PlannedOrderLine(item.candidate_sku_id or "", sku.label, item.quantity or 0, item.unit or "", base_quantity,
                         calculated.unit_price, calculated.subtotal, calculated.tax, calculated.total)
        for (item, sku, base_quantity), calculated in zip(prepared, totals.lines, strict=True)
    )
    key = create_idempotency_key(command.merchant_id, command.voice_job_id, command.confirmed_revision)
    before = money(command.customer_balance)
    after = calculate_updated_balance(before, totals.total)
    return ConfirmationPlan(
        key, command.order_id, command.customer_id, command.draft.delivery_date.value, lines, totals,
        tuple(InventoryMovementPlan(sku_id, -quantity, command.order_id) for sku_id, quantity in demand.items()),
        command.invoice_id, command.invoice_number, totals.total,
        LedgerEntryPlan(command.customer_id, command.order_id, "debit", totals.total, before, after),
        {"type": "order.committed", "aggregate_id": command.order_id, "idempotency_key": key},
    )
