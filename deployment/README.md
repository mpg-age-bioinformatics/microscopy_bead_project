# WEB deployment

Deploy the published `mpgagebioinformatics/mcs_bead_proj:web` image with Docker Compose and Caddy. This setup uses a certificate supplied by your organization or certificate provider. Only TCP port **443** is published; application port 8050 stays inside the Docker network.

## Requirements

- A Linux server with Docker and Docker Compose, and a user allowed to run Docker.
- A DNS hostname pointing to the server, with TCP 443 accessible from the intended networks.
- A readable source-data directory, including any network share mounted before the containers start.
- A persistent local directory for accounts, output and certificates.
- A valid PEM certificate chain for the hostname and matching private key without an interactive passphrase.

## 1. Set your deployment variables

Copy the repository's `deployment` directory to the server, or use it from a checkout. Run the commands below in that directory using Bash.

```bash
cp -n .env.example .env
```

Edit `.env` and fill in all three values:

```dotenv
SOURCE_DATA_HOST=
RUNTIME_ROOT=
SITE_HOST=
```

| Variable | Value to provide |
| --- | --- |
| `SOURCE_DATA_HOST` | Absolute host path to the input data directory containing the source folders |
| `RUNTIME_ROOT` | Absolute host path to persistent application storage, outside the source directory and repository |
| `SITE_HOST` | Website hostname, such as `microscopy.example.org`, without `https://` or a path |

Use absolute paths rather than `~`. Quote paths containing spaces. Keep the same `RUNTIME_ROOT` when replacing containers to retain users and output.

Load your edited `.env` into the shell for the commands in this guide. Repeat this when opening a new shell or changing the values:

```bash
set -a
. ./.env
set +a
: "${SOURCE_DATA_HOST:?Set SOURCE_DATA_HOST in .env}"
: "${RUNTIME_ROOT:?Set RUNTIME_ROOT in .env}"
: "${SITE_HOST:?Set SITE_HOST in .env}"
```

Only source the `.env` file you created and edited. Shell variables override Compose's `.env` values, so reload it after edits.

## 2. Check the source and create storage

```bash
docker run --rm \
  --mount "type=bind,source=$SOURCE_DATA_HOST,target=/data,readonly" \
  alpine:3.22 ls -lah /data

mkdir -p "$RUNTIME_ROOT"/{accounts,output,certs,caddy-data,caddy-config}
chmod 700 "$RUNTIME_ROOT" "$RUNTIME_ROOT/accounts" "$RUNTIME_ROOT/certs"
```

Confirm the expected source folders appear. If access fails, check the mount and permissions with your server administrator. If you cannot create `RUNTIME_ROOT`, ask the administrator to create it and give your deployment user access.

| Location | Contents |
| --- | --- |
| `<SOURCE_DATA_HOST>/` | Input data; mounted read-only |
| `<RUNTIME_ROOT>/accounts/app.db` | Users, signing secret and update history |
| `<RUNTIME_ROOT>/output/extracted/` | Extracted records and reports |
| `<RUNTIME_ROOT>/output/backup/` | Up to 20 extraction snapshots |
| `<RUNTIME_ROOT>/certs/` | Certificate chain and private key; read-only inside Caddy |
| `<RUNTIME_ROOT>/caddy-data/`, `<RUNTIME_ROOT>/caddy-config/` | Persistent Caddy state |

`<SOURCE_DATA_HOST>` and `<RUNTIME_ROOT>` above mean the values you configured. All generated data goes under `RUNTIME_ROOT`; existing extracted data or backups beside the source are not used.

## 3. Install the certificate

Set these shell variables to the supplied PEM files, replacing the example paths:

```bash
CERT_CHAIN_FILE="/absolute/path/to/certificate-chain.pem"
CERT_KEY_FILE="/absolute/path/to/private-key.pem"

install -m 644 "$CERT_CHAIN_FILE" "$RUNTIME_ROOT/certs/fullchain.pem"
install -m 600 "$CERT_KEY_FILE" "$RUNTIME_ROOT/certs/privkey.pem"

openssl x509 -in "$RUNTIME_ROOT/certs/fullchain.pem" \
  -noout -subject -issuer -dates -checkhost "$SITE_HOST"
```

