select
    account_id,
    customer_id,
    account_type,
    opened_at::date as opened_at,
    nullif(closed_at, '')::date as closed_at,
    status
from {{ source("staging", "account") }}
