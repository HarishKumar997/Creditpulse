with days as (
    select generate_series('2022-01-01'::date, '2026-12-31'::date, interval '1 day')::date as date_day
)

select
    date_day,
    extract(year from date_day)::int as calendar_year,
    extract(quarter from date_day)::int as calendar_quarter,
    extract(month from date_day)::int as calendar_month,
    extract(day from date_day)::int as calendar_day,
    to_char(date_day, 'YYYY-MM') as year_month,
    extract(isodow from date_day)::int as iso_day_of_week
from days
