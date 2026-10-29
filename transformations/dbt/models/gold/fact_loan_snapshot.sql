{% set as_of = var("as_of_date", "2024-12-31") %}

with repay as (
    select *
    from {{ ref("fact_repayment") }}
    where event_date <= '{{ as_of }}'::date
),

paid as (
    select
        loan_id,
        sum(paid_amount) as paid_to_date,
        sum(due_amount) as due_to_date,
        min(event_date) filter (where paid_amount < due_amount) as oldest_unpaid_date,
        count(*) filter (where paid_amount < due_amount) as unpaid_events
    from repay
    group by loan_id
),

scored as (
    select
        l.loan_id,
        '{{ as_of }}'::date as snapshot_date,
        l.account_id,
        a.customer_id,
        l.product_code,
        l.principal_amount,
        coalesce(p.paid_to_date, 0)::numeric(18, 2) as paid_to_date,
        greatest(l.principal_amount - coalesce(p.paid_to_date, 0), 0)::numeric(18, 2)
            as outstanding_balance_proxy,
        case
            when coalesce(p.due_to_date, 0) = 0 then null
            else coalesce(p.paid_to_date, 0) / p.due_to_date
        end as repayment_completion_rate,
        case
            when coalesce(p.unpaid_events, 0) = 0 then 0
            else ('{{ as_of }}'::date - p.oldest_unpaid_date)
        end as days_past_due
    from {{ ref("dim_loan") }} as l
    inner join {{ ref("dim_account") }} as a
        on l.account_id = a.account_id
    left join paid as p
        on l.loan_id = p.loan_id
)

select
    loan_id,
    snapshot_date,
    account_id,
    customer_id,
    product_code,
    principal_amount,
    paid_to_date,
    outstanding_balance_proxy,
    repayment_completion_rate,
    days_past_due,
    refdata.delinquency_bucket(days_past_due) as delinquency_bucket
from scored
