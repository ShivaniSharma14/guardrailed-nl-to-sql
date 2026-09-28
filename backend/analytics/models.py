from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=255)
    region = models.CharField(max_length=100, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "customers"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "products"

    def __str__(self):
        return self.name


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    order_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    class Meta:
        db_table = "orders"

    def __str__(self):
        return f"Order {self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    class Meta:
        db_table = "order_items"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=0),
                name="order_item_unit_price_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
