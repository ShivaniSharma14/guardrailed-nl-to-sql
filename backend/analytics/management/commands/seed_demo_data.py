from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from analytics.models import Customer, Order, OrderItem, Product


class Command(BaseCommand):
    help = "Seed the database with deterministic demo analytics data."

    def add_arguments(self, parser):
        # Native Django way to add a boolean CLI flag
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear all existing demo data before seeding",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # Check if the user passed the --clear flag
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing demo data..."))
            # Delete in reverse order of foreign keys to avoid integrity errors
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            Product.objects.all().delete()
            Customer.objects.all().delete()

        # If they didn't pass --clear, safeguard against overwriting data
        elif any(
            model.objects.exists() for model in [Customer, Product, Order, OrderItem]
        ):
            self.stdout.write(
                self.style.WARNING("Demo data already exists. No data was changed.")
            )
            self.stdout.write(
                "Use `python manage.py seed_demo_data --clear` to replace it."
            )
            return

        self._seed()

    def _seed(self):
        customers = [
            Customer(name="Aarav Sharma", region="North"),
            Customer(name="Priya Mehta", region="North"),
            Customer(name="Rohan Kapoor", region="South"),
            Customer(name="Ananya Iyer", region="South"),
            Customer(name="Kabir Singh", region="East"),
            Customer(name="Meera Das", region="East"),
            Customer(name="Arjun Patel", region="West"),
            Customer(name="Ishita Shah", region="West"),
        ]
        Customer.objects.bulk_create(customers)

        products = [
            Product(
                name="Laptop Pro 14", category="Electronics", price=Decimal("75000.00")
            ),
            Product(
                name="Wireless Mouse", category="Electronics", price=Decimal("1500.00")
            ),
            Product(
                name="Mechanical Keyboard",
                category="Electronics",
                price=Decimal("4500.00"),
            ),
            Product(
                name="Office Chair", category="Furniture", price=Decimal("12000.00")
            ),
            Product(
                name="Standing Desk", category="Furniture", price=Decimal("22000.00")
            ),
            Product(name="Notebook", category="Stationery", price=Decimal("250.00")),
            Product(name="Pen Set", category="Stationery", price=Decimal("400.00")),
            Product(name="Backpack", category="Accessories", price=Decimal("2500.00")),
        ]
        Product.objects.bulk_create(products)

        # Re-fetch from DB to get the auto-generated primary keys
        customers = list(Customer.objects.all())
        products = list(Product.objects.all())

        orders_data = [
            (0, 0, "completed"),
            (0, 1, "completed"),
            (1, 2, "completed"),
            (1, 3, "cancelled"),
            (2, 5, "completed"),
            (2, 8, "pending"),
            (3, 10, "completed"),
            (3, 12, "completed"),
            (4, 15, "completed"),
            (4, 18, "cancelled"),
            (5, 20, "completed"),
            (5, 22, "completed"),
            (6, 25, "completed"),
            (6, 28, "pending"),
            (7, 30, "completed"),
            (7, 32, "completed"),
        ]

        orders = []
        for customer_index, days_offset, status in orders_data:
            orders.append(
                Order(
                    customer=customers[customer_index],
                    order_date=date(2026, 1, 1) + timedelta(days=days_offset),
                    status=status,
                )
            )
        Order.objects.bulk_create(orders)

        orders = list(Order.objects.order_by("id"))

        item_data = [
            (0, 0, 1, "75000.00"),
            (0, 1, 2, "1500.00"),
            (1, 2, 1, "4500.00"),
            (1, 5, 5, "250.00"),
            (2, 3, 1, "12000.00"),
            (2, 7, 2, "2500.00"),
            (3, 4, 1, "22000.00"),
            (4, 5, 10, "250.00"),
            (4, 6, 3, "400.00"),
            (5, 0, 1, "75000.00"),
            (5, 2, 1, "4500.00"),
            (6, 3, 2, "12000.00"),
            (6, 7, 1, "2500.00"),
            (7, 1, 3, "1500.00"),
            (8, 4, 1, "22000.00"),
            (8, 5, 8, "250.00"),
            (9, 6, 5, "400.00"),
            (10, 0, 2, "72000.00"),
            (10, 7, 1, "2500.00"),
            (11, 2, 2, "4500.00"),
            (12, 3, 1, "12000.00"),
            (12, 5, 20, "250.00"),
            (13, 4, 2, "21000.00"),
            (14, 0, 1, "73000.00"),
            (14, 1, 1, "1500.00"),
            (15, 7, 3, "2500.00"),
        ]

        items = [
            OrderItem(
                order=orders[order_index],
                product=products[product_index],
                quantity=quantity,
                unit_price=Decimal(unit_price),
            )
            for order_index, product_index, quantity, unit_price in item_data
        ]
        OrderItem.objects.bulk_create(items)

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data seeded successfully:\n"
                f"  Customers: {Customer.objects.count()}\n"
                f"  Products: {Product.objects.count()}\n"
                f"  Orders: {Order.objects.count()}\n"
                f"  Order items: {OrderItem.objects.count()}"
            )
        )
