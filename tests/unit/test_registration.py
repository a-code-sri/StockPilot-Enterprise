from datetime import date

import pytest

from backend.modules.business.domain.registration import (
    gstin_check_char,
    validate_cin,
    validate_gstin,
    validate_pan,
    verify_registration,
)

VALID_GSTINS = ["27AAPFU0939F1ZV", "29AAGCB7383J1Z4"]


@pytest.mark.parametrize("gstin", VALID_GSTINS)
def test_known_gstins_pass_checksum(gstin):
    assert gstin_check_char(gstin[:14]) == gstin[14]
    assert validate_gstin(gstin).ok


def test_single_character_typo_is_caught():
    r = validate_gstin("27AAPFU0939F1ZW")
    assert not r.ok
    assert any("checksum" in e for e in r.errors)


def test_lowercase_and_spaces_are_normalised():
    assert validate_gstin(" 27aapfu0939f1zv ").ok


@pytest.mark.parametrize("bad", ["", "27AAPFU0939F1Z", "27AAPFU0939F1AV", "ABAAPFU0939F1ZV"])
def test_malformed_gstin(bad):
    assert not validate_gstin(bad).ok


def test_unknown_state_code():
    first14 = "50AAPFU0939F1Z"
    r = validate_gstin(first14 + gstin_check_char(first14))
    assert any("state code" in e for e in r.errors)


def test_pan_holder_type():
    assert validate_pan("AAPFU0939F").details["holder_type"] == "Firm / LLP"
    assert not validate_pan("AAPXU0939F").ok  # X is not a holder type
    assert not validate_pan("AAPF0939F").ok


def test_cin_parsing():
    r = validate_cin("U72200MH2009PTC123456", today=date(2026, 1, 1))
    assert r.ok
    assert r.details["company_class"] == "Private Limited Company"
    assert r.details["incorporation_year"] == 2009
    assert not validate_cin("U72200MH2999PTC123456", today=date(2026, 1, 1)).ok


def test_pan_must_match_gstin():
    r = verify_registration(legal_name="Ultra", gstin="27AAPFU0939F1ZV", pan="AAPFU0939G")
    assert any("does not match" in e for e in r.errors)


def test_state_must_match_gstin():
    r = verify_registration(legal_name="Ultra", gstin="27AAPFU0939F1ZV", pan="AAPFU0939F", state_code="29")
    assert any("Maharashtra" in e for e in r.errors)


def test_requires_gstin_or_pan():
    assert not verify_registration(legal_name="X", gstin=None, pan=None).ok


def test_company_cin_with_non_company_pan_warns():
    r = verify_registration(
        legal_name="Ultra Corp", gstin="27AAPFU0939F1ZV", pan=None, cin="U72200MH2009PTC123456"
    )
    assert r.ok
    assert any("company PAN" in w for w in r.warnings)


def test_pan_name_initial_warning():
    r = verify_registration(legal_name="Zeta Traders", gstin="27AAPFU0939F1ZV", pan=None)
    assert r.ok
    assert any("5th character" in w for w in r.warnings)
    assert not verify_registration(legal_name="Ultra Traders", gstin="27AAPFU0939F1ZV", pan=None).warnings
