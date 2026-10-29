create schema if not exists staging;
create schema if not exists ops;
create schema if not exists refdata;
create schema if not exists gold;

create or replace function refdata.delinquency_bucket(days integer)
returns text
language sql
immutable
as $$
select case
    when days is null or days <= 0 then 'current'
    when days <= 30 then 'dpd_1_30'
    when days <= 60 then 'dpd_31_60'
    when days <= 90 then 'dpd_61_90'
    else 'dpd_90_plus'
end
$$;

create table if not exists staging.customer_version (
    customer_id text not null,
    created_at text,
    region_code text,
    customer_segment text,
    status text,
    source_updated_at text not null,
    batch_id text not null,
    primary key (customer_id, source_updated_at)
);

create table if not exists staging.account (
    account_id text primary key,
    customer_id text not null,
    account_type text,
    opened_at text,
    closed_at text,
    status text,
    source_updated_at text not null,
    batch_id text not null
);

create table if not exists staging.loan (
    loan_id text primary key,
    account_id text not null references staging.account (account_id),
    product_code text,
    principal_amount numeric(18, 2),
    annual_rate numeric(8, 2),
    origination_date date,
    maturity_date date,
    loan_status text,
    source_updated_at text not null,
    batch_id text not null
);

create table if not exists staging.repayment (
    repayment_id text primary key,
    loan_id text not null references staging.loan (loan_id),
    event_timestamp timestamptz,
    due_amount numeric(18, 2),
    paid_amount numeric(18, 2),
    payment_status text,
    source_updated_at text not null,
    batch_id text not null
);

create table if not exists staging.quarantine (
    source_name text not null,
    business_key text not null,
    reject_reason text not null,
    batch_id text not null,
    payload jsonb not null,
    primary key (source_name, business_key, batch_id)
);

create table if not exists ops.pipeline_run (
    run_id text primary key,
    batch_id text not null,
    status text not null,
    started_at timestamptz not null,
    finished_at timestamptz,
    rows_read integer not null default 0,
    rows_accepted integer not null default 0,
    rows_rejected integer not null default 0,
    rows_duplicate integer not null default 0,
    error_summary text,
    step text,
    timings jsonb
);

create table if not exists ops.source_watermark (
    source_name text primary key,
    last_source_updated_at text,
    last_success_run_id text,
    updated_at timestamptz not null default now()
);

create table if not exists ops.committed_batch (
    batch_id text primary key,
    run_id text not null,
    committed_at timestamptz not null default now()
);
