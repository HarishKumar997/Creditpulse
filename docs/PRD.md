# CreditPulse — Credit Risk Data Engineering Platform
**Product Requirements Document (PRD)**  
**Version:** 1.0 · **Status:** Portfolio specification · **Owner:** Harish Kumar  
**Last updated:** 29 October 2026

> **Project positioning:** A production-minded, synthetic-data portfolio project demonstrating how to ingest, validate, transform, orchestrate, test, observe, and serve financial data. CreditPulse is an engineering demonstration—not a real credit bureau, lending decision engine, or production credit-scoring service.

## 1. Executive summary

CreditPulse is an end-to-end data platform that turns messy customer, account, loan, and repayment data into trusted analytical datasets for risk analysts and data scientists. It combines a local development environment with a Databricks lakehouse implementation and a lightweight recruiter-facing web experience.

The platform demonstrates the practical responsibilities of a data engineer: reliable ingestion, schema enforcement, incremental processing, deduplication, historical tracking, data quality, orchestration, reproducibility, observability, security, and cost-aware design.

**Core principle:** make the pipeline explainable, rerunnable, testable, and measurable before making it large.

## 2. Problem statement

Financial analytics teams receive data from multiple systems, with inconsistent schemas, late-arriving records, duplicate events, missing identifiers, and changing customer/account attributes. If these issues are not handled systematically, dashboards and downstream models can produce inconsistent results.

CreditPulse simulates this problem with generated data and provides a documented pipeline that:
- preserves raw source records for traceability;
- validates and standardizes records;
- tracks changes over time;
- produces analytics-ready tables;
- detects quality failures and pipeline regressions;
- supports safe reruns and incremental loads; and
- exposes synthetic, aggregated outputs through a read-only demo.

## 3. Goals and measurable outcomes

### Product goals
1. Demonstrate an end-to-end batch data engineering workflow.
2. Show both local development and a cloud lakehouse path.
3. Make data quality and failure recovery first-class features.
4. Give a recruiter a clear, quick way to understand the system and inspect evidence.
5. Keep the project reproducible without paid services or real personal data.

### Engineering success criteria
- A clean setup can run locally using documented commands.
- Re-running the same input does not create duplicate business records.
- Invalid records are quarantined with a reason code rather than silently discarded.
- Incremental processing only handles new/changed records after the initial load.
- A simulated failed task can be retried without corrupting downstream tables.
- Automated tests run in CI and fail the build when a critical rule breaks.
- Gold-layer metrics reconcile to documented source totals within stated rules.
- The README links to architecture, tests, data dictionary, decisions, and demo.
- Performance claims are backed by reproducible measurements, not estimates.

**Suggested portfolio benchmark:** start with 100,000–1,000,000 synthetic repayment events on a developer machine. Report actual runtime and environment. Treat this as a test workload, not a claim of enterprise scale.

## 4. Non-goals

- Using real consumer credit records or personally identifiable information.
- Building a legally valid credit score or making lending decisions.
- Claiming production deployment, enterprise scale, or cloud certification without evidence.
- Running Spark or long-running ETL jobs inside Vercel Functions.
- Integrating every popular data tool just to inflate the stack.
- Building a full commercial credit bureau or multi-tenant SaaS product.

## 5. Users and use cases

### Primary users
- **Data engineer:** builds, tests, operates, and troubleshoots pipelines.
- **Risk analyst:** explores curated portfolio-level indicators.
- **Data scientist:** consumes consistent, documented features.
- **Recruiter / engineering interviewer:** reviews architecture, code quality, test evidence, and technical decisions.

### Representative user stories
- As a data engineer, I can ingest a daily file and know which records were accepted, rejected, or duplicated.
- As a data engineer, I can rerun a failed batch safely without double-counting payments.
- As an analyst, I can query curated loan and repayment metrics by reporting date and product segment.
- As a data scientist, I can use a documented Gold table with stable column definitions.
- As an interviewer, I can follow the architecture from source to output and reproduce the local demo.

