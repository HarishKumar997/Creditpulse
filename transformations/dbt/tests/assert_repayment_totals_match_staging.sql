with gold as (
    select
        coalesce(sum(due_amount), 0) as due_amount,
        coalesce(sum(paid_amount), 0) as paid_amount,
        count(*) as row_count
    from {{ ref("fact_repayment") }}
),

src as (
    select
        coalesce(sum(due_amount), 0) as due_amount,
        coalesce(sum(paid_amount), 0) as paid_amount,
        count(*) as row_count
    from {{ source("staging", "repayment") }}
)

select *
from gold as g
cross join src as s
where g.due_amount is distinct from s.due_amount
    or g.paid_amount is distinct from s.paid_amount
    or g.row_count is distinct from s.row_count
