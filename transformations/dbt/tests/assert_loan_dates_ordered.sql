select loan_id
from {{ ref("dim_loan") }}
where maturity_date < origination_date
