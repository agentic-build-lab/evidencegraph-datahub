# Migration plan for EG-042

Proposed change: `drop_column` on `urn:li:dataset:(urn:li:dataPlatform:postgres,commerce.raw_orders,PROD)` / `customer_tier`.

## Risk-ranked consumers

| Risk | Score | Asset | Owner | Evidence path count |
|---|---:|---|---|---:|
| blocker | 100 | `urn:li:mlFeature:(customer_profile,customer_tier_signal)` | urn:li:corpGroup:risk-ml | 1 |
| blocker | 90 | `urn:li:dataset:(urn:li:dataPlatform:dbt,analytics.fct_customer_value,PROD)` | urn:li:corpGroup:growth-analytics | 1 |
| blocker | 90 | `urn:li:mlModelDeployment:(urn:li:dataPlatform:kubernetes,churn_api_prod,PROD)` | urn:li:corpGroup:ml-platform | 1 |
| critical | 85 | `urn:li:mlModel:(urn:li:dataPlatform:mlflow,churn_propensity_v4,PROD)` | urn:li:corpGroup:risk-ml | 1 |
| critical | 80 | `urn:li:dashboard:(looker,executive_revenue_watch)` | urn:li:corpGroup:finance-analytics | 1 |
| critical | 75 | `urn:li:dataset:(urn:li:dataPlatform:dbt,analytics.stg_orders,PROD)` | urn:li:corpGroup:analytics-engineering | 1 |
| high | 60 | `urn:li:dataJob:(urn:li:dataFlow:(airflow,daily_customer_value,prod),build_customer_value)` | urn:li:corpGroup:data-platform | 1 |

## Ordered steps

1. **Preserve the producer contract** (BLOCKING) — Introduce a compatibility projection and update transformations before the source change.
2. **Protect analytics consumers** (BLOCKING) — Migrate metrics and dashboard fields, then run semantic validation queries.
3. **Protect ML consumers** (BLOCKING) — Version the feature contract, verify parity, and gate model deployment on validation.
4. **Re-query the fresh context graph** (BLOCKING) — After applying the migration in an approved environment, re-run DataHub lineage and schema collection; close only when no unremediated consumer remains.

## Merge policy

Do not merge until every generated validation is `passed`, the DataHub context frontier is complete, and the fresh-graph closure check finds no unremediated consumer.
