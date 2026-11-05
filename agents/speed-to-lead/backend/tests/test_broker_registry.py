"""Pure-function tests for the broker registry. No database needed."""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.broker_registry import (  # noqa: E402
    RegView, decide, extract_broker_code, fmt_ist, looks_like_registration,
    mask_phone, parse_registration, parse_status_query, phone10, classify_source,
)

UTC = timezone.utc
NOW = datetime(2026, 11, 4, 15, 34, tzinfo=UTC)   # 9:04 PM IST


def test_phone10():
    assert phone10("919876543210") == "9876543210"
    assert phone10("+91 98765 43210") == "9876543210"
    assert phone10("12345") is None
    assert phone10(None) is None


def test_parse_registration_full():
    p = parse_registration("REG Ravi Kumar 9876543210 Skyline Heights")
    assert (p.name, p.client_phone10, p.project_hint) == ("Ravi Kumar", "9876543210", "Skyline Heights")


def test_parse_registration_separators_and_country_code():
    p = parse_registration("register: Anita Rao, +91 98765-43210, Skyline")
    assert p.name == "Anita Rao" and p.client_phone10 == "9876543210" and p.project_hint == "Skyline"


def test_parse_registration_no_name_no_project():
    p = parse_registration("9876543210")
    assert p.name is None and p.project_hint is None and p.client_phone10 == "9876543210"


def test_parse_registration_requires_mobile():
    assert parse_registration("REG Ravi Kumar") is None
    assert parse_registration("REG Ravi 1234567890") is None   # does not start 6-9


def test_looks_like_registration_needs_command_and_number():
    assert looks_like_registration("REG Ravi 9876543210")
    assert not looks_like_registration("hi what is the price")
    assert not looks_like_registration("Ravi 9876543210")        # no command word


def test_status_query():
    assert parse_status_query("status reg-7k2q9m") == "REG-7K2Q9M"
    assert parse_status_query("hello") is None


def test_extract_broker_code():
    assert extract_broker_code("BRK-RAV7 floor plan please") == ("BRK-RAV7", "floor plan please")
    assert extract_broker_code("brk-rav7") == ("BRK-RAV7", "")
    assert extract_broker_code("BRKRAV7 Skyline") == ("BRK-RAV7", "Skyline")
    assert extract_broker_code("what is the price") == (None, "what is the price")


def test_fmt_ist_and_mask():
    assert fmt_ist(NOW) == "04 Nov 2026, 9:04 PM IST"
    assert mask_phone("9876543210") == "98XXXXXX10"


def reg(i, broker, hours_ago, valid_days=60, status="registered"):
    at = NOW - timedelta(hours=hours_ago)
    return RegView(i, broker, at, at + timedelta(days=valid_days), status)


def test_decide_new():
    assert decide("A", [], None, NOW).kind == "new"


def test_decide_already_mine():
    d = decide("A", [reg(1, "A", 5)], None, NOW)
    assert d.kind == "already_mine" and d.first.id == 1


def test_decide_conflict_broker_first_claim_wins():
    # B arrives after A and C: the earliest active registration is the one to beat
    d = decide("B", [reg(2, "C", 3), reg(1, "A", 10)], None, NOW)
    assert d.kind == "conflict_broker" and d.first.id == 1


def test_decide_expired_registration_does_not_block():
    old = reg(1, "A", 24 * 90, valid_days=60)     # 90 days ago, valid 60
    assert decide("B", [old], None, NOW).kind == "new"


def test_decide_superseded_or_duplicate_rows_do_not_block():
    assert decide("B", [reg(1, "A", 5, status="superseded")], None, NOW).kind == "new"
    assert decide("B", [reg(1, "A", 5, status="duplicate")], None, NOW).kind == "new"


def test_decide_existing_direct_lead_conflicts():
    d = decide("A", [], NOW - timedelta(days=2), NOW)
    assert d.kind == "conflict_lead" and d.existing_lead_at is not None


def test_decide_broker_claim_beats_direct_lead_check():
    # an active broker registration is the older claim, so it is reported first
    d = decide("B", [reg(1, "A", 5)], NOW - timedelta(days=2), NOW)
    assert d.kind == "conflict_broker"


def test_classify_source():
    assert classify_source("b1", "ad1") == "broker"
    assert classify_source(None, "ad1") == "ad"
    assert classify_source(None, None) == "organic"


from agents.escalation import detect_escalation  # noqa: E402


def test_escalation_negotiation():
    assert detect_escalation("Can I get a discount on the 3BHK?") == "negotiation"
    assert detect_escalation("what is your best price") == "negotiation"
    assert detect_escalation("is the price negotiable, I want to negotiate") == "negotiation"


def test_escalation_availability():
    assert detect_escalation("Is a 3BHK on the 12th floor available?") == "availability"
    assert detect_escalation("how many units are left") == "availability"
    assert detect_escalation("which floors are available") == "availability"


def test_escalation_does_not_fire_on_normal_questions():
    for q in ("What is the price per sq ft?", "What is the RERA number?", "When is possession?",
              "Can I get the floor plan", "Book a site visit on Saturday", "hi"):
        assert detect_escalation(q) is None, q


# ── AI summary transcript builder ─────────────────────────────────────────────
from types import SimpleNamespace  # noqa: E402
from services.lead_summary import build_transcript, MAX_MESSAGES, MAX_CHARS  # noqa: E402


def _m(who, text):
    return SimpleNamespace(sender_type=who, message_text=text)


def test_transcript_labels_and_skips_empty():
    rows = [_m("lead", "price?"), _m("ai", "1.45 cr"), _m("admin", "I will call you"), _m("ai", None)]
    assert build_transcript(rows) == "Buyer: price?\nAssistant: 1.45 cr\nStaff: I will call you"


def test_transcript_truncates_long_messages_and_caps_count():
    long = "x" * (MAX_CHARS + 50)
    assert build_transcript([_m("lead", long)]).endswith("...")
    many = [_m("lead", f"m{i}") for i in range(MAX_MESSAGES + 10)]
    assert build_transcript(many).count("\n") == MAX_MESSAGES - 1
    assert "m0" not in build_transcript(many).split("\n")[0]