## 6. Scope and delivery phases

### Phase 1 — Local MVP (required)
- Python ingestion from CSV and a small mock REST API.
- PostgreSQL as the local operational/reference database and serving warehouse.
- Local files in Parquet format for raw and transformed batches.
- PySpark transformations for cleaning, deduplication, joins, and aggregates.
- Bronze / Silver / Gold logical layers.
- Data quality checks, quarantine output, structured logging, and unit tests.
- Docker Compose for PostgreSQL and local dependencies.
- GitHub Actions CI for linting and tests.
- Synthetic sample data and a deterministic generator.

### Phase 2 — Orchestration and transformation quality
- Apache Airflow DAG with task dependencies, retries, timeouts, and backfill.
- dbt models for warehouse transformations, documentation, and tests.
- Idempotent batch processing and a pipeline-run audit table.
- Data quality checks such as uniqueness, not-null, accepted values, and referential integrity.

### Phase 3 — Databricks lakehouse
- PySpark notebooks or Python wheel executed on Databricks.
- Delta Lake tables for Bronze, Silver, and Gold.
- Databricks Workflows/Jobs for scheduling the cloud pipeline.
- Incremental ingestion pattern appropriate to the chosen source.
- Documented permissions, secrets handling, lineage/monitoring where available.
- Clearly label any Databricks Free Edition limitations and keep local execution usable.

### Phase 4 — Recruiter-facing experience
- A small Next.js/TypeScript dashboard or static project site.
- Vercel deployment for the frontend and public documentation.
- Display precomputed, synthetic aggregate outputs only.
- Show pipeline run status, data-quality summary, Gold metrics, and architecture.
- Link to GitHub source, tests, data dictionary, design decisions, and demo limitations.

### Optional stretch goals (only after the core works)
- Kafka or Redpanda for event streaming.
- MongoDB as an additional document-source simulation (not a second warehouse).
- Terraform for reproducible cloud infrastructure.
- OpenLineage/Marquez or platform-native lineage.
- Great Expectations or Soda if a dedicated data-quality framework adds value.
- A cloud object store and warehouse on one chosen provider.
- A feature table and a simple, clearly labelled research-only risk model.

## 7. Functional requirements

| ID | Requirement | Priority | Acceptance criteria |
|---|---|---|---|
| FR-01 | Generate synthetic entities and events | Must | Same seed produces reproducible data; no real personal data |
| FR-02 | Ingest CSV and mock API data | Must | Captures batch ID, source, ingestion timestamp, row counts, and errors |
| FR-03 | Validate schema and required fields | Must | Invalid rows receive explicit rejection reasons |
| FR-04 | Deduplicate records | Must | Business key and event/version rules are documented and tested |
| FR-05 | Process incrementally | Must | Watermark or source cursor is persisted; rerun is safe |
| FR-06 | Maintain Bronze/Silver/Gold layers | Must | Raw data is retained; curated layers can be rebuilt |
| FR-07 | Create historical customer/account records | Should | SCD Type 2 includes effective start/end dates and current-row flag |
| FR-08 | Build analytical data model | Must | Documented facts, dimensions, grain, keys, and metric definitions |
| FR-09 | Orchestrate pipeline | Should | DAG dependencies, retries, timeouts, and backfill are demonstrated |
| FR-10 | Test transformations and data quality | Must | Unit, integration, and warehouse tests run in CI where feasible |
| FR-11 | Record pipeline execution metadata | Must | Run ID, status, timings, counts, and error summary are queryable |
| FR-12 | Expose aggregate demo outputs | Should | Public demo contains synthetic aggregates only and is read-only |
| FR-13 | Document local setup | Must | A new user can follow the README from clone to successful run |
| FR-14 | Measure performance | Should | Benchmark command, machine/environment, input size, and results documented |

## 8. Data design

