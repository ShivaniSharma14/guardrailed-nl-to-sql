from decimal import Decimal

from django.db import IntegrityError
from django.db.utils import DataError
from django.test import TestCase

from analytics.models import Customer, Order, OrderItem, Product


class CustomerModelTests(TestCase):
    def test_str_returns_name(self):
        customer = Customer.objects.create(name="Test Customer", region="North")
        self.assertEqual(str(customer), "Test Customer")

    def test_customer_can_have_multiple_orders(self):
        customer = Customer.objects.create(name="Test Customer", region="North")
        Order.objects.create(customer=customer, order_date="2026-01-01")
        Order.objects.create(customer=customer, order_date="2026-01-02")
        self.assertEqual(customer.orders.count(), 2)


class ProductModelTests(TestCase):
    def test_str_returns_name(self):
        product = Product.objects.create(
            name="Test Product", category="Electronics", price=Decimal("100.00")
        )
        self.assertEqual(str(product), "Test Product")


class OrderModelTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="Test Customer", region="North")

    def test_default_status_is_pending(self):
        order = Order.objects.create(customer=self.customer, order_date="2026-01-01")
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_str_includes_pk(self):
        order = Order.objects.create(customer=self.customer, order_date="2026-01-01")
        self.assertEqual(str(order), f"Order {order.pk}")

    def test_deleting_customer_cascades_to_orders(self):
        order = Order.objects.create(customer=self.customer, order_date="2026-01-01")
        order_id = order.id
        self.customer.delete()
        self.assertFalse(Order.objects.filter(id=order_id).exists())


class OrderItemModelTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="Test Customer", region="North")
        self.order = Order.objects.create(customer=self.customer, order_date="2026-01-01")
        self.product = Product.objects.create(
            name="Test Product", category="Electronics", price=Decimal("100.00")
        )

    def test_str_includes_quantity_and_product_name(self):
        item = OrderItem.objects.create(
            order=self.order, product=self.product, quantity=3, unit_price=Decimal("100.00")
        )
        self.assertEqual(str(item), "3x Test Product")

    def test_negative_unit_price_violates_check_constraint(self):
        with self.assertRaises(IntegrityError):
            OrderItem.objects.create(
                order=self.order,
                product=self.product,
                quantity=1,
                unit_price=Decimal("-10.00"),
            )

    def test_deleting_order_cascades_to_items(self):
        item = OrderItem.objects.create(
            order=self.order, product=self.product, quantity=1, unit_price=Decimal("100.00")
        )
        item_id = item.id
        self.order.delete()
        self.assertFalse(OrderItem.objects.filter(id=item_id).exists())

    def test_line_total_can_be_computed_from_quantity_and_unit_price(self):
        item = OrderItem.objects.create(
            order=self.order, product=self.product, quantity=3, unit_price=Decimal("100.00")
        )
        self.assertEqual(item.quantity * item.unit_price, Decimal("300.00"))