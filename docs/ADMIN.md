# GO OIL DMS — Administrator Guide

**Version 5.0-enterprise · Runbook for day-2 operations**

---

## 1 · Daily
- Check `/api/health` — should be `ok`
- Skim Business Alerts page for red alerts
- Run exception scanner if unreliable data suspected: `POST /reverse/exceptions/scan`
- Verify backup ran (`ls -la /var/backups/gooil/` — expect fresh tarball today)

## 2 · Weekly
- Rotate JWT_SECRET quarterly, ADMIN_PASSWORD every 90 days
- Review notification digest deliveries once real providers are wired
- Run reconciliation (`POST /finance/reconciliation/run`) if any diffs pending

## 3 · Onboarding a new user
```bash
# via admin UI: Users → New User
# OR via curl (super_admin required):
curl -X POST $BASE/api/auth/register \
  -H "Authorization: Bearer $SUPER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"newuser@gooil.com","password":"Strong2026","name":"New User","role":"sales_executive"}'
```
Then attach party (distributor/retailer) via `/collections/users/{id}`.

## 4 · Adding a distributor
```bash
curl -X POST $BASE/api/collections/distributors \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"New Marine Ltd","gstin":"27AAAAA1111A1Z5","region":"West","credit_limit":500000}'
```

## 5 · Bulk import (Excel)
UI → Master Data → Import Excel.
Or:
```bash
curl -X POST -F "file=@products.xlsx" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$BASE/api/integrations/import/excel?collection=products"
```
Expected columns match the collection schema (see `docs/SCHEMA.md`). First row = header.

## 6 · Enabling a live integration
### Payments (Razorpay)
1. Get Key ID + Key Secret from Razorpay dashboard
2. Set env: `PAYMENT_PROVIDER=razorpay`, `RAZORPAY_KEY_ID=…`, `RAZORPAY_KEY_SECRET=…`
3. Restart backend
4. Test: `POST /api/integrations/payments/create-order` → `configured: true`

### Email (SendGrid)
1. Get API key from SendGrid
2. Set env: `EMAIL_PROVIDER=sendgrid`, `SENDGRID_API_KEY=…`, `EMAIL_FROM=noreply@your-domain.com`
3. Restart backend
4. Test: `POST /notifications/send` with your own recipient_id

### AI Copilot
1. From Emergent → Profile → Universal Key, copy the key
2. Add `EMERGENT_LLM_KEY=<key>` to `backend/.env` (or `.env.production`)
3. Restart backend
4. Test: `GET /ai/copilot/status` → `ready: true`

## 7 · Emergency (backend down)
```bash
sudo supervisorctl status backend      # RUNNING / EXITED?
sudo supervisorctl restart backend
tail -n 80 /var/log/supervisor/backend.err.log
```
Common causes:
- Missing `MONGO_URL` in .env → recreate .env or restore backup
- JWT_SECRET too short → set ≥ 32 char value
- Mongo unreachable → check `mongo` container / Atlas connectivity

## 8 · Emergency (frontend blank white screen)
```bash
sudo supervisorctl restart frontend
tail -n 40 /var/log/supervisor/frontend.err.log
```
Blank page usually = `REACT_APP_BACKEND_URL` mis-set → fix `.env` → hard reload (Ctrl-Shift-R).

## 9 · Restore from backup
```bash
./scripts/restore.sh /var/backups/gooil/gooil-dms-backup-20260728-020000.tar.gz
sudo supervisorctl restart backend
```
Verify: log in as admin, run exception scan, spot-check alerts.

## 10 · Audit trail
Every mutation writes to `audit_log`. Query by entity:
```bash
mongosh go_oil_dms --eval 'db.audit_log.find({entity_id:"inv-88ac"}).sort({timestamp:-1}).toArray()'
```
Also available in the Audit Log page.

## 11 · Contact escalation
- Platform outages → email `ops@your-domain.com`
- Data-integrity concerns → run reconciliation + attach output before contacting engineering
- Security incidents → rotate secrets and open a P1 ticket
