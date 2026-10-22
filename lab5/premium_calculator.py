"""Insurance premium calculator.

Quotes health, motor and life premiums, works out an applicant's age,
saves quotes to a log, imports policies from partner XML, downloads rate
tables, extracts customer claim archives, splits premiums into
instalments and computes renewal dates.

Configuration (environment variables):
    UNDERWRITER_TOKEN   secret used by ``is_authorised`` (no default)
    PREMIUM_LOG_FILE    quote log path (default: premium_quotes.log)
    PREMIUM_HOST        address a server would bind to (default: 127.0.0.1)
"""

import csv
import hmac
import logging
import os
import secrets
import tarfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime

from defusedxml import ElementTree as SafeET

logger = logging.getLogger(__name__)

# Global quote book: policy number -> {"name": ..., "premium": ...}
QUOTES = {}

HOST = os.environ.get("PREMIUM_HOST", "127.0.0.1")
LOG_FILE = os.environ.get("PREMIUM_LOG_FILE", "premium_quotes.log")
BASE_RATES = {"health": 5000, "motor": 3000, "life": 8000}

SENIOR_AGE = 45
SENIOR_LOADING = 1.5
SMOKER_LOADING = 1.3
RATE_PER_RUPEE_INSURED = 0.002
CLAIM_SURCHARGE = 1000

MAX_ARCHIVE_MEMBERS = 1000
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024  # 100 MB uncompressed


@dataclass
class Applicant:
    """Rating factors that describe the person being insured."""

    age: int
    smoker: bool = False
    claims: int = 0

    def __post_init__(self):
        if not isinstance(self.smoker, bool):
            raise TypeError(
                f"smoker must be True or False, got {self.smoker!r}")
        if self.age < 0 or self.claims < 0:
            raise ValueError("age and claims must not be negative")


def calculate_premium(policy_type, sum_insured, applicant, discounts=None):
    """Return the premium in rupees, rounded to 2 decimal places.

    ``discounts`` is a list of rupee amounts. It is never modified, and the
    final premium may not be negative.
    """
    if policy_type not in BASE_RATES:
        raise ValueError(f"unknown policy type: {policy_type!r}")
    if sum_insured < 0:
        raise ValueError("sum_insured must not be negative")

    premium = BASE_RATES[policy_type] + sum_insured * RATE_PER_RUPEE_INSURED
    if applicant.age > SENIOR_AGE:
        premium *= SENIOR_LOADING
    if applicant.smoker:
        premium *= SMOKER_LOADING
    premium += applicant.claims * CLAIM_SURCHARGE
    premium -= sum(discounts or [])
    if premium < 0:
        raise ValueError("discounts exceed the premium")
    return round(premium, 2)


def age_from_dob(dob, today=None):
    """Return completed years of age for a DD-MM-YYYY date of birth."""
    born = datetime.strptime(dob, "%d-%m-%Y").date()
    today = today or date.today()
    if born > today:
        raise ValueError("date of birth is in the future")
    had_birthday = (today.month, today.day) >= (born.month, born.day)
    return today.year - born.year - (0 if had_birthday else 1)


def policy_number():
    """Return a new policy number that is not already in the quote book."""
    while True:
        number = f"POL-{100000 + secrets.randbelow(900000)}"
        if number not in QUOTES:
            return number


def _csv_safe(text):
    """Stop spreadsheet programs from treating text as a formula."""
    text = str(text)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


def save_quote(name, premium):
    """Store a quote in memory, append it to the log and return its number."""
    number = policy_number()
    QUOTES[number] = {"name": name, "premium": premium}
    with open(LOG_FILE, "a", encoding="utf-8", newline="") as log:
        csv.writer(log).writerow([number, _csv_safe(name), f"{premium:.2f}"])
    return number


def import_policies(xml_text):
    """Parse partner XML into (type, age, sum) tuples.

    Records with missing or non-numeric fields are skipped and logged.
    """
    root = SafeET.fromstring(xml_text)
    result = []
    for policy in root.findall("policy"):
        try:
            result.append((policy.get("type"),
                           int(policy.get("age")),
                           int(policy.get("sum"))))
        except (TypeError, ValueError):
            logger.warning("skipping invalid policy record: %s",
                           policy.attrib)
    return result


def fetch_rates(url, timeout=10):
    """Download a rate table over HTTPS with certificate verification."""
    if urllib.parse.urlparse(url).scheme != "https":
        raise ValueError("only https:// URLs are allowed")
    # Scheme is restricted to https above, so file:/ and custom schemes
    # cannot reach urlopen.
    request = urllib.request.Request(url)
    with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec
        return response.read()


def import_claim_documents(archive_path, destination="claims_docs"):
    """Safely extract a customer-supplied tar archive of claim documents.

    The archive is checked for size, then extracted with the ``data``
    filter, which rejects absolute paths, ``..`` escapes, links that point
    outside the destination and special device files.
    """
    with tarfile.open(archive_path) as tar:
        members = tar.getmembers()
        if len(members) > MAX_ARCHIVE_MEMBERS:
            raise ValueError("archive has too many files")
        if sum(member.size for member in members) > MAX_ARCHIVE_BYTES:
            raise ValueError("archive is too large")
        tar.extractall(destination, members=members, filter="data")


def monthly_instalment(premium, months=12):
    """Split a premium into equal monthly instalments (to the paisa)."""
    if months < 1:
        raise ValueError("months must be at least 1")
    return round(premium / months, 2)


def is_authorised(token):
    """Check an underwriter token against the UNDERWRITER_TOKEN secret."""
    expected = os.environ.get("UNDERWRITER_TOKEN", "")
    if not expected or not isinstance(token, str):
        return False
    return hmac.compare_digest(token.encode(), expected.encode())


def renewal_due(start, years=1):
    """Return the renewal date (YYYY-MM-DD) ``years`` after ``start``."""
    begin = datetime.strptime(start, "%Y-%m-%d").date()
    try:
        due = begin.replace(year=begin.year + years)
    except ValueError:  # 29 February in a non-leap target year
        due = begin.replace(year=begin.year + years, day=28)
    return due.isoformat()


def print_quotes():
    """Print every saved quote."""
    print("===== Quote Book =====")
    for index, (number, quote) in enumerate(QUOTES.items(), start=1):
        print(index, number, quote["name"], "Rs.", quote["premium"])


def main():
    """Run a short demonstration of the calculator."""
    sample_xml = ("<policies>"
                  "<policy type='health' age='40' sum='300000'/>"
                  "<policy type='motor' age='abc' sum='1'/>"
                  "</policies>")
    young = Applicant(age=30)
    p1 = calculate_premium("health", 500000, young)
    p2 = calculate_premium("health", 500000, young)
    p3 = calculate_premium("motor", 800000, Applicant(age=50))
    p4 = calculate_premium("life", 100000, Applicant(age=25),
                           [1000, 1000, 1000])
    print("Quote 1:", p1)
    print("Quote 2 (same customer details):", p2)
    print("Non-smoker aged 50:", p3)
    print("Life with stacked discounts:", p4)
    print("Age from DOB 31-12-1990:", age_from_dob("31-12-1990"))
    print("Monthly instalment:", monthly_instalment(p3))
    print("Renewal due:", renewal_due("2025-03-15"))
    print("Imported:", import_policies(sample_xml))
    print("Saved as:", save_quote("Kiran", p1))
    print("Authorised (wrong token):", is_authorised("not-the-token"))
    print("Server would listen on", HOST)
    print_quotes()


if __name__ == "__main__":
    main()
