view: executive_revenue_watch {
  sql_table_name: analytics.fct_customer_value ;;

  dimension: customer_tier {
    type: string
    sql: ${TABLE}.customer_tier ;;
  }

  measure: revenue_usd {
    type: sum
    sql: ${TABLE}.lifetime_value_usd ;;
  }
}

