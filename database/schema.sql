-- Banking System Database Schema
-- Created for Sumanglam Multi State Society

-- Operators table for authentication
CREATE TABLE IF NOT EXISTS operators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) DEFAULT 'operator' CHECK(role IN ('admin', 'operator')),
    is_active BOOLEAN DEFAULT 1,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME
);

-- Customers table with Aadhaar-based unique accounts
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aadhaar_number VARCHAR(12) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    address TEXT NOT NULL,
    monthly_salary DECIMAL(15,2) NOT NULL,
    phone_number VARCHAR(15),
    email VARCHAR(100),
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (created_by) REFERENCES operators (id)
);

-- Guarantors table for loan applications
CREATE TABLE IF NOT EXISTS guarantors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    guarantor_name VARCHAR(100) NOT NULL,
    guarantor_aadhaar VARCHAR(12) NOT NULL,
    guarantor_address TEXT NOT NULL,
    guarantor_phone VARCHAR(15),
    relationship VARCHAR(50),
    guarantor_type INTEGER CHECK(guarantor_type IN (1, 2)), -- 1 for first guarantor, 2 for second
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers (id)
);

-- Loans table
CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    loan_amount DECIMAL(15,2) NOT NULL,
    interest_rate DECIMAL(5,2) NOT NULL,
    tenure_months INTEGER NOT NULL,
    emi_amount DECIMAL(15,2) NOT NULL,
    outstanding_principal DECIMAL(15,2) NOT NULL,
    outstanding_interest DECIMAL(15,2) DEFAULT 0,
    total_outstanding DECIMAL(15,2) NOT NULL,
    loan_status VARCHAR(20) DEFAULT 'active' CHECK(loan_status IN ('active', 'completed', 'defaulted')),
    disbursement_date DATE NOT NULL,
    maturity_date DATE NOT NULL,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    FOREIGN KEY (customer_id) REFERENCES customers (id),
    FOREIGN KEY (created_by) REFERENCES operators (id)
);

-- EMI Payments table
CREATE TABLE IF NOT EXISTS emi_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_id INTEGER NOT NULL,
    payment_date DATE NOT NULL,
    emi_amount DECIMAL(15,2) NOT NULL,
    principal_amount DECIMAL(15,2) NOT NULL,
    interest_amount DECIMAL(15,2) NOT NULL,
    outstanding_after_payment DECIMAL(15,2) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'paid' CHECK(payment_status IN ('paid', 'overdue', 'partial')),
    collected_by INTEGER,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (loan_id) REFERENCES loans (id),
    FOREIGN KEY (collected_by) REFERENCES operators (id)
);

-- Fixed Deposits table
CREATE TABLE IF NOT EXISTS fixed_deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    deposit_amount DECIMAL(15,2) NOT NULL,
    interest_rate DECIMAL(5,2) NOT NULL,
    tenure_months INTEGER NOT NULL,
    maturity_amount DECIMAL(15,2) NOT NULL,
    deposit_date DATE NOT NULL,
    maturity_date DATE NOT NULL,
    fd_status VARCHAR(20) DEFAULT 'active' CHECK(fd_status IN ('active', 'matured', 'premature_withdrawal')),
    certificate_number VARCHAR(50) UNIQUE,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    FOREIGN KEY (customer_id) REFERENCES customers (id),
    FOREIGN KEY (created_by) REFERENCES operators (id)
);

-- Recurring Deposits table
CREATE TABLE IF NOT EXISTS recurring_deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    monthly_amount DECIMAL(15,2) NOT NULL,
    interest_rate DECIMAL(5,2) NOT NULL,
    tenure_months INTEGER NOT NULL,
    maturity_amount DECIMAL(15,2) NOT NULL,
    start_date DATE NOT NULL,
    maturity_date DATE NOT NULL,
    total_deposited DECIMAL(15,2) DEFAULT 0,
    rd_status VARCHAR(20) DEFAULT 'active' CHECK(rd_status IN ('active', 'completed', 'discontinued')),
    certificate_number VARCHAR(50) UNIQUE,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    FOREIGN KEY (customer_id) REFERENCES customers (id),
    FOREIGN KEY (created_by) REFERENCES operators (id)
);

-- RD Installments table
CREATE TABLE IF NOT EXISTS rd_installments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rd_id INTEGER NOT NULL,
    installment_month DATE NOT NULL,
    amount_due DECIMAL(15,2) NOT NULL,
    amount_paid DECIMAL(15,2) DEFAULT 0,
    payment_date DATE,
    payment_status VARCHAR(20) DEFAULT 'pending' CHECK(payment_status IN ('pending', 'paid', 'overdue')),
    collected_by INTEGER,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rd_id) REFERENCES recurring_deposits (id),
    FOREIGN KEY (collected_by) REFERENCES operators (id)
);

-- System Configuration table
CREATE TABLE IF NOT EXISTS system_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value VARCHAR(500) NOT NULL,
    description TEXT,
    updated_by INTEGER,
    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES operators (id)
);

-- Certificates table
CREATE TABLE IF NOT EXISTS certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificate_number VARCHAR(50) UNIQUE NOT NULL,
    certificate_type VARCHAR(20) NOT NULL CHECK(certificate_type IN ('loan_completion', 'fd_opening', 'rd_opening')),
    customer_id INTEGER NOT NULL,
    reference_id INTEGER NOT NULL, -- loan_id, fd_id, or rd_id
    certificate_path VARCHAR(500),
    generated_by INTEGER,
    generated_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers (id),
    FOREIGN KEY (generated_by) REFERENCES operators (id)
);

-- Audit Trail table
CREATE TABLE IF NOT EXISTS audit_trail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operator_id INTEGER NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    table_name VARCHAR(50),
    record_id INTEGER,
    old_values TEXT,
    new_values TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    action_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (operator_id) REFERENCES operators (id)
);

-- System Backups table
CREATE TABLE IF NOT EXISTS system_backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_filename VARCHAR(200) NOT NULL,
    backup_size INTEGER,
    backup_type VARCHAR(20) DEFAULT 'automatic' CHECK(backup_type IN ('automatic', 'manual')),
    backup_status VARCHAR(20) DEFAULT 'completed' CHECK(backup_status IN ('completed', 'failed')),
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    FOREIGN KEY (created_by) REFERENCES operators (id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_customers_aadhaar ON customers(aadhaar_number);
CREATE INDEX IF NOT EXISTS idx_loans_customer ON loans(customer_id);
CREATE INDEX IF NOT EXISTS idx_loans_status ON loans(loan_status);
CREATE INDEX IF NOT EXISTS idx_emi_payments_loan ON emi_payments(loan_id);
CREATE INDEX IF NOT EXISTS idx_emi_payments_date ON emi_payments(payment_date);
CREATE INDEX IF NOT EXISTS idx_fd_customer ON fixed_deposits(customer_id);
CREATE INDEX IF NOT EXISTS idx_rd_customer ON recurring_deposits(customer_id);
CREATE INDEX IF NOT EXISTS idx_audit_operator ON audit_trail(operator_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_trail(action_timestamp);