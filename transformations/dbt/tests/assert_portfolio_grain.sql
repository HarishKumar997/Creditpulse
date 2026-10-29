-- One portfolio row per report date and product. A second row would double-count the day's payments.
select report_date, product_code
from {{ ref("agg_portfolio_daily") }}
group by 1, 2
having count(*) > 1
