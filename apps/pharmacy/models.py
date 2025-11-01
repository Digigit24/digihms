from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


class ProductCategory(models.Model):
    """Product category for pharmacy items"""
    CATEGORY_TYPES = [
        ('medicine', 'Medicine'),
        ('healthcare_product', 'Healthcare Product'),
        ('medical_equipment', 'Medical Equipment')
    ]

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=50, choices=CATEGORY_TYPES)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pharmacy_product_categories'
        verbose_name_plural = 'Product Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class PharmacyProduct(models.Model):
    """Pharmacy product model"""
    product_name = models.CharField(max_length=255)
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    company = models.CharField(max_length=255, blank=True, null=True)
    batch_no = models.CharField(max_length=100, blank=True, null=True)
    
    # Pricing
    mrp = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        blank=True,
        null=True
    )
    
    # Inventory
    quantity = models.PositiveIntegerField(default=0)
    minimum_stock_level = models.PositiveIntegerField(default=10)
    
    # Dates
    expiry_date = models.DateField(blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pharmacy_products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product_name']),
            models.Index(fields=['company']),
            models.Index(fields=['batch_no']),
        ]

    def __str__(self):
        return self.product_name

    @property
    def is_in_stock(self):
        """Check if product is in stock"""
        return self.quantity > 0

    @property
    def low_stock_warning(self):
        """Check if product stock is below minimum level"""
        return self.quantity <= self.minimum_stock_level

    def save(self, *args, **kwargs):
        """Auto-set selling price if not provided"""
        if not self.selling_price:
            self.selling_price = self.mrp
        super().save(*args, **kwargs)


class Cart(models.Model):
    """Shopping cart for pharmacy products"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pharmacy_cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pharmacy_carts'

    def __str__(self):
        return f"Cart of {self.user.username}"

    @property
    def total_items(self):
        """Get total number of items in cart"""
        return self.cart_items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0

    @property
    def total_amount(self):
        """Calculate total cart amount"""
        return sum(
            item.price_at_time * item.quantity
            for item in self.cart_items.all()
        )


class CartItem(models.Model):
    """Individual items in the shopping cart"""
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    product = models.ForeignKey(
        PharmacyProduct,
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)
    price_at_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    class Meta:
        db_table = 'pharmacy_cart_items'
        unique_together = ['cart', 'product']

    def save(self, *args, **kwargs):
        """Set price at time of adding to cart"""
        if not self.price_at_time:
            self.price_at_time = self.product.selling_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.product_name} - {self.quantity}"

    @property
    def total_price(self):
        """Calculate total price for this cart item"""
        return self.quantity * self.price_at_time


class PharmacyOrder(models.Model):
    """Pharmacy order model"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded')
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='pharmacy_orders'
    )
    
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    
    shipping_address = models.TextField()
    billing_address = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pharmacy_orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.id} - {self.get_status_display()}"


class PharmacyOrderItem(models.Model):
    """Items in a pharmacy order"""
    order = models.ForeignKey(
        PharmacyOrder,
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    product = models.ForeignKey(
        PharmacyProduct,
        on_delete=models.PROTECT
    )
    quantity = models.PositiveIntegerField()
    price_at_time = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    class Meta:
        db_table = 'pharmacy_order_items'

    def __str__(self):
        return f"{self.product.product_name} - {self.quantity}"

    @property
    def total_price(self):
        """Calculate total price for this order item"""
        return self.quantity * self.price_at_time