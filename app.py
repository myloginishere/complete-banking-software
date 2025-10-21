# Loans backend routes for listing, creating, viewing, and EMI posting
# Insert into app.py below existing imports and helper functions

from datetime import date

@app.route('/loans')
@require_login
def loans():
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT l.*, c.full_name
        FROM loans l JOIN customers c ON l.customer_id = c.id
        ORDER BY l.created_date DESC
    ''').fetchall()
    conn.close()
    return render_template('loans/list.html', loans=rows)

@app.route('/loans/add', methods=['GET', 'POST'])
@require_login
def add_loan():
    conn = get_db_connection()
    # defaults
    default_interest = float(conn.execute("SELECT config_value FROM system_config WHERE config_key='loan_interest_rate'").fetchone()['config_value'])
    today = datetime.now().date().strftime('%Y-%m-%d')

    eligibility = None
    if request.method == 'POST':
        form = request.form
        customer_id = int(form['customer_id'])
        loan_amount = float(form['loan_amount'])
        interest_rate = float(form['interest_rate'])
        tenure_months = int(form['tenure_months'])
        disbursement_date = form['disbursement_date']

        # eligibility checks
        ok, msg = check_loan_eligibility(customer_id, loan_amount)
        if ok:
            emi = calculate_emi(loan_amount, interest_rate, tenure_months)
            # 50% salary EMI cap
            cust = conn.execute('SELECT monthly_salary,date_of_birth FROM customers WHERE id=?', (customer_id,)).fetchone()
            if cust:
                if emi > 0.5 * cust['monthly_salary']:
                    ok = False
                    msg = f"EMI exceeds 50% of salary. Max allowed: ₹{0.5*cust['monthly_salary']:.2f}"
            # retirement/tenure cap
            retirement_age = int(conn.execute("SELECT config_value FROM system_config WHERE config_key='retirement_age'").fetchone()['config_value'])
            age = calculate_age(cust['date_of_birth'])
            remaining_years = max(0, retirement_age - age)
            max_tenure = min(int(conn.execute("SELECT config_value FROM system_config WHERE config_key='max_loan_tenure'").fetchone()['config_value']), remaining_years*12)
            if tenure_months > max_tenure:
                ok = False
                msg = f"Tenure exceeds limit. Max allowed: {max_tenure} months"
        
        if form.get('action') == 'check':
            eligibility = {'ok': ok, 'message': msg, 'emi': calculate_emi(loan_amount, interest_rate, tenure_months) if ok else None}
        else:
            if not ok:
                flash(msg, 'error')
            else:
                # create loan
                maturity = datetime.strptime(disbursement_date, '%Y-%m-%d') + timedelta(days=30*tenure_months)
                emi = calculate_emi(loan_amount, interest_rate, tenure_months)
                cur = conn.execute('''
                    INSERT INTO loans (customer_id, loan_amount, interest_rate, tenure_months, emi_amount, outstanding_principal, total_outstanding, loan_status, disbursement_date, maturity_date, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
                ''', (customer_id, loan_amount, interest_rate, tenure_months, emi, loan_amount, loan_amount, disbursement_date, maturity.strftime('%Y-%m-%d'), session['operator_id']))
                loan_id = cur.lastrowid
                # guarantors
                conn.execute('''INSERT INTO guarantors (customer_id, guarantor_name, guarantor_aadhaar, guarantor_address, guarantor_phone, relationship, guarantor_type)
                                VALUES (?, ?, ?, ?, ?, ?, 1)''', (customer_id, form['g1_name'], form['g1_aadhaar'], form['g1_address'], form.get('g1_phone',''), 'Guarantor',))
                conn.execute('''INSERT INTO guarantors (customer_id, guarantor_name, guarantor_aadhaar, guarantor_address, guarantor_phone, relationship, guarantor_type)
                                VALUES (?, ?, ?, ?, ?, ?, 2)''', (customer_id, form['g2_name'], form['g2_aadhaar'], form['g2_address'], form.get('g2_phone',''), 'Guarantor',))
                conn.commit()
                log_action('CREATE_LOAN', 'loans', loan_id, None, {'customer_id': customer_id, 'amount': loan_amount})
                conn.close()
                flash('Loan created successfully', 'success')
                return redirect(url_for('loan_detail', loan_id=loan_id))
    conn.close()
    return render_template('loans/add.html', default_interest=default_interest, today=today, eligibility=eligibility)

@app.route('/loans/<int:loan_id>')
@require_login
def loan_detail(loan_id):
    conn = get_db_connection()
    loan = conn.execute('SELECT * FROM loans WHERE id=?', (loan_id,)).fetchone()
    if not loan:
        conn.close()
        flash('Loan not found', 'error')
        return redirect(url_for('loans'))
    customer = conn.execute('SELECT * FROM customers WHERE id=?', (loan['customer_id'],)).fetchone()
    guarantors = conn.execute('SELECT * FROM guarantors WHERE customer_id=? ORDER BY guarantor_type', (loan['customer_id'],)).fetchall()
    payments = conn.execute('SELECT * FROM emi_payments WHERE loan_id=? ORDER BY payment_date', (loan_id,)).fetchall()
    conn.close()
    return render_template('loans/detail.html', loan=loan, customer=customer, guarantors=guarantors, payments=payments)

@app.route('/loans/<int:loan_id>/collect-emi', methods=['POST'])
@require_login
def collect_emi(loan_id):
    conn = get_db_connection()
    loan = conn.execute('SELECT * FROM loans WHERE id=?', (loan_id,)).fetchone()
    if not loan or loan['loan_status'] != 'active':
        conn.close()
        flash('Invalid loan state', 'error')
        return redirect(url_for('loans'))
    # compute monthly interest on outstanding principal
    monthly_rate = float(loan['interest_rate'])/(12*100)
    interest = round(loan['outstanding_principal'] * monthly_rate, 2)
    principal = round(loan['emi_amount'] - interest, 2)
    new_outstanding = max(0.0, float(loan['outstanding_principal']) - principal)

    conn.execute('''INSERT INTO emi_payments (loan_id, payment_date, emi_amount, principal_amount, interest_amount, outstanding_after_payment, payment_status, collected_by)
                    VALUES (?, DATE('now'), ?, ?, ?, ?, 'paid', ?)''', (loan_id, loan['emi_amount'], principal, interest, new_outstanding, session['operator_id']))
    # update loan outstanding
    new_status = 'completed' if new_outstanding <= 0.01 else 'active'
    conn.execute('UPDATE loans SET outstanding_principal=?, total_outstanding=?, loan_status=? WHERE id=?', (new_outstanding, new_outstanding, new_status, loan_id))
    conn.commit()
    log_action('EMI_POST', 'emi_payments', loan_id, None, {'principal': principal, 'interest': interest})
    conn.close()
    flash('Monthly EMI posted successfully', 'success')
    return redirect(url_for('loan_detail', loan_id=loan_id))
