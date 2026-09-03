from extraction.api_lookup import fetch_product_by_barcode


def test_api_lookup_mock_fallback():
    res = fetch_product_by_barcode("8595717713418")
    assert res["product_found"] is True
    assert "ketchup" in res["product_name"].lower()
    assert res["brand"] == "Vilgain"


def test_api_lookup_gs1_mock():
    res = fetch_product_by_barcode("09506000134376")
    assert res["product_found"] is True
    assert "milk" in res["product_name"].lower()
