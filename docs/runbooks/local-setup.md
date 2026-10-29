# Local setup

Requirements: Docker Desktop, and Node 20 or newer for the demo site. The pipeline container supplies Python, Java, and dbt. The host does not need a JDK.

Spark's Windows launcher cannot start its Python worker when the interpreter path contains a space. The supported pipeline command is the container, which uses `/usr/local/bin/python`.

From the repository root:

```powershell
docker compose -f infra/docker-compose.yml up -d postgres
docker compose -f infra/docker-compose.yml --profile pipeline build pipeline
docker compose -f infra/docker-compose.yml --profile pipeline run --rm pipeline -m creditpulse.cli run --seed 42 --repayments 2000
```

That writes aggregate JSON to `web/data/`. Then:

```powershell
cd web
npm install
npm run dev
```

Open http://localhost:3000.

Host checks that do not start Spark:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m ruff check src tests
.\.venv\Scripts\python -m pytest -m "not integration"
```

The full suite, including the Postgres and Spark checks:

```powershell
docker compose -f infra/docker-compose.yml --profile pipeline run --rm pipeline -m pytest
```

GitHub Actions runs that suite on Ubuntu, where the interpreter path has no spaces, so it does not need the pipeline image.

Airflow, still local and free:

```powershell
docker compose -f infra/docker-compose.yml --profile orchestrate up -d
```

The UI is http://localhost:8080 with user `admin` and password `admin`. That password is a local placeholder, listed in `.env.example`. Trigger `creditpulse_daily`. It is not on a schedule.

The local Fernet key in the compose file is a placeholder for this demo database. Do not reuse it anywhere else.
