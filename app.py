# Certificates listing and regeneration routes

@app.route('/certificates')
@require_login
def certificates():
    q = request.args.get('q','').strip()
    type_filter = request.args.get('type','').strip()
    params = []
    where = []
    if q:
        where.append("(certificates.certificate_number LIKE ? OR customers.full_name LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    if type_filter:
        where.append("certificates.certificate_type = ?")
        params.append(type_filter)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    conn = get_db_connection()
    rows = conn.execute(f'''
        SELECT certificates.*, customers.full_name
        FROM certificates 
        JOIN customers ON customers.id = certificates.customer_id
        {where_sql}
        ORDER BY certificates.generated_date DESC
        LIMIT 200
    ''', params).fetchall()
    conn.close()
    return render_template('certificates/index.html', rows=rows, q=q, type=type_filter)

# Optional detail view (can be expanded later if needed)
@app.route('/certificates/<string:cert_no>')
@require_login
def certificate_detail(cert_no):
    conn = get_db_connection()
    cert = conn.execute('''SELECT certificates.*, customers.full_name FROM certificates 
                            JOIN customers ON customers.id=certificates.customer_id
                            WHERE certificate_number=?''', (cert_no,)).fetchone()
    conn.close()
    if not cert:
        flash('Certificate not found', 'error')
        return redirect(url_for('certificates'))
    # For now redirect back to list; template can be added later if detailed view is required
    return redirect(url_for('certificates', q=cert_no))
