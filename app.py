#!/usr/bin/env python3
"""
Complete Banking Software Solution
Created for Sumanglam Multi State Society
Author: AI Assistant
Version: 1.0
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
import calendar
import math
from functools import wraps
import json
import shutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'banking_system_secret_key_2024'  # Change this in production

# Database configuration
DATABASE = 'database/banking_system.db'

def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database with schema and default data"""
    conn = get_db_connection()
    
    # Read and execute schema
    with open('database/schema.sql', 'r') as f:
        schema = f.read()
    
    conn.executescript(schema)
    
    # Create default admin user
    admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
    conn.execute(
        'INSERT OR IGNORE INTO operators (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)',
        ('admin', admin_password, 'System Administrator', 'admin')
    )
    
    # Insert default system configuration
    default_configs = [
        ('loan_interest_rate', '12.0', 'Default loan interest rate (%)'),
        ('fd_interest_rate_1year', '8.0', 'FD interest rate for 1 year (%)'),
        ('fd_interest_rate_2year', '8.5', 'FD interest rate for 2 years (%)'),
        ('fd_interest_rate_3year', '9.0', 'FD interest rate for 3 years (%)'),
        ('rd_interest_rate', '8.0', 'RD interest rate (%)'),
        ('max_loan_tenure', '120', 'Maximum loan tenure in months'),
        ('retirement_age', '58', 'Retirement age for loan calculations'),
        ('max_emi_percentage', '50', 'Maximum EMI percentage of salary'),
        ('loan_eligibility_multiplier', '36', 'Salary multiplier for loan eligibility'),
        ('backup_time', '17:00', 'Daily backup time (24-hour format)')
    ]
    
    for config_key, config_value, description in default_configs:
        conn.execute(
            'INSERT OR IGNORE INTO system_config (config_key, config_value, description) VALUES (?, ?, ?)',
            (config_key, config_value, description)
        )
    
    conn.commit()
    conn.close()

def require_login(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'operator_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'operator_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        conn = get_db_connection()
        operator = conn.execute('SELECT role FROM operators WHERE id = ?', (session['operator_id'],)).fetchone()
        conn.close()
        
        if not operator or operator['role'] != 'admin':
            flash('Admin privileges required for this action.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def log_action(action_type, table_name=None, record_id=None, old_values=None, new_values=None):
    """Log user actions for audit trail"""
    if 'operator_id' not in session:
        return
    
    conn = get_db_connection()
    conn.execute(
        """INSERT INTO audit_trail 
           (operator_id, action_type, table_name, record_id, old_values, new_values, ip_address)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (session['operator_id'], action_type, table_name, record_id,
         json.dumps(old_values) if old_values else None,
         json.dumps(new_values) if new_values else None,
         request.remote_addr)
    )
    conn.commit()
    conn.close()

def calculate_emi(principal, rate, tenure):
    """Calculate EMI using standard banking formula"""
    monthly_rate = rate / (12 * 100)
    if monthly_rate == 0:
        return principal / tenure
    
    emi = (principal * monthly_rate * pow(1 + monthly_rate, tenure)) / (pow(1 + monthly_rate, tenure) - 1)
    return round(emi, 2)

def calculate_age(birth_date):
    """Calculate age from birth date"""
    today = datetime.now().date()
    if isinstance(birth_date, str):
        birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
    
    age = today.year - birth_date.year
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1
    return age

def check_loan_eligibility(customer_id, requested_amount):
    """Check loan eligibility based on salary and existing loans"""
    conn = get_db_connection()
    
    # Get customer details
    customer = conn.execute(
        'SELECT monthly_salary, date_of_birth FROM customers WHERE id = ?',
        (customer_id,)
    ).fetchone()
    
    if not customer:
        conn.close()
        return False, "Customer not found"
    
    # Check age for retirement
    age = calculate_age(customer['date_of_birth'])
    retirement_age = int(conn.execute(
        "SELECT config_value FROM system_config WHERE config_key = 'retirement_age'"
    ).fetchone()['config_value'])
    
    if age >= retirement_age:
        conn.close()
        return False, "Customer has reached retirement age"
    
    # Get loan eligibility multiplier
    multiplier = float(conn.execute(
        "SELECT config_value FROM system_config WHERE config_key = 'loan_eligibility_multiplier'"
    ).fetchone()['config_value'])
    
    max_eligible = customer['monthly_salary'] * multiplier
    
    # Check existing loans
    existing_loans = conn.execute(
        'SELECT SUM(total_outstanding) as total FROM loans WHERE customer_id = ? AND loan_status = "active"',
        (customer_id,)
    ).fetchone()
    
    existing_amount = existing_loans['total'] or 0
    available_amount = max_eligible - existing_amount
    
    conn.close()
    
    if requested_amount > available_amount:
        return False, f"Requested amount exceeds eligibility. Available: ₹{available_amount:,.2f}"
    
    return True, "Eligible"

@app.route('/')
def index():
    """Home page - redirect to login if not authenticated"""
    if 'operator_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = get_db_connection()
        operator = conn.execute(
            'SELECT * FROM operators WHERE username = ? AND password_hash = ? AND is_active = 1',
            (username, password_hash)
        ).fetchone()
        
        if operator:
            # Update last login
            conn.execute('UPDATE operators SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (operator['id'],))
            conn.commit()
            
            # Set session
            session['operator_id'] = operator['id']
            session['operator_name'] = operator['full_name']
            session['operator_role'] = operator['role']
            
            log_action('LOGIN')
            flash(f'Welcome, {operator["full_name"]}!', 'success')
            
            conn.close()
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
            conn.close()
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    log_action('LOGOUT')
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@require_login
def dashboard():
    """Main dashboard"""
    conn = get_db_connection()
    
    # Get dashboard statistics
    stats = {}
    
    # Total customers
    stats['total_customers'] = conn.execute('SELECT COUNT(*) as count FROM customers WHERE is_active = 1').fetchone()['count']
    
    # Active loans
    stats['active_loans'] = conn.execute('SELECT COUNT(*) as count FROM loans WHERE loan_status = "active"').fetchone()['count']
    
    # Total loan amount outstanding
    outstanding_result = conn.execute('SELECT SUM(total_outstanding) as total FROM loans WHERE loan_status = "active"').fetchone()
    stats['total_outstanding'] = outstanding_result['total'] or 0
    
    # Active FDs
    stats['active_fds'] = conn.execute('SELECT COUNT(*) as count FROM fixed_deposits WHERE fd_status = "active"').fetchone()['count']
    
    # Active RDs  
    stats['active_rds'] = conn.execute('SELECT COUNT(*) as count FROM recurring_deposits WHERE rd_status = "active"').fetchone()['count']
    
    # Recent activities (last 10 audit entries)
    recent_activities = conn.execute(
        """SELECT at.*, o.full_name as operator_name
           FROM audit_trail at
           JOIN operators o ON at.operator_id = o.id
           ORDER BY at.action_timestamp DESC
           LIMIT 10"""
    ).fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', stats=stats, recent_activities=recent_activities)

if __name__ == '__main__':
    # Initialize database
    os.makedirs('database', exist_ok=True)
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5000)