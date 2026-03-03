# URL Shortener Service (l.afx.cc)

Self-hosted URL shortener with click analytics and admin dashboard.

## Quick Start

See [PRD](../../SHORTENER_PRD.md) for full specification.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up database
psql < schema.sql

# Run development server
python app.py
```

## Architecture

- **Redirect Service:** `l.afx.cc/<shortcode>` (302 redirects)
- **Admin Panel:** Integrated into mc.afx.cc or standalone
- **Database:** PostgreSQL on nexus
- **Analytics:** Click tracking with IP, User-Agent, Referer logging
