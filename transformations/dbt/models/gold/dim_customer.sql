with ordered as (
    select
        customer_id,
        region_code,
        customer_segment,
        status,
        replace(replace(source_updated_at, 'T', ' '), 'Z', '+00')::timestamptz as effective_from,
        lead(replace(replace(source_updated_at, 'T', ' '), 'Z', '+00')::timestamptz) over (
            partition by customer_id
            order by source_updated_at
        ) as next_effective_from
    from {{ source("staging", "customer_version") }}
)

select
    md5(customer_id || '|' || effective_from::text) as customer_sk,
    customer_id,
    region_code,
    customer_segment,
    status,
    effective_from,
    coalesce(next_effective_from, '9999-12-31'::timestamptz) as effective_to,
    next_effective_from is null as is_current
from ordered
