"""Sample metadata source. Database discovery and scheduled checks are future work.

A future importer should merge discovered names/types into the catalog while
preserving curated definitions, contacts, checks and lineage. This protocol is
the discovery boundary; it does not imply a working database connector.
"""
from typing import Protocol


class MetadataSource(Protocol):
    def discover(self) -> list[dict]: ...


class SampleSource:
    def discover(self):
        def contact(team, email, name):
            return {"team": team, "email": email + "@example.invalid", "name": name}

        revenue = contact("Revenue Operations", "revenue", "Alex Morgan")
        finance = contact("Finance", "finance", "Jordan Lee")
        analytics = contact("Analytics Engineering", "analytics", "Sam Rivera")
        marketing = contact("Growth Marketing", "growth", "Taylor Chen")

        def column(name, dtype, definition, sources=None, transformation="Direct source value"):
            return {"name": name, "data_type": dtype, "definition": definition,
                    "transformation": transformation, "sources": sources or []}

        def source(table, column):
            return {"table": table, "column": column}

        def asset(id, name, schema, domain, description, owner, columns, consumers, checks=None):
            return {"id": id, "name": name, "schema_name": schema, "domain": domain,
                    "description": description, "owner": owner["team"], "contacts": [owner],
                    "columns": columns, "consumers": consumers, "checks": checks or []}

        return [
            asset("orders", "orders", "commerce", "Commerce",
                  "One row per confirmed customer order. The source of truth for order value before refunds. Amounts are stored in the transaction currency; revenue reporting uses the modeled net amount.",
                  revenue, [
                      column("order_id", "BIGINT", "Unique identifier assigned when an order is confirmed."),
                      column("customer_id", "BIGINT", "Customer responsible for the order."),
                      column("gross_amount", "DECIMAL(18,2)", "Total confirmed order value, including discounts and excluding tax."),
                      column("refund_amount", "DECIMAL(18,2)", "Total refunded value for this order; zero when no refund has been issued."),
                  ], [revenue], [
                      {"name": "Order identifier is unique", "column": "order_id", "rule": "COUNT(*) = COUNT(DISTINCT order_id)", "status": "passed", "observed": "0 duplicate identifiers", "checked_at": "2026-11-18T09:00:00Z"},
                      {"name": "Order value is nonnegative", "column": "gross_amount", "rule": "gross_amount >= 0", "status": "passed", "observed": "All sample rows passed", "checked_at": "2026-11-18T09:00:00Z"},
                      {"name": "Refund does not exceed order value", "column": "refund_amount", "rule": "refund_amount <= gross_amount", "status": "warning", "observed": "3 sample rows need review", "checked_at": "2026-11-18T09:00:00Z"},
                  ]),
            asset("customers", "customers", "commerce", "Customer",
                  "Customer profile and acquisition channel. Used to understand customer cohorts without copying personal contact details into reporting models.", analytics, [
                      column("customer_id", "BIGINT", "Unique customer identifier."),
                      column("acquisition_channel", "VARCHAR", "First attributed acquisition channel."),
                  ], [marketing]),
            asset("net_orders", "net_orders", "analytics", "Finance",
                  "Confirmed orders after refunds, enriched with the customer acquisition channel. Supplies the finance and growth reporting models.", analytics, [
                      column("order_id", "BIGINT", "Original confirmed order identifier.", [source("orders", "order_id")]),
                      column("net_amount", "DECIMAL(18,2)", "Order value after refunds, excluding tax.", [source("orders", "gross_amount"), source("orders", "refund_amount")], "orders.gross_amount - orders.refund_amount"),
                      column("channel", "VARCHAR", "Acquisition channel attributed to this order's customer.", [source("customers", "acquisition_channel"), source("orders", "customer_id"), source("customers", "customer_id")], "Join orders.customer_id = customers.customer_id; select customers.acquisition_channel"),
                  ], [finance, marketing]),
            asset("daily_revenue", "daily_revenue", "reporting", "Finance",
                  "Daily net revenue rollup for the finance close and revenue dashboard. A change to the net amount definition affects finance reporting and revenue operations.", finance, [
                      column("revenue", "DECIMAL(20,2)", "Sum of net order values within each reporting day.", [source("net_orders", "net_amount")], "SUM(net_orders.net_amount) GROUP BY order_date"),
                  ], [finance, revenue]),
            asset("channel_performance", "channel_performance", "reporting", "Marketing",
                  "Net order value by acquisition channel. Used by growth teams to compare campaign performance and allocate spend.", marketing, [
                      column("channel", "VARCHAR", "Acquisition channel for the reporting group.", [source("net_orders", "channel")]),
                      column("net_sales", "DECIMAL(20,2)", "Net order value attributed to this acquisition channel.", [source("net_orders", "net_amount"), source("net_orders", "channel")], "SUM(net_orders.net_amount) GROUP BY net_orders.channel"),
                  ], [marketing]),
        ]
