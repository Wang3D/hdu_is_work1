# Work 1 — Secure REST API and CVE analysis

This is a local implementation of Work 1 from the HDU Information Security lab
manual. The remote Git repository step is intentionally left for later.

## Local setup with PostgreSQL

In PowerShell, from this folder:

```powershell
.\Setup.ps1 -Python python
.\.venv\Scripts\python.exe manage.py init-db
.\.venv\Scripts\python.exe manage.py create-user --login student
.\Start.ps1
```

`Setup.ps1` creates a dedicated database `hdu_is_work1`, a least-privilege
login `work1_app`, and random local secrets in ignored `.env`. It refuses to
modify an existing database or role. If PostgreSQL is not on `PATH`, the Python
driver still works, but the PostgreSQL server must be running.

## API calls

```powershell
$login = Invoke-RestMethod http://127.0.0.1:5000/auth/login `
  -Method Post -ContentType 'application/json' `
  -Body '{"login":"student","password":"your-password"}'
$token = $login.access_token

Invoke-RestMethod http://127.0.0.1:5000/api/data `
  -Headers @{Authorization="Bearer $token"}
Invoke-RestMethod http://127.0.0.1:5000/api/data `
  -Method Post -ContentType 'application/json' `
  -Headers @{Authorization="Bearer $token"} `
  -Body '{"content":"first note"}'
```

Endpoints are `GET /health`, `POST /auth/login`, `GET /api/data`, and
`POST /api/data`. Protected endpoints return HTTP 401 without a valid bearer
token.

## Security controls

- All SQL uses psycopg parameter binding; input is never concatenated into SQL.
- Passwords are stored as bcrypt hashes, never plaintext.
- Login issues a 15-minute HS256 JWT with issuer, audience, subject, issued-at,
  and expiry claims. Protected routes validate those claims.
- Login errors are generic, input is validated, and data length is bounded.
- User-controlled text is HTML-escaped before it is returned.
- The database role cannot create databases or roles, and `.env` is ignored.

## CI security checks

`.github/workflows/ci.yml` runs on every push and pull request. It runs Bandit
(SAST), pip-audit (dependency/SCA), and pytest. Local checks:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m bandit -r app manage.py run.py -ll
```

## CVE case study — CVE-2019-0193 (Apache Solr)

The selected CVE is Apache Solr DataImportHandler remote command execution.
The isolated Vulhub environment is already prepared at:

```text
..\vulhub\solr\CVE-2019-0193
```

Start and inspect the local environment:

```powershell
Set-Location 'C:\Users\GuppyCat\Desktop\Home\Information Security\vulhub\solr\CVE-2019-0193'
docker compose up -d
docker compose ps
```

The lab uses Apache Solr 8.1.1 and exposes the local admin interface at
`http://127.0.0.1:8983/`. Read the lab README before performing the
verification request. Use only the harmless proof command shown there
(`touch /tmp/success`), and record the exact request and container output for
the report. Do not expose the container to the internet.

Root cause: the DataImportHandler allowed an external `dataConfig` value to
define a script-based transformer. The script could invoke Java runtime
functionality, so an unauthenticated attacker could submit a crafted import
configuration and execute a command in the Solr container.

The remediation is to disable or remove the vulnerable DataImportHandler
configuration, prevent untrusted clients from submitting `dataConfig`, and
upgrade Solr to a vendor-fixed release. Stop the vulnerable container, apply
the selected version/configuration fix, rebuild, and repeat the same harmless
request. The proof file must no longer be created, while the Solr admin page
and normal `demo` core functionality must still work:

```powershell
docker compose down
docker compose up --build -d
docker compose ps
```

## Evidence checklist

- Successful login, 401 without a token, and protected data screenshots.
- Bandit and pip-audit output with no high/critical findings.
- Vulhub startup, reproduction request, root-cause notes, patched rebuild, and
  repeated request showing that the proof file is no longer created.
- `pytest -q` regression output.
