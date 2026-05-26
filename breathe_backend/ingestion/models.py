import uuid
from django.db import models


class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    timezone = models.CharField(max_length=64, default='Asia/Kolkata')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Facility(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='facilities')
    name = models.CharField(max_length=255)
    plant_code = models.CharField(max_length=64, blank=True)
    country = models.CharField(max_length=64, default='India')
    region = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return f"{self.name} ({self.plant_code})"

    class Meta:
        verbose_name_plural = 'Facilities'


class IngestionBatch(models.Model):
    SOURCE_SAP = 'SAP_FUEL'
    SOURCE_UTILITY = 'UTILITY_ELECTRICITY'
    SOURCE_TRAVEL = 'TRAVEL_CONCUR'
    SOURCE_CHOICES = [
        (SOURCE_SAP, 'SAP Fuel & Procurement'),
        (SOURCE_UTILITY, 'Utility Electricity'),
        (SOURCE_TRAVEL, 'Corporate Travel'),
    ]

    STATUS_PENDING = 'PENDING'
    STATUS_PROCESSING = 'PROCESSING'
    STATUS_DONE = 'DONE'
    STATUS_FAILED = 'FAILED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_DONE, 'Done'),
        (STATUS_FAILED, 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='batches')
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True)
    source_type = models.CharField(max_length=32, choices=SOURCE_CHOICES)
    file_name = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    ingested_at = models.DateTimeField(auto_now_add=True)
    ingested_by = models.CharField(max_length=255, default='analyst')
    row_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.source_type} — {self.file_name} ({self.status})"


class RawRow(models.Model):
    STATUS_OK = 'OK'
    STATUS_FAILED = 'FAILED'
    STATUS_SUSPICIOUS = 'SUSPICIOUS'
    STATUS_CHOICES = [
        (STATUS_OK, 'OK'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_SUSPICIOUS, 'Suspicious'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='rows')
    row_number = models.IntegerField()
    raw_data = models.JSONField()
    parse_status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_OK)
    parse_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Row {self.row_number} — {self.parse_status}"


class EmissionFactor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_type = models.CharField(max_length=32)
    category = models.CharField(max_length=64)
    region = models.CharField(max_length=64, default='India')
    unit = models.CharField(max_length=32)
    factor_kgco2e = models.FloatField()
    source_name = models.CharField(max_length=255)
    version = models.CharField(max_length=32)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.category} — {self.factor_kgco2e} kgCO2e/{self.unit}"


class EmissionRecord(models.Model):
    SCOPE_1 = 'SCOPE_1'
    SCOPE_2 = 'SCOPE_2'
    SCOPE_3 = 'SCOPE_3'
    SCOPE_CHOICES = [
        (SCOPE_1, 'Scope 1 — Direct'),
        (SCOPE_2, 'Scope 2 — Electricity'),
        (SCOPE_3, 'Scope 3 — Value Chain'),
    ]

    STATUS_PENDING = 'PENDING_REVIEW'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Review'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='records')
    raw_row = models.OneToOneField(RawRow, on_delete=models.SET_NULL, null=True, blank=True)
    factor = models.ForeignKey(EmissionFactor, on_delete=models.SET_NULL, null=True, blank=True)

    scope = models.CharField(max_length=16, choices=SCOPE_CHOICES)
    category = models.CharField(max_length=64)
    source_type = models.CharField(max_length=32)

    period_start = models.DateField()
    period_end = models.DateField()

    quantity_raw = models.FloatField()
    unit_raw = models.CharField(max_length=32)
    quantity_norm = models.FloatField()
    unit_norm = models.CharField(max_length=32)
    co2e_kg = models.FloatField()

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    flagged_reason = models.TextField(blank=True)
    approved_by = models.CharField(max_length=255, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    is_edited = models.BooleanField(default=False)
    edit_history = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.scope} — {self.category} — {self.co2e_kg:.2f} kgCO2e"


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(EmissionRecord, on_delete=models.CASCADE, related_name='audit_events')
    actor = models.CharField(max_length=255)
    action = models.CharField(max_length=64)
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} by {self.actor} at {self.created_at}"