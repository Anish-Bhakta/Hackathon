"""
Product Label Required Rules Definition
Simple declaration rules required on packaged products.
"""

REQUIRED_LABEL_RULES = {
    "mrp": {
        "name": "Maximum Retail Price (MRP)",
        "description": "Retail price including all taxes.",
        "required": True,
        "critical": True,
        "active": True
    },
    "manufacturing_date": {
        "name": "Manufacturing Date",
        "description": "Month and year when the item was packed.",
        "required": True,
        "critical": True,
        "active": True
    },
    "expiry_date": {
        "name": "Expiry / Best Before Date",
        "description": "Date until which the product is safe to use.",
        "required": True,
        "critical": True,
        "active": True
    },
    "net_quantity": {
        "name": "Net Quantity",
        "description": "Weight or volume in standard units (g, kg, ml, L).",
        "required": True,
        "critical": True,
        "active": True
    },
    "product_name": {
        "name": "Product Name",
        "description": "The generic or common name of the item.",
        "required": False,
        "critical": False,
        "active": True
    },
    "manufacturer_name": {
        "name": "Manufacturer Name",
        "description": "Name of the company that made or packed the item.",
        "required": False,
        "critical": False,
        "active": True
    },
    "manufacturer_address": {
        "name": "Manufacturer Address",
        "description": "Full address of the manufacturer or importer.",
        "required": False,
        "critical": False,
        "active": True
    },
    "batch_number": {
        "name": "Batch / Lot Number",
        "description": "Code or lot number for product tracking.",
        "required": False,
        "critical": False,
        "active": True
    },
    "customer_care": {
        "name": "Customer Care Helpline",
        "description": "Contact details for customer questions or complaints.",
        "required": False,
        "critical": False,
        "active": True
    },
    "country_of_origin": {
        "name": "Country of Origin",
        "description": "Country where the product was manufactured.",
        "required": False,
        "critical": False,
        "active": True
    },
    "product_description": {
        "name": "Product Description",
        "description": "Short description or ingredients list.",
        "required": False,
        "critical": False,
        "active": True
    },
    "unit_of_measurement": {
        "name": "Unit of Measurement",
        "description": "Standard weight/volume unit symbol (g, kg, ml, L).",
        "required": False,
        "critical": False,
        "active": True
    }
}

DEFAULT_RULES = REQUIRED_LABEL_RULES
