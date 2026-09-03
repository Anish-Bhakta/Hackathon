from compliance.checker import validate
def test_missing(): _,s=validate({"product_name":"X"}); assert s["missing"]>0
