select
    event_date as report_date,
    product_code,
    count(*)::int as repayment_count,
    count(distinct loan_id)::int as loan_count,
    sum(due_amount)::numeric(18, 2) as due_amount,
    sum(paid_amount)::numeric(18, 2) as paid_amount,
    sum(paid_amount) / nullif(sum(due_amount), 0) as repayment_completion_rate,
    count(*) filter (where paid_amount < due_amount)::int as delinquent_event_count
from {{ ref("fact_repayment") }}
group by 1, 2
