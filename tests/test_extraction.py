from extraction.extractor import extract


def test_ocr_extraction():
    text = "Product X | MRP Rs. 50 | Net Qty 100 g | Batch No: ABC123 | EXP 12/2026 | Customer Care: +91-9892599660 | Made in India"
    data = extract(text)
    assert data["mrp"] == "50"
    assert data["net_quantity"] == "100 g"
    assert data["batch_number"] == "ABC123"
    assert data["expiry_date"] == "12/2026"
    assert data["country_of_origin"] == "India"
    assert "9892599660" in data["customer_care"]


def test_gs1_extraction():
    url = "https://id.gs1.org/01/8595717713418/10/LOT789/17/261231"
    data = extract("Sample OCR text", barcode=url)
    assert data["is_gs1"] == "True"
    assert data["barcode"] == "8595717713418"
    assert data["batch_number"] == "LOT789"
    assert data["expiry_date"] == "2026-12-31"


def test_mrp_extraction_formats():
    t1 = "MRP Rs. 150.00 (Incl. of all taxes)"
    assert extract(t1)["mrp"] == "150.00"

    t2 = "M.R.P. ₹ 1,250.00 INCL TAXES"
    assert extract(t2)["mrp"] == "1250.00"

    t3 = "Price: 99/-"
    assert extract(t3)["mrp"] == "99"


def test_relative_expiry_calculation():
    text = "MFG DATE: 05/2024\nBEST BEFORE 12 MONTHS FROM MANUFACTURE\nB.No. B240501"
    data = extract(text)
    assert data["manufacturing_date"] == "05/2024"
    assert "05/2025" in data["expiry_date"]
    assert data["batch_number"] == "B240501"


def test_net_quantity_units():
    t1 = "Net Content: 500 ml"
    d1 = extract(t1)
    assert d1["net_quantity"] == "500 ml"
    assert d1["unit_of_measurement"] == "ml"

    t2 = "NET WT. 1.5 Litre"
    d2 = extract(t2)
    assert d2["net_quantity"] == "1.5 Litre"
    assert d2["unit_of_measurement"] == "l"


def test_dot_matrix_inkjet_and_decimal_weight():
    # Test thin rotated inkjet dates and MRP
    text1 = "JUL26 JUN27\nAA26GE/30.00\nNET WEIGHT: 1.2 kg (1kg+200g FREE)\nAASHIRVAAD\nIodized SALT"
    data1 = extract(text1)
    assert "07/2026" in data1["manufacturing_date"]
    assert "06/2027" in data1["expiry_date"]
    assert data1["batch_number"] == "AA26GE"
    assert data1["mrp"] == "30.00"
    assert "1.2 kg" in data1["net_quantity"]
    assert data1["product_name"] == "Aashirvaad Iodized Salt"

    # Test dropped decimal point weight fix (e.g. 23 kg -> 2.3 kg)
    text2 = "NET WEIGHT: 23 kg\nBRAND NAME"
    data2 = extract(text2)
    assert data2["net_quantity"] == "2.3 kg"


