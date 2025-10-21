# Certificate routes: FD opening, RD opening, Loan completion (PDF) with admin-only regeneration
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

import io


def _generate_certificate_pdf(title, fields: dict):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, height-30*mm, "Sumanglam Multi State Society")
    c.setFont("Helvetica", 12)
    c.drawCentredString(width/2, height-38*mm, title)
    # Body
    y = height - 55*mm
    c.setFont("Helvetica", 11)
    for label, value in fields.items():
        c.drawString(25*mm, y, f"{label}:")
        c.drawString(80*mm, y, str(value))
        y -= 10*mm
    # Signatures
    c.line(30*mm, 30*mm, 80*mm, 30*mm)
    c.drawString(40*mm, 25*mm, "Secretary")
    c.line(110*mm, 30*mm, 160*mm, 30*mm)
    c.drawString(125*mm, 25*mm, "Director")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def _issue_certificate_number(prefix: str):
    # Use timestamp + random suffix for uniqueness; in production, use a sequence table
    return f"{prefix}-{int(datetime.now().timestamp())}"


@app.route('/certificates/fd/<int:fd_id>/pdf')
@require_login
def cert_fd_open(fd_id):
    conn = get_db_connection()
    fd = conn.execute('SELECT * FROM fixed_deposits WHERE id=?', (fd_id,)).fetchone()
    if not fd:
        conn.close()
        flash('FD not found', 'error')
        return redirect(url_for('deposits'))
    customer = conn.execute('SELECT full_name,aadhaar_number,address FROM customers WHERE id=?', (fd['customer_id'],)).fetchone()
    # ensure certificate number exists
    cert_no = fd['certificate_number'] or _issue_certificate_number('FD')
    if not fd['certificate_number']:
        conn.execute('UPDATE fixed_deposits SET certificate_number=? WHERE id=?', (cert_no, fd_id))
        conn.commit()
    # track certificate record
    conn.execute('''INSERT OR IGNORE INTO certificates (certificate_number, certificate_type, customer_id, reference_id, generated_by)
                    VALUES (?, 'fd_opening', ?, ?, ?)''', (cert_no, fd['customer_id'], fd_id, session['operator_id']))
    conn.commit()
    conn.close()

    fields = {
        'Certificate No': cert_no,
        'Customer Name': customer['full_name'],
        'Aadhaar': customer['aadhaar_number'],
        'Address': customer['address'],
        'Deposit Amount': f"₹{fd['deposit_amount']:.2f}",
        'Interest Rate': f"{fd['interest_rate']}%",
        'Tenure': f"{fd['tenure_months']} months",
        'Deposit Date': fd['deposit_date'],
        'Maturity Date': fd['maturity_date']
    }
    pdf = _generate_certificate_pdf('Fixed Deposit Opening Certificate', fields)
    return send_file(pdf, mimetype='application/pdf', as_attachment=True, download_name=f"FD_{cert_no}.pdf")


@app.route('/certificates/rd/<int:rd_id>/pdf')
@require_login
def cert_rd_open(rd_id):
    conn = get_db_connection()
    rd = conn.execute('SELECT * FROM recurring_deposits WHERE id=?', (rd_id,)).fetchone()
    if not rd:
        conn.close()
        flash('RD not found', 'error')
        return redirect(url_for('deposits'))
    customer = conn.execute('SELECT full_name,aadhaar_number,address FROM customers WHERE id=?', (rd['customer_id'],)).fetchone()
    cert_no = rd['certificate_number'] or _issue_certificate_number('RD')
    if not rd['certificate_number']:
        conn.execute('UPDATE recurring_deposits SET certificate_number=? WHERE id=?', (cert_no, rd_id))
        conn.commit()
    conn.execute('''INSERT OR IGNORE INTO certificates (certificate_number, certificate_type, customer_id, reference_id, generated_by)
                    VALUES (?, 'rd_opening', ?, ?, ?)''', (cert_no, rd['customer_id'], rd_id, session['operator_id']))
    conn.commit()
    conn.close()

    fields = {
        'Certificate No': cert_no,
        'Customer Name': customer['full_name'],
        'Aadhaar': customer['aadhaar_number'],
        'Address': customer['address'],
        'Monthly Amount': f"₹{rd['monthly_amount']:.2f}",
        'Interest Rate': f"{rd['interest_rate']}%",
        'Tenure': f"{rd['tenure_months']} months",
        'Start Date': rd['start_date'],
        'Maturity Date': rd['maturity_date']
    }
    pdf = _generate_certificate_pdf('Recurring Deposit Opening Certificate', fields)
    return send_file(pdf, mimetype='application/pdf', as_attachment=True, download_name=f"RD_{cert_no}.pdf")


