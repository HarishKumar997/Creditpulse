select
    r.repayment_id,
    r.loan_id,
    l.account_id,
    a.customer_id,
    l.product_code,
    r.event_timestamp,
    r.event_timestamp::date as event_date,
    r.due_amount,
    r.paid_amount,
    r.payment_status,
    replace(replace(r.source_updated_at, 'T', ' '), 'Z', '+00')::timestamptz as source_updated_at,
    r.batch_id
from {{ source("staging", "repayment") }} as r
inner join {{ source("staging", "loan") }} as l
    on r.loan_id = l.loan_id
inner join {{ source("staging", "account") }} as a
    on l.account_id = a.account_id
