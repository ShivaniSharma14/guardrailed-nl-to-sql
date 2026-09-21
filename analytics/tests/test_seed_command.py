from io import StringIO

from django.core.management import call_command
from django.db import connection
from django.test import TestCase

from analytics.models import Customer, Order, OrderItem, Product


class SeedDemoDataCommandTests(TestCase):
    def test_seeds_expected_row_counts(self):
        call_command("seed_demo_data", stdout=StringIO())
        self.assertEqual(Customer.objects.count(), 8)
        self.assertEqual(Product.objects.count(), 8)
        self.assertEqual(Order.objects.count(), 16)
        self.assertEqual(OrderItem.objects.count(), 26)

    def test_seeds_customers_across_multiple_regions(self):
        call_command("seed_demo_data", stdout=StringIO())
        regions = set(Customer.objects.values_list("region", flat=True))
        self.assertEqual(regions, {"North", "South", "East", "West"})

    def test_running_twice_without_clear_does_not_duplicate(self):
        call_command("seed_demo_data", stdout=StringIO())
        call_command("seed_demo_data", stdout=StringIO())
        self.assertEqual(Customer.objects.count(), 8)

    def test_clear_flag_removes_and_reseeds_cleanly(self):
        call_command("seed_demo_data", stdout=StringIO())
        call_command("seed_demo_data", "--clear", stdout=StringIO())
        self.assertEqual(Customer.objects.count(), 8)
        self.assertEqual(Order.objects.count(), 16)

    def test_order_items_reference_valid_orders_and_products(self):
        call_command("seed_demo_data", stdout=StringIO())
        for item in OrderItem.objects.select_related("order", "product"):
            self.assertIsNotNone(item.order_id)
            self.assertIsNotNone(item.product_id)

    def test_seeded_data_produces_meaningful_revenue_by_region(self):
        """
        This is the actual analytical sanity check from the very first
        roadmap message — automated instead of manually eyeballed.
        If the seed data were degenerate (e.g. all in one region, or
        all zero-revenue), this query would expose it immediately.
        """
        call_command("seed_demo_data", stdout=StringIO())

        query = """
            SELECT c.region, SUM(oi.quantity * oi.unit_price) AS total_revenue
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            JOIN customers c ON o.customer_id = c.id
            GROUP BY c.region
            ORDER BY total_revenue DESC;
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        # We should see revenue spread across more than one region —
        # a single-row result would mean the demo data is too thin to
        # be a meaningful LLM test target.
        self.assertGreater(len(rows), 1)
        for region, total_revenue in rows:
            self.assertGreater(total_revenue, 0)