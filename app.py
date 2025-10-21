# Reports backend routes (EMI monthly, renewals, CSV export)

@app.route('/reports')
@require_login
def reports():
    now = datetime.now()
    default_month = now.strftime('%Y-%m')
    default_from = (now.replace(day=1)).strftime('%Y-%m-%d')
    default_to = now.strftime('%Y-%m-%d')
    return render_template('reports/index.html', default_month=default_month, default_from=default_from, default_to=default_to)

@app.route('/reports/emis')
@require_login
def report_emis():
    month = request.args.get('month')
    if not month:
        month = datetime.now().strftime('%Y-%m')
    start = f"{month}-01"
    # end of month: add one month then minus a day
    start_dt = datetime.strptime(start, '%Y-%m-%d')
    next_month = (start_dt.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_dt = next_month - timedelta(days=1)
    end = end_dt.strftime('%Y-%m-%d')

    conn = get_db_connection()
    rows = conn.execute('''
        SELECT ep.*, c.full_name
        FROM emi_payments ep 
        JOIN loans l ON ep.loan_id = l.id
        JOIN customers c ON l.customer_id = c.id
        WHERE DATE(ep.payment_date) BETWEEN DATE(?) AND DATE(?)
        ORDER BY ep.payment_date
    ''', (start, end)).fetchall()
    conn.close()

    month_label = start_dt.strftime('%B %Y')
    return render_template('reports/emis.html', rows=rows, month_label=month_label)

@app.route('/reports/renewals')
@require_login
def report_renewals():
    month = request.args.get('month')
    if not month:
        month = datetime.now().strftime('%Y-%m')
    ref = datetime.strptime(f"{month}-01", '%Y-%m-%d')
    start_next = (ref.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_next = (start_next.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    conn = get_db_connection()
    fds = conn.execute('''
        SELECT fd.*, c.full_name
        FROM fixed_deposits fd JOIN customers c ON fd.customer_id=c.id
        WHERE DATE(fd.maturity_date) BETWEEN DATE(?) AND DATE(?)
        ORDER BY fd.maturity_date
    ''', (start_next.strftime('%Y-%m-%d'), end_next.strftime('%Y-%m-%d'))).fetchall()

    rds = conn.execute('''
        SELECT rd.*, c.full_name
        FROM recurring_deposits rd JOIN customers c ON rd.customer_id=c.id
        WHERE DATE(rd.maturity_date) BETWEEN DATE(?) AND DATE(?)
        ORDER BY rd.maturity_date
    ''', (start_next.strftime('%Y-%m-%d'), end_next.strftime('%Y-%m-%d'))).fetchall()
    conn.close()

    return render_template('reports/renewals.html', fds=fds, rds=rds)

@app.route('/reports/export')
@require_login
def export_transactions():
    from_date = request.args.get('from') or datetime.now().strftime('%Y-%m-01')
    to_date = request.args.get('to') or datetime.now().strftime('%Y-%m-%d')
    conn = get_db_connection()
    # Combine major transactional tables into one CSV: EMI payments + RD installments paid + FD opens + RD opens
    # For simplicity, output a unified schema: date,type,reference_id,customer_id,amount,notes

    rows = []
    # EMI payments
    for r in conn.execute('''SELECT payment_date as date, 'EMI' as type, loan_id as ref_id, l.customer_id as customer_id, emi_amount as amount, 'EMI posted' as notes
                             FROM emi_payments ep JOIN loans l ON ep.loan_id=l.id
                             WHERE DATE(payment_date) BETWEEN DATE(?) AND DATE(?)''', (from_date, to_date)).fetchall():
        rows.append(r)
    # RD installments marked paid
    for r in conn.execute('''SELECT payment_date as date, 'RD_INSTALLMENT' as type, rd_id as ref_id, rd.customer_id as customer_id, amount_paid as amount, payment_status as notes
                             FROM rd_installments ri JOIN recurring_deposits rd ON ri.rd_id=rd.id
                             WHERE payment_status='paid' AND DATE(payment_date) BETWEEN DATE(?) AND DATE(?)''', (from_date, to_date)).fetchall():
        rows.append(r)
    # FD opens
    for r in conn.execute('''SELECT deposit_date as date, 'FD_OPEN' as type, id as ref_id, customer_id, deposit_amount as amount, certificate_number as notes
                             FROM fixed_deposits WHERE DATE(deposit_date) BETWEEN DATE(?) AND DATE(?)''', (from_date, to_date)).fetchall():
        rows.append(r)
    # RD opens
    for r in conn.execute('''SELECT start_date as date, 'RD_OPEN' as type, id as ref_id, customer_id, monthly_amount as amount, certificate_number as notes
                             FROM recurring_deposits WHERE DATE(start_date) BETWEEN DATE(?) AND DATE(?)''', (from_date, to_date)).fetchall():
        rows.append(r)
    conn.close()

    # Build CSV
    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['date','type','reference_id','customer_id','amount','notes'])
    for r in rows:
        writer.writerow([r['date'], r['type'], r['ref_id'], r['customer_id'], r['amount'], r['notes']])
    output.seek(0)

    from flask import Response
    filename = f"transactions_{from_date}_to_{to_date}.csv"
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename={filename}'})