### Synthetic source entities
- **customers:** customer_id, created_at, region_code, customer_segment, status.
- **accounts:** account_id, customer_id, account_type, opened_at, closed_at, status.
- **loans:** loan_id, account_id, product_code, principal_amount, annual_rate, origination_date, maturity_date, loan_status.
- **repayments:** repayment_id, loan_id, event_timestamp, due_amount, paid_amount, payment_status, source_updated_at.
- **source_events:** event_id, entity_type, operation, event_timestamp, payload, source_updated_at.

All names, identifiers, and values are synthetic. Do not generate realistic government IDs, actual account numbers, or real personal records.

### Target model
- `dim_customer` — customer attributes with SCD Type 2 history where implemented.
- `dim_account` — account attributes.
- `dim_date` — calendar dimensions.
- `fact_loan_snapshot` — one row per loan per snapshot date (grain must be explicit).
- `fact_repayment` — one row per unique repayment event.
- `agg_portfolio_daily` — daily aggregate balances, due/paid amounts, delinquency buckets, and counts.

### Example derived metrics
- repayment completion rate = eligible paid amount / eligible due amount, with null/zero-denominator rules documented;
- delinquency rate by a defined overdue-day threshold;
- outstanding balance proxy, with assumptions stated;
- count of accepted, rejected, and duplicate events per batch.

These are illustrative analytical definitions, not official credit bureau metrics. Every metric must have a definition, grain, exclusions, and tests.

## 9. Data processing design

### Bronze
Persist source-aligned records with ingestion metadata: `ingested_at`, `source_name`, `batch_id`, and a payload/schema version when appropriate. Preserve source values for auditability. Avoid silently overwriting raw inputs.

### Silver
Normalize timestamps and types; standardize controlled values; deduplicate using documented business keys; validate references; quarantine invalid records with `reject_reason`; handle late-arriving updates explicitly.

### Gold
Publish stable, documented facts, dimensions, and aggregates designed for analyst queries. Define table grain and business logic. Add dbt tests and reconciliation checks where applicable.

### Incremental processing and idempotency
- Use a stable business/event key and source update timestamp or cursor.
- Persist run metadata and the last successfully committed watermark.
- Advance the watermark only after the required output is committed.
- Use merge/upsert or deterministic replacement strategies appropriate to the target.
- Make retry behavior explicit; avoid assuming exactly-once delivery across independent systems.
- Include a replay/backfill procedure and test it.

## 10. Technology decisions

| Concern | Primary choice | Why | Alternative / boundary |
|---|---|---|---|
| Language | Python | Ingestion, utilities, testing, orchestration glue | Keep business logic modular |
| Distributed processing | PySpark | Demonstrates distributed transformations | Pandas only for small local tasks |
| Lakehouse | Databricks + Delta Lake | Cloud execution and transactional lakehouse tables | Local PySpark/Parquet for reproducibility |
| Local database | PostgreSQL | Relational integrity, SQL serving, familiar local setup | Do not use it as a substitute for the lakehouse |
| Document source | MongoDB (optional) | Useful only to simulate semi-structured source payloads | Keep optional; avoid duplicating PostgreSQL's role |
| Orchestration | Apache Airflow | Dependencies, scheduling, retries, backfills | Databricks Workflows for cloud jobs |
| Warehouse transformations | dbt Core | Modular SQL, tests, documentation | Use only where the warehouse target is supported |
| Quality | pytest + SQL/dbt assertions | Fast feedback and testable rules | Add Great Expectations/Soda only if justified |
| Storage format | Parquet locally; Delta in lakehouse | Columnar analytics and table reliability | CSV only as an interchange/source format |
| Containers | Docker Compose | Repeatable local services | Document non-Docker fallback only if practical |
| CI | GitHub Actions | Lint and test on pull requests | Avoid claiming deployment if CI only tests |
| Frontend | Next.js + TypeScript | Recruiter-friendly demo | Static HTML is enough if time is limited |
| Hosting | Vercel for site/UI | Convenient public frontend and previews | Run ETL on local/Docker/Databricks, not as a Vercel request |
| Observability | Python structured logs + run audit table | Visible operational evidence | Add metrics/tracing when useful |
| Streaming (stretch) | Kafka/Redpanda | Demonstrates event ingestion concepts | Not required for a credible batch MVP |

