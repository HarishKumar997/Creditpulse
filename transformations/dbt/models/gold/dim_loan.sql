select
    loan_id,
    account_id,
    product_code,
    principal_amount,
    annual_rate,
    origination_date,
    maturity_date,
    loan_status
from {{ source("staging", "loan") }}
