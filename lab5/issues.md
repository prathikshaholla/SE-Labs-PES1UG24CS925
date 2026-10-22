# Lab 5: Issues Found in `premium_calculator.py`

Line numbers refer to the **original** file. Sources: Bandit (B), Pylint (P), Flake8 (F), and **Manual** for problems found by running the program and reading the output (no tool flagged these).

Ordered High, then Medium, then logic bugs, then Low and style.

| # | Issue | Type | Line(s) | Description | Fix Approach |
|---|-------|------|---------|-------------|--------------|
| 1 | Unsafe `tarfile.extractall` (B202, **High**) | Security | 63-65 | The archive is uploaded by customers, and `extractall` trusts every member path. A crafted `../../x` entry or a symlink can write files outside `claims_docs` (path traversal, CWE-22). The tarfile was also never closed if extraction failed. | Open with `with`, cap member count and total size, and extract with `filter="data"`, which rejects absolute paths, `..`, outside links and device files. Tested with a malicious archive: blocked. |
| 2 | Unverified SSL context (B323, **Medium**; P: W0212) | Security | 58 | `ssl._create_unverified_context()` turns off certificate and hostname checks, so a man-in-the-middle could feed us tampered rate tables (CWE-295). It also uses a private `_` API. | Use the default verified context (`urlopen` default). Add a timeout. |
| 3 | `urlopen` accepts any scheme (B310, **Medium**) | Security | 59 | `url` is not checked, so `file:///etc/passwd` or custom schemes would be fetched (CWE-22). | Reject anything but `https://` before opening. The remaining Bandit warning is a false positive after this check, so it is suppressed with a justified `# nosec`. |
| 4 | XML parsed with `xml.etree` (B314 **Medium**, B405 Low) | Security | 7, 48 | Partner XML is untrusted. `ElementTree` is vulnerable to entity-expansion ("billion laughs") attacks (CWE-20). | Use `defusedxml.ElementTree`. Tested: an entity bomb now raises `EntitiesForbidden`. |
| 5 | Bind to all interfaces (B104, **Medium**) | Security | 12 | `HOST = "0.0.0.0"` would expose the service on every network interface. | Default to `127.0.0.1`, overridable by the `PREMIUM_HOST` environment variable. |
| 6 | Hardcoded `/tmp` log path (B108, **Medium**) | Security | 14 | `/tmp` is world-writable, so other users can pre-create or symlink the file. The line is also too long (F: E501). | Default to `premium_quotes.log` in the working directory, overridable with `PREMIUM_LOG_FILE`. |
| 7 | **Mutable default argument** `discounts=[]` (P: W0102) | Logic bug | 17, 27 | The function appends `500` to the default list on every call, and that list is shared between calls. **Output showed it:** Quote 1 = 6000.0 but Quote 2 for identical customer details = 5500.0. It also silently changed a caller's own list. | Default to `None`, never mutate the argument, and drop the stray `discounts.append(500)`. Quotes 1 and 2 now both give 6000.0. |
| 8 | `smoker="no"` is treated as a smoker (**Manual**) | Logic bug | 22, 92 | Any non-empty string is truthy, so the "non-smoker aged 50" got the 1.3x smoker loading. Expected 6900 for that quote; the program printed 7970 (8970 minus 1000 of leaked discounts from bug 7). No type checking exists. | `Applicant` dataclass validates that `smoker` is a real `bool` (raises `TypeError`) and that age and claims are not negative. The unknown `policy_type` now raises a clear `ValueError` instead of a `KeyError`. |
| 9 | **Negative premium** (**Manual**) | Logic bug | 25-26, 93 | Discounts are subtracted with no limit. The life quote printed **-800.0**, which would pay the customer. | Raise `ValueError("discounts exceed the premium")`. The demo now uses valid discounts (5200.0). |
| 10 | **Age ignores the birthday** (**Manual**) | Logic bug | 30-34 | `today.year - born.year` only. For DOB 31-12-1990 it printed 36, but the person is 35 until 31 Dec. Premiums use age bands (over 45), so people near 45 were over-charged. | Subtract 1 if the birthday has not happened yet this year. Also reject a future DOB. |
| 11 | Monthly instalment loses money; `months=0` returns the full premium (**Manual**; P: R1705) | Logic bug | 67-71 | `math.floor` drops up to nearly one rupee per month (664 x 12 = 7968, not 7970). `months == 0` silently returns the whole premium as a "monthly" amount. Negative months give nonsense. | Round to 2 decimals (664.17) and raise `ValueError` for `months < 1`. Removed the needless `else`. |
| 12 | Renewal crashes on 29 Feb (**Manual**) | Logic bug | 79-81 | `date.replace(year=...)` raises `ValueError: day is out of range` for 29-02 policies when the target year is not a leap year. | Catch the error and fall back to 28 Feb. |
| 13 | Hardcoded secret + `==` comparison (B105, Low) | Security | 13, 74, 103 | The underwriter token sits in source code (and in version control), and `==` leaks timing information. | Read it from the `UNDERWRITER_TOKEN` environment variable (no default, so authorisation fails closed) and compare with `hmac.compare_digest`. Removed the real token from `main()`. |
| 14 | Predictable policy numbers (B311, Low) | Security / Logic | 37 | `random` is not secure, so numbers are guessable. With only 900,000 values, collisions overwrite earlier quotes in the dict. | `secrets.randbelow` and a loop that retries until the number is unused. |
| 15 | Bare `except: continue` (B112 Low; F: E722; P: W0702) | Quality / Security | 51-54 | Hides every error, including `KeyboardInterrupt`. Bad records vanish silently. | Catch `(TypeError, ValueError)` only and log a warning naming the skipped record. |
| 16 | Unsafe log writing (P: R1732, W1514, C0209) | Quality | 42-44 | File opened without `with` (leaks the handle on error), no encoding, `%` formatting. Names containing commas break the log, and names starting with `=` become formulas when opened in Excel (CSV injection). | `with open(..., encoding="utf-8", newline="")`, the `csv` module for quoting, and a prefix on formula-like names. |
| 17 | `main()` runs on import (**Manual**) | Quality | 107 | Importing the module for tests executes the demo and writes to the log. | Add `if __name__ == "__main__":`. |
| 18 | Too many arguments (P: R0913, R0917) | Quality | 17 | Six positional arguments. | Group age, smoker and claims into an `Applicant` dataclass. |
| 19 | Non snake_case names (P: C0103) | Style | 17, 30, 36, 39, 47, 57, 61, 67, 73, 79, 83 | 11 functions use camelCase. | Renamed all, e.g. `calculatePremium` -> `calculate_premium`. |
| 20 | Missing docstrings (P: C0114, C0116) | Style | 1, 17-89 | No module or function docstrings. | Added to the module and every function. |
| 21 | Unnecessary `else` / simplifiable `if` (P: R1705, R1703) | Style | 68-71, 74-77 | `if x: return True else: return False` patterns. | Return the expression directly. |
| 22 | `range(len(...))` loop (P: C0200) | Style | 86-87 | Clumsy indexing, and the line is too long (F: E501). | `enumerate(QUOTES.items(), start=1)`. |
| 23 | PEP 8 layout (F: E302 x12, E305, E501 x5) | Style | 17-107 | One blank line between functions, and lines over 79 characters (line 101 is 148). | Two blank lines between top-level definitions, long lines wrapped. |

## Before and after

| Tool | Before | After |
|------|--------|-------|
| Pylint | 5.73 / 10 (36 messages) | **10.00 / 10** (0 messages) |
| Bandit | 10 issues (1 High, 5 Medium, 4 Low) | **0 issues** (1 justified `# nosec`) |
| Flake8 | 19 violations | **0 violations** |

All 23 issues above were fixed (the lab required at least 4).