**Architecture rule:** PostgreSQL is the local relational database and optional serving layer; Databricks/Delta is the lakehouse path. MongoDB is optional and only justified as a source-system simulation. Do not force all tools into one architecture.

## 11. Non-functional requirements

- **Reliability:** safe reruns, explicit failure states, no silent data loss.
- **Data quality:** rules are versioned, observable, and testable.
- **Reproducibility:** pinned dependencies, deterministic seed, documented commands.
- **Security:** secrets via environment variables/secret manager; no secrets committed.
- **Privacy:** synthetic data only; no real consumer records or production credentials.
- **Performance:** benchmark before optimizing; record dataset size and environment.
- **Maintainability:** typed/modular code where useful, clear naming, small functions, readable SQL.
- **Accessibility:** dashboard has labels, keyboard-friendly controls, readable contrast.
- **Cost:** local-first development; cloud jobs are opt-in and stopped after use.
- **Portability:** local MVP works without Databricks credentials.

## 12. Data quality and test strategy

### Unit tests
- parser behavior and schema conversions;
- deduplication logic;
- null and invalid-value handling;
- delinquency bucket boundaries;
- metric calculations and zero-denominator behavior;
- watermark and idempotency utilities.

### Integration tests
- ingest a fixture into the local environment;
- run Bronze → Silver → Gold;
- confirm row counts and reconciliation rules;
- rerun the same batch and verify no duplicate business events;
- simulate failure and verify safe retry.

### Data tests
- primary/business-key uniqueness;
- required columns not null;
- accepted values and valid ranges;
- foreign-key relationships;
- date ordering (e.g., maturity after origination);
- aggregate reconciliation between source and target.

### CI gates
1. Format/lint checks.
2. Unit tests.
3. Lightweight integration tests.
4. Build/import checks.
5. Optional container smoke test.
6. Publish test summary; block merge on critical failures.

## 13. API and demo requirements

The demo is read-only and serves precomputed synthetic aggregates. Example endpoints if a backend is implemented:
- `GET /api/health` — service status.
- `GET /api/summary` — overall synthetic portfolio metrics.
- `GET /api/quality/latest` — latest published quality summary.
- `GET /api/runs` — recent run metadata.
- `GET /api/portfolio/daily?from=YYYY-MM-DD&to=YYYY-MM-DD` — daily aggregates.

Responses must include a schema/version where appropriate and return clear errors for invalid parameters. Do not expose row-level customer or account records publicly. For the simplest deployment, generate static JSON artifacts from the pipeline and let the Vercel frontend read them.

## 14. Vercel and deployment model

**Vercel hosts the recruiter-facing UI and documentation, not the heavy data pipeline.** PySpark/Databricks workloads, Airflow workers, and long-running ETL should run in their appropriate execution environment. Vercel Functions have runtime and bundle constraints; avoid coupling a recruiter page request to a Spark job.

Recommended flow:
1. Pipeline runs locally or in Databricks.
2. Tests and quality checks pass.
3. A small, sanitized aggregate JSON artifact is published to the web app's static data directory or a suitable read-only endpoint.
4. GitHub Actions checks code and can publish the static demo artifact.
5. Vercel deploys the Next.js site from the public GitHub repository.
6. The README links to the live demo, source code, architecture, and test evidence.

Never publish credentials, raw synthetic event dumps unnecessarily, private work data, or environment files.

## 15. Security, ethics, and responsible use

- Use generated synthetic data only.
- Do not use this project to make real credit eligibility decisions.
- Avoid sensitive attributes and protected-class proxies in any optional model experiment.
- If a research model is added, label it educational, evaluate limitations and potential bias, and do not present it as production-ready.
- Store secrets outside Git; rotate immediately if one is accidentally exposed.
- Use aggregate-only public outputs and include a clear demo disclaimer.

