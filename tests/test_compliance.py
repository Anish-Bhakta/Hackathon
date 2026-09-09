from compliance.checker import validate

def test_primary_fields_pass():
    data = {
        "mrp": "100.00",
        "manufacturing_date": "05/2024",
        "expiry_date": "05/2026",
        "net_quantity": "500 g"
    }
    _, s = validate(data)
    assert s["overall_status"] == "COMPLIANT"
    assert s["critical_passed"] == 4

def test_primary_fields_missing():
    data = {
        "mrp": "100.00",
        "manufacturing_date": "05/2024"
        # missing expiry_date and net_quantity
    }
    _, s = validate(data)
    assert s["overall_status"] == "NON-COMPLIANT"
    assert s["missing"] > 0

