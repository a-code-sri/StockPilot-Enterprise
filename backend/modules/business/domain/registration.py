"""
Offline validation of Indian business registration numbers.

Checks performed (no network access, no paid APIs):
  GSTIN  15 chars: state code (2) + PAN (10) + entity no. (1) + 'Z' + checksum (1).
         The checksum is the official mod-36 algorithm, so typos are caught.
  PAN    10 chars: AAAAA9999A; 4th char is the holder type (C = company, F = firm, ...).
  CIN    21 chars: listing status + industry code + state + year + ownership + reg. no.

Cross-checks: the PAN embedded in the GSTIN must equal the PAN; GSTIN state
should match the declared state and the CIN state; companies (with a CIN) should
have a company PAN; the PAN's 5th char usually matches the legal name.

Passing these checks proves the numbers are well-formed and consistent, not that
the government registry lists them. That final step is a human approval
(see BusinessService.review), or a future live-lookup integration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

GSTIN_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
CIN_RE = re.compile(r"^([LU])([0-9]{5})([A-Z]{2})([0-9]{4})([A-Z]{3})([0-9]{6})$")

# GST state / UT codes.
GST_STATES: dict[str, str] = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "25": "Daman and Diu", "26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra",
    "28": "Andhra Pradesh (old)", "29": "Karnataka", "30": "Goa", "31": "Lakshadweep", "32": "Kerala",
    "33": "Tamil Nadu", "34": "Puducherry", "35": "Andaman and Nicobar Islands", "36": "Telangana",
    "37": "Andhra Pradesh", "38": "Ladakh", "97": "Other Territory", "99": "Centre Jurisdiction",
}

# Registrar-of-Companies state abbreviations used inside CINs -> GST state code(s).
CIN_STATE_TO_GST: dict[str, tuple[str, ...]] = {
    "JK": ("01",), "HP": ("02",), "PB": ("03",), "CH": ("04",), "UR": ("05",), "UK": ("05",),
    "HR": ("06",), "DL": ("07",), "RJ": ("08",), "UP": ("09",), "BR": ("10",), "SK": ("11",),
    "AR": ("12",), "NL": ("13",), "MN": ("14",), "MZ": ("15",), "TR": ("16",), "ML": ("17",),
    "AS": ("18",), "WB": ("19",), "JH": ("20",), "OR": ("21",), "OD": ("21",), "CT": ("22",),
    "CG": ("22",), "MP": ("23",), "GJ": ("24",), "DD": ("25", "26"), "DN": ("26",), "MH": ("27",),
    "AP": ("28", "37"), "KA": ("29",), "GA": ("30",), "LD": ("31",), "KL": ("32",), "TN": ("33",),
    "PY": ("34",), "AN": ("35",), "TG": ("36",), "TS": ("36",), "LA": ("38",),
}

PAN_HOLDER_TYPES = {
    "P": "Individual", "C": "Company", "H": "Hindu Undivided Family", "F": "Firm / LLP",
    "A": "Association of Persons", "T": "Trust", "B": "Body of Individuals", "L": "Local Authority",
    "J": "Artificial Juridical Person", "G": "Government",
}

CIN_OWNERSHIP = {
    "PLC": "Public Limited Company", "PTC": "Private Limited Company", "OPC": "One Person Company",
    "GOI": "Government of India Company", "SGC": "State Government Company", "FLC": "Foreign Company (Listed)",
    "FTC": "Foreign Subsidiary (Private)", "NPL": "Not-for-profit (Section 8) Company",
    "GAP": "Guarantee & Association (Public)", "GAT": "Guarantee & Association (Private)",
    "ULL": "Unlimited Liability (Public)", "ULT": "Unlimited Liability (Private)",
}


def normalise(value: str | None) -> str:
    return re.sub(r"\s+", "", (value or "")).upper()


def gstin_check_char(first14: str) -> str:
    """Official GSTIN checksum: alternate weights 1,2; fold each product base 36."""
    total = 0
    for i, ch in enumerate(first14):
        product = GSTIN_CHARSET.index(ch) * (2 if i % 2 else 1)
        total += product // 36 + product % 36
    return GSTIN_CHARSET[(36 - total % 36) % 36]


@dataclass
class CheckResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict:
        return {"valid": self.ok, "errors": self.errors, "warnings": self.warnings, "details": self.details}


def validate_pan(pan: str) -> CheckResult:
    r = CheckResult()
    pan = normalise(pan)
    if not PAN_RE.match(pan):
        r.errors.append("PAN must be 10 characters: 5 letters, 4 digits, 1 letter (e.g. AAPFU0939F).")
        return r
    holder = PAN_HOLDER_TYPES.get(pan[3])
    if holder is None:
        r.errors.append(f"PAN 4th character '{pan[3]}' is not a valid holder type.")
    r.details.update({"pan": pan, "holder_type": holder})
    return r


def validate_gstin(gstin: str) -> CheckResult:
    r = CheckResult()
    gstin = normalise(gstin)
    if not GSTIN_RE.match(gstin):
        r.errors.append("GSTIN must be 15 characters: 2-digit state code, PAN, entity number, 'Z', checksum.")
        return r

    state = GST_STATES.get(gstin[:2])
    if state is None:
        r.errors.append(f"GSTIN state code '{gstin[:2]}' does not exist.")

    expected = gstin_check_char(gstin[:14])
    if gstin[14] != expected:
        r.errors.append(f"GSTIN checksum is wrong (last character should be '{expected}'). Check for a typo.")

    pan_result = validate_pan(gstin[2:12])
    r.errors.extend(f"GSTIN contains an invalid PAN: {e}" for e in pan_result.errors)

    r.details.update({
        "gstin": gstin,
        "state_code": gstin[:2],
        "state": state,
        "embedded_pan": gstin[2:12],
        "entity_number": gstin[12],
    })
    return r


def validate_cin(cin: str, *, today: date | None = None) -> CheckResult:
    r = CheckResult()
    cin = normalise(cin)
    m = CIN_RE.match(cin)
    if not m:
        r.errors.append("CIN must be 21 characters, e.g. U72200MH2009PTC123456.")
        return r

    listing, industry, state, year, ownership, regno = m.groups()
    current_year = (today or date.today()).year
    if not 1850 <= int(year) <= current_year:
        r.errors.append(f"CIN incorporation year {year} is not plausible.")
    if state not in CIN_STATE_TO_GST:
        r.warnings.append(f"CIN state code '{state}' is not recognised.")
    if ownership not in CIN_OWNERSHIP:
        r.warnings.append(f"CIN ownership code '{ownership}' is not a common company class.")

    r.details.update({
        "cin": cin,
        "listed": listing == "L",
        "industry_code": industry,
        "state_code": state,
        "incorporation_year": int(year),
        "company_class": CIN_OWNERSHIP.get(ownership, ownership),
        "registration_number": regno,
    })
    return r


def verify_registration(
    *,
    legal_name: str,
    gstin: str | None,
    pan: str | None,
    cin: str | None = None,
    state_code: str | None = None,
    today: date | None = None,
) -> CheckResult:
    """Run all checks and cross-checks. At least a GSTIN or a PAN is required."""
    result = CheckResult()
    gstin, pan, cin = normalise(gstin), normalise(pan), normalise(cin)

    if not gstin and not pan:
        result.errors.append("Provide at least a GSTIN or a PAN.")
        return result

    checks = {}
    if gstin:
        checks["gstin"] = validate_gstin(gstin)
    if pan:
        checks["pan"] = validate_pan(pan)
    if cin:
        checks["cin"] = validate_cin(cin, today=today)

    for name, c in checks.items():
        result.errors.extend(c.errors)
        result.warnings.extend(c.warnings)
        result.details[name] = c.details

    g, p, c = checks.get("gstin"), checks.get("pan"), checks.get("cin")
    effective_pan = pan or (gstin[2:12] if g and g.ok else "")

    if g and g.ok and pan and gstin[2:12] != pan:
        result.errors.append(f"GSTIN contains PAN {gstin[2:12]}, which does not match the PAN entered ({pan}).")

    if g and g.ok and state_code and gstin[:2] != state_code:
        result.errors.append(
            f"GSTIN is registered in {GST_STATES.get(gstin[:2], gstin[:2])}, "
            f"but the business state is {GST_STATES.get(state_code, state_code)}."
        )

    if c and c.ok and g and g.ok:
        expected_states = CIN_STATE_TO_GST.get(c.details["state_code"], ())
        if expected_states and gstin[:2] not in expected_states:
            result.warnings.append(
                "CIN and GSTIN are registered in different states. This is allowed (one company can hold "
                "GST registrations in several states) but double-check the numbers."
            )

    if c and c.ok and effective_pan and PAN_RE.match(effective_pan) and effective_pan[3] != "C":
        result.warnings.append("A company with a CIN normally has a company PAN (4th character 'C').")

    name = re.sub(r"^(M/S\.?|THE)\s+", "", (legal_name or "").strip().upper())
    if effective_pan and PAN_RE.match(effective_pan) and effective_pan[3] != "P" and name:
        if effective_pan[4] != name[0]:
            result.warnings.append(
                f"PAN 5th character '{effective_pan[4]}' usually matches the first letter of the legal name "
                f"('{name[0]}')."
            )

    return result
