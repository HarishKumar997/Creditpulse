select
    customer_sk,
    customer_id,
    region_code,
    customer_segment,
    status,
    effective_from,
    effective_to
from {{ ref("dim_customer") }}
where is_current
