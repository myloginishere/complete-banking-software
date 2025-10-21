# Complete Banking Software - User Manual
## Sumanglam Multi State Society Banking System v1.1

---

## Table of Contents

1. System Overview
2. Getting Started
3. User Roles and Permissions
4. Login and Security
5. Dashboard Overview
6. Customer Management
7. Loan Management
8. Deposit Management
9. EMI Processing
10. Reports and Analytics
11. Certificate Generation
12. Administrative Functions
13. Security Features
14. Troubleshooting
15. System Requirements
16. Quick URL Reference

---

## System Overview
Complete web-based banking for customer accounts, loans, deposits, EMIs, certificates, reports, and admin controls. Aadhaar-unique customers, professional PDFs, full audit trail, and backup logging.

## Getting Started
- Access: http://localhost:5000
- Default admin: admin / admin123 (change after first login)
- First steps (Admin): set rates and parameters in Admin → System Settings; add Operators.

## User Roles and Permissions
Admin: everything (operators, settings, certificates regeneration, backups, audit/health).
Operator: daily operations (customers, loans, deposits, EMIs, reports, generate certificates).

## Login and Security
- SHA-256 password hashing
- Session expires on browser close
- Role-based access
- Full audit logging (user, time, IP)

## Dashboard Overview
- Stats: customers, loans, outstanding, FDs, RDs
- Recent audit trail
- Quick actions

## Customer Management
- Add customer (Aadhaar unique, validation)
- View/edit profiles; salary used for eligibility, EMI caps

## Loan Management
- Eligibility: Salary × 36 minus existing outstanding
- EMI cap: total EMI ≤ 50% of salary
- Tenure: min(request) capped by retirement age (58) and max tenure (120m)
- EMI formula: EMI = [P × R × (1+R)^N] / [(1+R)^N − 1]
- Dual guarantors collected on creation
- Pages:
  - List: /loans
  - Add: /loans/add (Check Eligibility or Create Loan)
  - Detail: /loans/<id> (EMI schedule, post EMI)

## Deposit Management
- FD: amount, tenure (12/24/36m), rate, maturity amount, certificate
- RD: monthly amount, tenure (12–60m), rate, schedule auto-generated, overdue marking
- Pages:
  - Deposits home: /deposits (FD/RD lists, PDF buttons)
  - Open FD: /deposits/fd/open
  - Open RD: /deposits/rd/open
  - RD Detail: /deposits/rd/<id>

## EMI Processing
- Post monthly EMI from loan detail (principal/interest split, outstanding update, auto-complete on payoff)
- Reported in monthly report

## Reports and Analytics
- Reports home: /reports
- Monthly EMIs (paid): /reports/emis?month=YYYY-MM
- FD/RD renewals (next month): /reports/renewals?month=YYYY-MM
- Transactions export (CSV): /reports/export?from=YYYY-MM-DD&to=YYYY-MM-DD

## Certificate Generation
- One-click PDFs:
  - FD opening (row button in Deposits)
  - RD opening (row button in Deposits and RD detail)
  - Loan completion (button on Loan detail once completed)
- Listing & filters:
  - /certificates (search by number/name via q, filter by type)
- Admin-only regeneration:
  - POST from /certificates row actions
- Unique numbering: FD-, RD-, LN- + timestamp

## Administrative Functions
- Admin home: /admin
- Operators
  - Add: /admin/operators/add
  - Edit: /admin/operators/<id>/edit
  - Activate/Deactivate: /admin/operators/<id>/toggle
- System Settings (in Admin page):
  - Rates: loan, RD, FD 1Y/2Y/3Y
  - Limits: max tenure, retirement age, max EMI %, eligibility multiplier
  - Backup time (HH:MM)
- Backups
  - Manual: Run Manual Backup button (logged in system_backups)
  - Daily automation: schedule at 17:00 via OS cron/systemd hitting POST /admin/backup/run
- Audit & Health
  - Recent audit entries
  - Health snapshot: DB connectivity, active operators

## Security Features
- Password hashing; session security; role-based permissions
- Audit logging with IP
- Backups logged; cron recommended for daily

## Troubleshooting
- Login: verify credentials/caps lock; admin can reset
- Slow pages: browser cache/network
- EMI mismatch: check rates/tenure; recalc
- Certificates: verify PDF viewer and try regenerate (admin)

## System Requirements
- Python 3.8+
- Flask, ReportLab
- Modern browser (Chrome/Firefox/Edge/Safari)

## Quick URL Reference
- Login: /login
- Dashboard: /dashboard
- Customers: /customers
- Loans: /loans, /loans/add, /loans/<id>
- Deposits: /deposits, /deposits/fd/open, /deposits/rd/open, /deposits/rd/<id>
- Reports: /reports, /reports/emis, /reports/renewals, /reports/export
- Certificates: /certificates
- Admin: /admin

---

Last Updated: October 2025 (v1.1)
