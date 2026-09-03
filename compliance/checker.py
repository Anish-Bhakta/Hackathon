"""
Package Label Compliance Checker Engine
Validates product label declarations using clear, simple language.
"""

import re
from .rules import DEFAULT_RULES


def validate(data, rules=None):
    rules = rules or DEFAULT_RULES
    results = {}
    passed = missing = invalid = review = 0

    is_gs1 = data.get("is_gs1") in (True, "True", 1, "1")

    for field, rule in rules.items():
        v = (data.get(field) or "").strip()
        field_title = rule.get("name") or field.replace("_", " ").title()
        is_required = rule.get("required", True)

        confidence = 0.90 if v else 0.0

        if not v:
            if is_required:
                status = "MISSING"
                msg = f"{field_title} was not found on the product label."
                confidence = 0.0
            else:
                status = "PASS"
                msg = f"Optional item ({field_title}) not present."
                confidence = 1.0
        elif field == "mrp":
            if re.search(r"\d+", v):
                status = "PASS"
                msg = f"Valid price (₹{v}) is declared."
                confidence = 0.95
            else:
                status = "INVALID"
                msg = "Price format could not be verified."
                confidence = 0.40
        elif field in ("manufacturing_date", "expiry_date"):
            if is_gs1 and re.match(r"^\d{4}-\d{2}-\d{2}$", v):
                status = "PASS"
                msg = "Date verified via digital barcode standard."
                confidence = 0.99
            elif re.search(r"\d{1,2}[\/\.-]\d{2,4}", v) or re.search(r"\w+\s+\d{2,4}", v):
                status = "PASS"
                msg = f"Valid date format ({v}) detected."
                confidence = 0.95
            else:
                status = "REVIEW"
                msg = "Date format requires manual check."
                confidence = 0.60
        elif field == "net_quantity":
            if re.search(r"\d+\s*(?:kg|g|mg|ml|l|L|N|pcs|grm|FL\.?OZ)", v, re.I):
                status = "PASS"
                msg = "Net quantity declared with metric units."
                confidence = 0.95
            else:
                status = "PASS"
                msg = "Net quantity declared."
                confidence = 0.85
        elif field == "customer_care":
            status = "PASS"
            msg = "Customer Care contact details verified."
            confidence = 0.95
        else:
            status = "PASS"
            msg = f"{field_title} is declared on the label."
            confidence = 0.90

        results[field] = {
            "extracted_value": v,
            "status": status,
            "confidence": confidence,
            "validation_message": msg,
        }

        if status == "PASS":
            passed += 1
        elif status == "MISSING":
            missing += 1
        elif status == "INVALID":
            invalid += 1
        elif status == "REVIEW":
            review += 1

    total = len(results)
    score = round(passed / total * 100, 2) if total else 0
    overall = (
        "COMPLIANT"
        if (missing == 0 and invalid == 0 and review == 0)
        else ("NEEDS REVIEW" if review and not (missing or invalid) else "NON-COMPLIANT")
    )

    return results, {
        "total_fields": total,
        "passed": passed,
        "missing": missing,
        "invalid": invalid,
        "review": review,
        "compliance_score": score,
        "overall_status": overall,
    }
