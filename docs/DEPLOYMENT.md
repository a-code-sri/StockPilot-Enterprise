# Putting StockPilot online (HTTPS)

This runs the same Docker stack on a cloud server, with [Caddy](https://caddyserver.com) in
front getting a free HTTPS certificate automatically. Plan for about an hour the first time.

## What you need

| | |
|---|---|
| A Linux server (VPS) | Ubuntu 24.04. **4 GB RAM** without AI, **8 GB+** with the AI assistant (CPU is fine; it is just slower). 40 GB disk. Any provider works: DigitalOcean, Hetzner, AWS Lightsail, Azure, Oracle Cloud, … |
| A domain name | e.g. `stockpilot.yourcompany.com` (a subdomain of a domain you already own is fine) |
| SSH access | the provider gives you an IP address and login |

## 1. Point the domain at the server

In your domain's DNS settings add an **A record**: name `stockpilot` (or `@` for the bare
domain) → the server's public IP. Wait until `ping stockpilot.yourcompany.com` shows that IP
(usually minutes, sometimes up to an hour).

## 2. Prepare the server

```bash
ssh root@YOUR_SERVER_IP

# Docker
curl -fsSL https://get.docker.com | sh

# Firewall: SSH + web only
ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443 && ufw --force enable

# Code
git clone https://github.com/a-code-sri/StockPilot-Enterprise.git /opt/stockpilot
cd /opt/stockpilot
```

## 3. Configure

```bash
cp .env.example .env
nano .env
```

Set at least:

```ini
POSTGRES_PASSWORD=<long random>
JWT_SECRET=<run: openssl rand -base64 48>
ADMIN_USERNAME=...   ADMIN_EMAIL=...   ADMIN_PASSWORD=<strong>
APP_ENV=production

DOMAIN=stockpilot.yourcompany.com
ACME_EMAIL=you@yourcompany.com
APP_BASE_URL=https://stockpilot.yourcompany.com
CORS_ORIGINS=https://stockpilot.yourcompany.com

# Recommended on the internet: only admins create accounts
ALLOW_REGISTRATION=false
```

Optional: SMTP settings so "Forgot password" sends emails (see `.env.example`).

## 4. Start

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
# with the AI assistant:
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile ai up -d --build
```

Open `https://stockpilot.yourcompany.com`. The first visit can take ~30 seconds while the
certificate is issued. Check with `docker compose logs caddy` if it doesn't load.

Tip: save typing with `alias dc='docker compose -f docker-compose.yml -f docker-compose.prod.yml'`.

## Updating to a new version

```bash
cd /opt/stockpilot
git pull
dc up -d --build          # migrations run automatically when the api starts
```

## Backups

The `backup` service writes a database dump to `/opt/stockpilot/backups` every day and keeps
14 days. **Also copy them off the server** — a dead server takes its disk with it:

```bash
# from your own computer, e.g. weekly
scp root@YOUR_SERVER_IP:/opt/stockpilot/backups/*.dump ./stockpilot-backups/
```

Restore (stops the app briefly):

```bash
dc stop api worker
dc exec backup backup.sh list
dc exec backup backup.sh restore stockpilot-YYYYmmdd-HHMMSS.dump
dc start api worker
```

## Security checklist

- [ ] Strong, unique `POSTGRES_PASSWORD`, `JWT_SECRET`, `ADMIN_PASSWORD`
- [ ] `ALLOW_REGISTRATION=false` (admins create users; send them a reset link to set a password)
- [ ] Firewall allows only 22, 80, 443 (the database and API ports are not published)
- [ ] Off-server backup copies
- [ ] `apt update && apt upgrade` monthly (or enable unattended-upgrades)
