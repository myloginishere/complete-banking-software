# Admin backend routes: operators, settings, backup, audit, health

@app.route('/admin')
@require_admin
def admin_home():
    conn = get_db_connection()
    operators = conn.execute('SELECT * FROM operators ORDER BY created_date DESC').fetchall()
    cfg_rows = conn.execute('SELECT config_key,config_value FROM system_config').fetchall()
    backups = conn.execute('SELECT * FROM system_backups ORDER BY created_date DESC LIMIT 20').fetchall()
    audits = conn.execute('''SELECT at.*, o.full_name as operator_name FROM audit_trail at 
                              JOIN operators o ON at.operator_id=o.id
                              ORDER BY action_timestamp DESC LIMIT 10''').fetchall()
    # health
    db_ok = True
    try:
        conn.execute('SELECT 1').fetchone()
    except:
        db_ok = False
    active_operators = conn.execute('SELECT COUNT(*) as c FROM operators WHERE is_active=1').fetchone()['c']
    conn.close()

    cfg = {r['config_key']: r['config_value'] for r in cfg_rows}
    health = {
        'db_ok': db_ok,
        'pending_backups': 0,
        'active_operators': active_operators
    }
    return render_template('admin/index.html', operators=operators, cfg=cfg, backups=backups, audits=audits, health=health)

@app.route('/admin/operators/add', methods=['GET','POST'])
@require_admin
def admin_operator_add():
    if request.method=='POST':
        f = request.form
        username = f['username']
        password_hash = hashlib.sha256(f['password'].encode()).hexdigest()
        full_name = f['full_name']
        role = f.get('role','operator')
        conn = get_db_connection()
        conn.execute('INSERT INTO operators (username, password_hash, full_name, role, is_active) VALUES (?, ?, ?, ?, 1)',
                     (username, password_hash, full_name, role))
        conn.commit()
        conn.close()
        flash('Operator added', 'success')
        return redirect(url_for('admin_home'))
    return render_template_string('''{% extends "base.html" %}{% block content %}
        <h3 class="mt-3">Add Operator</h3>
        <form method="POST" class="card card-body mt-3">
          <div class="row g-3">
            <div class="col-md-4"><label class="form-label">Username</label><input class="form-control" name="username" required></div>
            <div class="col-md-4"><label class="form-label">Password</label><input class="form-control" name="password" type="password" required></div>
            <div class="col-md-4"><label class="form-label">Full Name</label><input class="form-control" name="full_name" required></div>
            <div class="col-md-4"><label class="form-label">Role</label><select class="form-select" name="role"><option value="operator">operator</option><option value="admin">admin</option></select></div>
          </div>
          <div class="mt-3"><button class="btn btn-primary" type="submit">Save</button> <a href="{{ url_for('admin_home') }}" class="btn btn-outline-secondary">Cancel</a></div>
        </form>
      {% endblock %}''')

@app.route('/admin/operators/<int:op_id>/edit', methods=['GET','POST'])
@require_admin
def admin_operator_edit(op_id):
    conn = get_db_connection()
    op = conn.execute('SELECT * FROM operators WHERE id=?', (op_id,)).fetchone()
    if not op:
        conn.close()
        flash('Operator not found', 'error')
        return redirect(url_for('admin_home'))
    if request.method=='POST':
        f = request.form
        full_name = f['full_name']
        role = f.get('role','operator')
        is_active = 1 if f.get('is_active')=='on' else 0
        conn.execute('UPDATE operators SET full_name=?, role=?, is_active=? WHERE id=?', (full_name, role, is_active, op_id))
        conn.commit()
        conn.close()
        flash('Operator updated', 'success')
        return redirect(url_for('admin_home'))
    conn.close()
    return render_template_string('''{% extends "base.html" %}{% block content %}
        <h3 class="mt-3">Edit Operator</h3>
        <form method="POST" class="card card-body mt-3">
          <div class="row g-3">
            <div class="col-md-4"><label class="form-label">Full Name</label><input class="form-control" name="full_name" value="{{ op.full_name }}" required></div>
            <div class="col-md-4"><label class="form-label">Role</label><select class="form-select" name="role"><option value="operator" {% if op.role=='operator' %}selected{% endif %}>operator</option><option value="admin" {% if op.role=='admin' %}selected{% endif %}>admin</option></select></div>
            <div class="col-md-4 form-check mt-4"><input class="form-check-input" type="checkbox" name="is_active" {% if op.is_active %}checked{% endif %}> <label class="form-check-label">Active</label></div>
          </div>
          <div class="mt-3"><button class="btn btn-primary" type="submit">Save</button> <a href="{{ url_for('admin_home') }}" class="btn btn-outline-secondary">Cancel</a></div>
        </form>
      {% endblock %}''', op=op)

@app.route('/admin/operators/<int:op_id>/toggle', methods=['POST'])
@require_admin
def admin_operator_toggle(op_id):
    conn = get_db_connection()
    cur = conn.execute('SELECT is_active FROM operators WHERE id=?', (op_id,)).fetchone()
    if cur:
        new_state = 0 if cur['is_active'] else 1
        conn.execute('UPDATE operators SET is_active=? WHERE id=?', (new_state, op_id))
        conn.commit()
    conn.close()
    flash('Operator status updated', 'success')
    return redirect(url_for('admin_home'))

@app.route('/admin/settings/save', methods=['POST'])
@require_admin
def admin_settings_save():
    conn = get_db_connection()
    for k,v in request.form.items():
        conn.execute('INSERT INTO system_config (config_key,config_value) VALUES (?,?) ON CONFLICT(config_key) DO UPDATE SET config_value=excluded.config_value, updated_date=CURRENT_TIMESTAMP', (k, v))
    conn.commit()
    conn.close()
    flash('Settings saved', 'success')
    return redirect(url_for('admin_home'))

# Backup simulation daily at configured time and manual trigger
@app.route('/admin/backup/run', methods=['POST'])
@require_admin
def admin_backup_run():
    filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    # simulate backup file in backups folder
    os.makedirs('backups', exist_ok=True)
    open(os.path.join('backups', filename), 'wb').close()
    size = 0
    conn = get_db_connection()
    conn.execute('INSERT INTO system_backups (backup_filename, backup_size, backup_type, backup_status, created_by) VALUES (?, ?, '"manual"', '"completed"', ?)', (filename, size, session['operator_id']))
    conn.commit()
    conn.close()
    flash('Backup completed', 'success')
    return redirect(url_for('admin_home'))
