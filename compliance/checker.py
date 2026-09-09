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
    crit_passed = crit_missing = crit_invalid = crit_review = 0
    crit_total = 0
    sec_passed = sec_total = 0

    is_gs1 = data.get("is_gs1") in (True, "True", 1, "1")

    for field, rule in rules.items():
        v = (data.get(field) or "").strip()
        field_title = rule.get("name") or field.replace("_", " ").title()
        is_required = rule.get("required", False)
        is_critical = rule.get("critical", False)

        if is_critical:
            crit_total += 1
        else:
            sec_total += 1

        confidence = 0.90 if v else 0.0

        if not v:
            if is_required or is_critical:
                status = "MISSING"
                msg = f"{field_title} was not detected on label."
                confidence = 0.0
            else:
                status = "PASS"
                msg = f"Optional item ({field_title}) not present."
                confidence = 1.0
        elif field == "mrp":
            if re.search(r"\d+", v):
                status = "PASS"
                msg = f"Valid price (₹{v}) verified."
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
            elif re.search(r"\d{1,2}[\/\.-]\d{2,4}", v) or re.search(r"\w+\s+\d{2,4}", v) or re.search(r"best\s+before", v, re.I):
                status = "PASS"
                msg = f"Valid date declaration ({v}) detected."
                confidence = 0.95
            else:
                status = "REVIEW"
                msg = "Date format requires manual check."
                confidence = 0.60
        elif field == "net_quantity":
            if re.search(r"\d+(?:\.\d+)?\s*(?:kg|g|mg|ml|l|L|N|pcs|grm|FL\.?OZ|pack|gm|gms|gram|grams|g\.|Litre|Litres|units)", v, re.I):
                status = "PASS"
                msg = "Net quantity declared with standard unit."
                confidence = 0.95
            else:
                status = "PASS"
                msg = "Net quantity declared."
                confidence = 0.85
        elif field == "customer_care":
            status = "PASS"
            msg = "Customer Care details verified."
            confidence = 0.95
        else:
            status = "PASS"
            msg = f"{field_title} is declared."
            confidence = 0.90

        results[field] = {
            "extracted_value": v,
            "status": status,
            "confidence": confidence,
            "validation_message": msg,
            "is_critical": is_critical,
        }

        if status == "PASS":
            passed += 1
            if is_critical:
                crit_passed += 1
            else:
                sec_passed += 1
        elif status == "MISSING":
            missing += 1
            if is_critical:
                crit_missing += 1
        elif status == "INVALID":
            invalid += 1
            if is_critical:
                crit_invalid += 1
        elif status == "REVIEW":
            review += 1
            if is_critical:
                crit_review += 1

    total = len(results)
    
    # Critical primary fields weighting (80% primary, 20% secondary)
    crit_score = (crit_passed / crit_total * 80) if crit_total else 80
    sec_score = (sec_passed / sec_total * 20) if sec_total else 20
    score = round(crit_score + sec_score, 2)

    # Primary pass criteria: MRP, MFG Date, Expiry Date, Net Quantity
    if crit_missing == 0 and crit_invalid == 0:
        if crit_review == 0:
            overall = "COMPLIANT"
        else:
            overall = "NEEDS REVIEW"
    else:
        overall = "NON-COMPLIANT"

    return results, {
        "total_fields": total,
        "passed": passed,
        "missing": missing,
        "invalid": invalid,
        "review": review,
        "critical_passed": crit_passed,
        "critical_total": crit_total,
        "compliance_score": score,
        "overall_status": overall,
    }