@app.route('/certificates/loan/<int:loan_id>/completion/pdf')
@require_login
def cert_loan_completion(loan_id):
    conn = get_db_connection()
    loan = conn.execute('SELECT * FROM loans WHERE id=?', (loan_id,)).fetchone()
    if not loan:
        conn.close()
        flash('Loan not found', 'error')
        return redirect(url_for('loans'))
    if loan['loan_status'] != 'completed':
        conn.close()
        flash('Loan is not completed yet', 'warning')
        return redirect(url_for('loan_detail', loan_id=loan_id))

    customer = conn.execute('SELECT full_name,aadhaar_number,address FROM customers WHERE id=?', (loan['customer_id'],)).fetchone()
    cert_no = _issue_certificate_number('LN')
    conn.execute('''INSERT INTO certificates (certificate_number, certificate_type, customer_id, reference_id, generated_by)
                    VALUES (?, 'loan_completion', ?, ?, ?)''', (cert_no, loan['customer_id'], loan_id, session['operator_id']))
    conn.commit()
    conn.close()

    fields = {
        'Certificate No': cert_no,
        'Customer Name': customer['full_name'],
        'Aadhaar': customer['aadhaar_number'],
        'Address': customer['address'],
        'Loan Amount': f"₹{loan['loan_amount']:.2f}",
        'Interest Rate': f"{loan['interest_rate']}%",
        'Tenure': f"{loan['tenure_months']} months",
        'Disbursement Date': loan['disbursement_date'],
        'Completion Date': datetime.now().strftime('%Y-%m-%d')
    }
    pdf = _generate_certificate_pdf('Loan Completion Certificate', fields)
    return send_file(pdf, mimetype='application/pdf', as_attachment=True, download_name=f"LN_{cert_no}.pdf")


# Admin-only regeneration
@app.route('/certificates/<string:cert_no>/regenerate', methods=['POST'])
@require_admin
def cert_regenerate(cert_no):
    conn = get_db_connection()
    cert = conn.execute('SELECT * FROM certificates WHERE certificate_number=?', (cert_no,)).fetchone()
    if not cert:
        conn.close()
        flash('Certificate not found', 'error')
        return redirect(url_for('reports'))
    customer = conn.execute('SELECT full_name,aadhaar_number,address FROM customers WHERE id=?', (cert['customer_id'],)).fetchone()

    if cert['certificate_type'] == 'fd_opening':
        ref = conn.execute('SELECT * FROM fixed_deposits WHERE id=?', (cert['reference_id'],)).fetchone()
        fields = {
            'Certificate No': cert_no,
            'Customer Name': customer['full_name'],
            'Aadhaar': customer['aadhaar_number'],
            'Address': customer['address'],
            'Deposit Amount': f"₹{ref['deposit_amount']:.2f}",
            'Interest Rate': f"{ref['interest_rate']}%",
            'Tenure': f"{ref['tenure_months']} months",
            'Deposit Date': ref['deposit_date'],
            'Maturity Date': ref['maturity_date']
        }
        title = 'Fixed Deposit Opening Certificate'
        filename = f"FD_{cert_no}.pdf"
    elif cert['certificate_type'] == 'rd_opening':
        ref = conn.execute('SELECT * FROM recurring_deposits WHERE id=?', (cert['reference_id'],)).fetchone()
        fields = {
            'Certificate No': cert_no,
            'Customer Name': customer['full_name'],
            'Aadhaar': customer['aadhaar_number'],
            'Address': customer['address'],
            'Monthly Amount': f"₹{ref['monthly_amount']:.2f}",
            'Interest Rate': f"{ref['interest_rate']}%",
            'Tenure': f"{ref['tenure_months']} months",
            'Start Date': ref['start_date'],
            'Maturity Date': ref['maturity_date']
        }
        title = 'Recurring Deposit Opening Certificate'
        filename = f"RD_{cert_no}.pdf"
    else:
        ref = conn.execute('SELECT * FROM loans WHERE id=?', (cert['reference_id'],)).fetchone()
        fields = {
            'Certificate No': cert_no,
            'Customer Name': customer['full_name'],
            'Aadhaar': customer['aadhaar_number'],
            'Address': customer['address'],
            'Loan Amount': f"₹{ref['loan_amount']:.2f}",
            'Interest Rate': f"{ref['interest_rate']}%",
            'Tenure': f"{ref['tenure_months']} months",
            'Disbursement Date': ref['disbursement_date'],
            'Completion Date': datetime.now().strftime('%Y-%m-%d')
        }
        title = 'Loan Completion Certificate'
        filename = f"LN_{cert_no}.pdf"
    conn.close()

    pdf = _generate_certificate_pdf(title, fields)
    return send_file(pdf, mimetype='application/pdf', as_attachment=True, download_name=filename)
