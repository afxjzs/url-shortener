# URL Shortener Service (l.afx.cc)

Self-hosted URL shortener with click analytics and admin dashboard integration.

## Architecture

- **Redirect Service:** Standalone Flask app (`l.afx.cc/<shortcode>`)
- **Admin Panel:** Integrated into `mc.afx.cc` dashboard
- **Database:** PostgreSQL on nexus server
- **Click Tracking:** IP (base64), User-Agent, Referer logging

## Quick Start

### 1. Set Up Database

```bash
# Create database
createdb url_shortener

# The app will auto-create tables on first run
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your database connection string
```

### 4. Run the Service

```bash
python app.py
```

Server runs on `http://localhost:5000`

## API Endpoints

### Redirect
```
GET /<shortcode>
→ 302 redirect to target_url
→ Logs click with IP, User-Agent, Referer
→ Returns 404 if not found or inactive
```

### QR Code
```
GET /qr/<shortcode>
→ Returns PNG QR code image pointing to shortcode
```

### Stats (basic)
```
GET /stats/<shortcode>
→ Returns: { shortcode, target_url, click_count, created_at, active }
```

### Health
```
GET /health
→ Returns: { status: "ok" }
```

## Database Schema

### `url_shortener_shortcodes`
- `id` (UUID, PK)
- `shortcode` (VARCHAR 255, unique, indexed)
- `target_url` (TEXT)
- `created_at` (DateTime)
- `updated_at` (DateTime)
- `active` (Boolean)
- `custom` (Boolean)
- `user_id` (UUID, nullable)

### `url_shortener_clicks`
- `id` (UUID, PK)
- `shortcode_id` (UUID, FK)
- `timestamp` (DateTime, indexed)
- `ip_address` (VARCHAR, base64 encoded)
- `user_agent` (TEXT)
- `referer` (TEXT)
- `country` (VARCHAR 2, nullable)
- `city` (VARCHAR, nullable)

## Testing

### Create a Test Shortcode (manual SQL)
```sql
INSERT INTO url_shortener_shortcodes (shortcode, target_url, active, custom)
VALUES ('test', 'https://example.com', true, false);
```

### Test Redirect
```bash
curl -I http://localhost:5000/test
# Should return 302 redirect
```

### Verify Click Logged
```bash
psql url_shortener -c "SELECT * FROM url_shortener_clicks ORDER BY timestamp DESC LIMIT 1;"
```

### Get QR Code
```bash
curl http://localhost:5000/qr/test -o qr.png
# Opens qr.png showing QR code
```

## Development Phases

### Phase 1 ✅ (CURRENT)
- Database schema
- Redirect service with click tracking
- QR code generation
- Basic stats endpoint

### Phase 2 (Next)
- Admin API endpoints (CRUD for shortcodes, analytics)
- Integration with mc.afx.cc

### Phase 3
- MC dashboard admin panel (sidebar link)
- Analytics dashboard

### Phase 4
- Rate limiting (10 shortcodes/min)
- Auto-generated shortcode logic
- Docker setup
- Caddyfile routing

## Performance

Target: <10ms response time for redirects

The service uses database indexes on `shortcode` for fast lookups.

## Notes

- IP addresses are base64 encoded for privacy
- QR codes are generated dynamically on-demand
- Click logging is asynchronous to avoid slowing down redirects
- Soft deletes via `active` flag preserve analytics

## See Also

- Full PRD: `/home/afxjzs/.openclaw/workspace/SHORTENER_PRD.md`
- Implementation Brief: `/home/afxjzs/.openclaw/workspace/CODER1_SHORTENER_BRIEF.md`
