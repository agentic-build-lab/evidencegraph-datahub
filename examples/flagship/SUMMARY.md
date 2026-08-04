# EvidenceGraph run EG-6385813884D5

- Change: `EG-042`
- Downstream assets: **7**
- Evidence claims: **8**
- Generated artifacts: **9**
- Validations: **14 passed / 0 failed**
- Write-back executable: **False**

## Highest-risk consumers

- `urn:li:mlFeature:(customer_profile,customer_tier_signal)` — blocker (100)
- `urn:li:dataset:(urn:li:dataPlatform:dbt,analytics.fct_customer_value,PROD)` — blocker (90)
- `urn:li:mlModelDeployment:(urn:li:dataPlatform:kubernetes,churn_api_prod,PROD)` — blocker (90)
- `urn:li:mlModel:(urn:li:dataPlatform:mlflow,churn_propensity_v4,PROD)` — critical (85)
- `urn:li:dashboard:(looker,executive_revenue_watch)` — critical (80)

## Safety decision

- Live write-back was not requested; this run is read-only.
- EVIDENCEGRAPH_ENABLE_WRITES is not true.
- Required DataHub MCP mutation tools were not discovered.
