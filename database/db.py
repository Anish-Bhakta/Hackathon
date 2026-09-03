"""
Database Interface Module
Supports MySQL with automatic seamless fallback to SQLite (packaged_compliance.db)
if MySQL is not configured or unavailable.
Includes auto-migration to ensure all schema columns exist and column sizes are TEXT.
"""

import os
import sqlite3
import mysql.connector
from config import Config

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "packaged_compliance.db")


def is_mysql_available():
    try:
        con = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            connect_timeout=2
        )
        con.close()
        return True
    except Exception:
        return False


_USE_SQLITE = not is_mysql_available()


def auto_migrate_schema():
    """Auto-migrate database schema to ensure all columns exist and text columns are TEXT type."""
    required_columns = [
        ("barcode", "TEXT"),
        ("gs1_digital_link", "TEXT"),
        ("image_url", "TEXT"),
        ("api_source", "TEXT"),
        ("customer_care", "TEXT"),
    ]

    if _USE_SQLITE:
        try:
            conn = sqlite3.connect(SQLITE_PATH)
            cur = conn.cursor()
            cur.execute("""
            CREATE TABLE IF NOT EXISTS inspections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_name TEXT,
                product_name TEXT,
                manufacturer_name TEXT,
                manufacturer_address TEXT,
                mrp TEXT,
                net_quantity TEXT,
                batch_number TEXT,
                manufacturing_date TEXT,
                expiry_date TEXT,
                consumer_care TEXT,
                customer_care TEXT,
                country_of_origin TEXT,
                product_description TEXT,
                unit_of_measurement TEXT,
                barcode TEXT,
                gs1_digital_link TEXT,
                image_url TEXT,
                api_source TEXT,
                compliance_score REAL,
                overall_status TEXT,
                raw_ocr_text TEXT,
                cleaned_ocr_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cur.execute("PRAGMA table_info(inspections)")
            existing = [row[1] for row in cur.fetchall()]
            for col_name, _ in required_columns:
                if col_name not in existing:
                    cur.execute(f"ALTER TABLE inspections ADD COLUMN {col_name} TEXT")
            conn.commit()
            conn.close()
        except Exception as e:
            print("SQLite auto migration warning:", e)
    else:
        try:
            con = mysql.connector.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME
            )
            cur = con.cursor()
            cur.execute("""
            CREATE TABLE IF NOT EXISTS inspections (
                id INT AUTO_INCREMENT PRIMARY KEY,
                image_name TEXT,
                product_name TEXT,
                manufacturer_name TEXT,
                manufacturer_address TEXT,
                mrp TEXT,
                net_quantity TEXT,
                batch_number TEXT,
                manufacturing_date TEXT,
                expiry_date TEXT,
                consumer_care TEXT,
                customer_care TEXT,
                country_of_origin TEXT,
                product_description TEXT,
                unit_of_measurement TEXT,
                barcode TEXT,
                gs1_digital_link TEXT,
                image_url TEXT,
                api_source TEXT,
                compliance_score DECIMAL(5,2),
                overall_status VARCHAR(30),
                raw_ocr_text LONGTEXT,
                cleaned_ocr_text LONGTEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            con.commit()

            cur.execute("SHOW COLUMNS FROM inspections")
            existing = [row[0] for row in cur.fetchall()]
            for col_name, col_type in required_columns:
                if col_name not in existing:
                    cur.execute(f"ALTER TABLE inspections ADD COLUMN {col_name} {col_type}")
            
            # Modify VARCHAR columns to TEXT in MySQL so truncation never occurs
            for col in ["product_name", "manufacturer_name", "customer_care", "consumer_care", "country_of_origin", "mrp", "net_quantity", "batch_number"]:
                try:
                    cur.execute(f"ALTER TABLE inspections MODIFY COLUMN {col} TEXT")
                except Exception:
                    pass

            con.commit()
            cur.close()
            con.close()
        except Exception as e:
            print("MySQL auto migration warning:", e)


# Run auto-migration on import
auto_migrate_schema()


def fetch_all(query, params=()):
    if _USE_SQLITE:
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        q = query.replace("%s", "?")
        cur.execute(q, params)
        rows = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return rows
    else:
        con = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        cur = con.cursor(dictionary=True)
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        con.close()
        return rows


def execute(query, params=()):
    if _USE_SQLITE:
        conn = sqlite3.connect(SQLITE_PATH)
        cur = conn.cursor()
        q = query.replace("%s", "?")
        cur.execute(q, params)
        conn.commit()
        last_id = cur.lastrowid
        cur.close()
        conn.close()
        return last_id
    else:
        con = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        cur = con.cursor()
        cur.execute(query, params)
        con.commit()
        last_id = cur.lastrowid
        cur.close()
        con.close()
        return last_id
