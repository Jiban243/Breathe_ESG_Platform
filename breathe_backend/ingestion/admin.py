from django.contrib import admin
from .models import (
    Client, Facility, IngestionBatch,
    RawRow, EmissionFactor, EmissionRecord, AuditEvent
)

admin.site.register(Client)
admin.site.register(Facility)
admin.site.register(IngestionBatch)
admin.site.register(RawRow)
admin.site.register(EmissionFactor)
admin.site.register(EmissionRecord)
admin.site.register(AuditEvent)