## 16. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Scope becomes too large | Complete the local MVP before cloud/streaming extras |
| Databricks access or free-tier limits change | Keep local PySpark + Parquet path functional |
| Too many tools with shallow implementation | Require evidence and tests for each tool included |
| Public demo appears static or fabricated | Show sample data lineage, run metadata, test output, and clearly label demo artifacts |
| Runtime/cost surprises | Use small benchmark data, opt-in cloud runs, tear down resources |
| Credit-risk metrics are ambiguous | Publish a data dictionary and exact metric definitions |
| Secrets or sensitive data leak | Synthetic data only, secret scanning, `.env.example`, `.gitignore` |

## 17. Delivery plan and definition of done

### Milestone A — Working local pipeline
- Generate data and run ingestion.
- Produce Bronze/Silver/Gold outputs.
- Load Gold tables into PostgreSQL.
- Demonstrate deduplication, quarantine, and idempotent rerun.

### Milestone B — Reliable workflow
- Add Airflow and dbt.
- Add automated tests and CI.
- Record pipeline-run metrics and a failure/retry demonstration.

### Milestone C — Databricks implementation
- Run a documented equivalent path using PySpark and Delta Lake.
- Record what differs from the local implementation.
- Include screenshots or logs from an actual successful run; never use mock screenshots as evidence.

### Milestone D — Recruiter presentation
- Publish architecture diagram, data dictionary, design decisions, setup steps, benchmark results, and known limitations.
- Deploy the read-only frontend to Vercel.
- Test the public site from a clean browser session.

**Definition of done:** another developer can clone the repository, follow the setup guide, run the local pipeline, run the tests, inspect the outputs, understand the data model, and explain the design trade-offs without needing a private walkthrough.

## 18. Public repository structure

```text
creditpulse/
├── README.md
├── docs/
│   ├── PRD.md
│   ├── architecture.md
│   ├── data-dictionary.md
│   ├── decisions/
│   └── runbooks/
├── data/
│   ├── samples/              # tiny synthetic fixtures only
│   └── generated/            # gitignored
├── ingestion/
├── transformations/
│   ├── pyspark/
│   └── dbt/
├── orchestration/
│   └── airflow/
├── warehouse/
│   └── sql/
├── tests/
├── scripts/
├── infra/
│   └── docker-compose.yml
├── web/                      # Next.js recruiter demo (optional)
├── .github/workflows/
└── .env.example
```

## 19. Recruiter-facing README checklist

The first screen of the README should contain:
- one-sentence project description;
- architecture diagram;
- actual technology stack (mark planned items as planned);
- quick-start commands;
- actual test status;
- a few real benchmark results with environment and input size;
- links to PRD, data dictionary, design decisions, and demo;
- a “What I learned / trade-offs” section;
- limitations and synthetic-data disclaimer.

Do not claim “production-grade,” “real-time,” “petabyte-scale,” or “exactly once” unless you can demonstrate and substantiate the claim.

## 20. Reference documentation

Use official docs as implementation references and verify the current version before following commands:
- Databricks medallion architecture: https://docs.databricks.com/gcp/en/lakehouse/medallion
- Databricks Delta Lake architecture: https://docs.databricks.com/aws/en/lakehouse-architecture/deployment-guide/delta-lake
- Apache Airflow DAG concepts: https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html
- Vercel Functions: https://vercel.com/docs/functions
- Vercel limits: https://vercel.com/docs/limits

---

## Product decision log (initial)

1. **Local-first:** the project must remain demonstrable without cloud credentials.
2. **PostgreSQL before MongoDB:** use a relational warehouse/reference store first; add MongoDB only if a document source provides a clear use case.
3. **Batch-first before streaming:** batch ingestion is enough to demonstrate core engineering fundamentals; Kafka is a stretch goal.
4. **Vercel for presentation:** keep heavy ETL execution outside the web request lifecycle.
5. **Evidence over buzzwords:** every listed tool should correspond to a working component, test, runbook, or measured result.
