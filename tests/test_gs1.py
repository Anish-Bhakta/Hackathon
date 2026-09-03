from extraction.gs1_parser import parse_gs1_digital_link, parse_yymmdd


def test_parse_yymmdd():
    assert parse_yymmdd("261231") == "2026-12-31"
    assert parse_yymmdd("240115") == "2024-01-15"


def test_gs1_uri_parsing():
    url = "https://id.gs1.org/01/09506000134376/10/BATCH999/17/261231/21/SER1001"
    res = parse_gs1_digital_link(url)
    assert res["is_gs1"] is True
    assert res["gtin"] == "09506000134376"
    assert res["batch_number"] == "BATCH999"
    assert res["expiry_date"] == "2026-12-31"
    assert res["serial_number"] == "SER1001"


def test_gs1_parentheses_parsing():
    s = "(01)08901030300000(10)LOT456(17)260831"
    res = parse_gs1_digital_link(s)
    assert res["is_gs1"] is True
    assert res["gtin"] == "08901030300000"
    assert res["batch_number"] == "LOT456"
    assert res["expiry_date"] == "2026-08-31"