The hostname must match and the certificate must be valid. The chain must start with the server certificate, followed by intermediate certificates. Keep private keys, account databases and your local `.env` outside Git and Docker images.

## 4. Pull and validate

```bash
docker compose config --quiet
docker compose pull
docker compose run --rm --no-deps caddy \
  caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

Continue when validation succeeds. Caddy reads `SITE_HOST` from the container environment using its [environment-variable syntax](https://caddyserver.com/docs/caddyfile/concepts#environment-variables). Automatic certificate issuance and renewal are disabled because this setup uses supplied certificates; HTTPS remains enabled.

## 5. Create the administrator once

**Skip this step if `<RUNTIME_ROOT>/accounts/app.db` already exists.**

```bash
docker compose run --rm --no-deps app python3 auth.py init --username admin
```

Enter a password of 8–256 characters. You must change it at first sign-in. Do not rerun initialization for an image update.

## 6. Start and verify

```bash
docker compose up -d
docker compose ps
docker compose logs --tail=100 -f app caddy
```

Startup processes the source data before starting Gunicorn. The first run extracts everything; later starts normally process incrementally. Network-share processing can take several minutes. Caddy may return **502 / connection refused** until Gunicorn listens on port 8050. Check that extraction completes successfully. Press **Ctrl+C** to leave the logs without stopping the containers.

Check HTTPS from the server:

```bash
curl -I --connect-timeout 10 --max-time 20 \
  --resolve "${SITE_HOST}:443:127.0.0.1" \
  "https://${SITE_HOST}/login"
```

Expect `HTTP/2 200`. Open `https://<SITE_HOST>` from an allowed network, sign in, and check the dashboard and Downloads. If the local check works but the browser cannot connect, check DNS and firewall access. Certificate trust errors require checking the chain or the organization's CA trust.

## Users and data updates

- Administrators manage users at `/admin/users` and trigger incremental updates or a full refetch at `/admin`.
- Only one data update can run at a time. Keep one application container and the image's single Gunicorn worker process.
- Administrators use `/download` for records, reports and backup archives. Excel and HTML exports are generated on request.
- Update summaries remain in `accounts/app.db`; the interface shows the latest 10 entries.

## Deploy a newer image

From the deployment directory, wait for active updates and exports to finish, then run:

```bash
docker compose pull app
docker compose up -d app
docker compose logs --tail=100 -f app
```

Accounts and output persist. Do not clear output or initialize accounts again. If adopting this configuration from an older deployment with a fixed hostname, add `SITE_HOST` to your existing `.env` before using the new Compose file and Caddyfile together.

## Renew the certificate

Arrange renewal with your certificate provider. Set `CERT_CHAIN_FILE` and `CERT_KEY_FILE` to the renewed files and repeat the installation and validation steps above. Then reload Caddy:

```bash
docker compose exec caddy \
  caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile --force
```

Verify HTTPS again. Replacing the original supplied files alone does not update the copies in `<RUNTIME_ROOT>/certs/`.

## Logs and backups

```bash
docker compose logs --tail=200 app
docker compose logs -f app caddy
```

Docker logs rotate at 10 MB per file, up to 3 files per container, and are removed with the container. The admin page keeps the latest 200 detailed log lines in memory, cleared on restart or the next update. Update summaries persist in the database.

Back up `RUNTIME_ROOT`, especially `accounts` and `output`, with restricted access to private keys. Use a SQLite-aware backup or stop the application while copying its database. The 20 extraction snapshots do not back up user accounts. Arrange source-data backups separately and monitor free space for both runtime storage and Docker.

To stop the deployment without deleting persistent data:

```bash
docker compose down
```
