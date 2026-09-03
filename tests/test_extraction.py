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
