CREATE DATABASE IF NOT EXISTS packaged_compliance; 
USE packaged_compliance;

CREATE TABLE IF NOT EXISTS inspections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    image_name VARCHAR(255),
    product_name VARCHAR(255),
    manufacturer_name VARCHAR(255),
    manufacturer_address TEXT,
    mrp VARCHAR(100),
    net_quantity VARCHAR(100),
    batch_number VARCHAR(150),
    manufacturing_date VARCHAR(100),
    expiry_date VARCHAR(100),
    consumer_care VARCHAR(100),
    country_of_origin VARCHAR(100),
    product_description TEXT,
    unit_of_measurement VARCHAR(50),
    barcode VARCHAR(255),
    gs1_digital_link TEXT,
    image_url TEXT,
    api_source VARCHAR(100),
    compliance_score DECIMAL(5,2),
    overall_status VARCHAR(30),
    raw_ocr_text LONGTEXT,
    cleaned_ocr_text LONGTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inspection_fields (
    id INT AUTO_INCREMENT PRIMARY KEY,
    inspection_id INT,
    field_name VARCHAR(100),
    extracted_value TEXT,
    status VARCHAR(20),
    confidence DECIMAL(5,2) NULL,
    validation_message TEXT,
    FOREIGN KEY (inspection_id) REFERENCES inspections(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS compliance_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    field_name VARCHAR(100) UNIQUE,
    rule_name VARCHAR(150),
    rule_description TEXT,
    is_required BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
