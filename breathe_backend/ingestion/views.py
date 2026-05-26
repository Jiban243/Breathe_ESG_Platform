import hashlib
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import (
    Client, Facility, IngestionBatch,
    RawRow, EmissionRecord, AuditEvent, EmissionFactor
)
from .parsers import parse_sap, parse_utility, parse_travel, file_hash


# ─── Upload View ─────────────────────────────────────────────────────

class UploadView(APIView):
    def post(self, request):
        source_type = request.data.get('source_type')
        file = request.FILES.get('file')
        client_slug = request.data.get('client_slug', 'acme-manufacturing')

        if not file or not source_type:
            return Response(
                {'error': 'file and source_type are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        VALID_SOURCES = ['SAP_FUEL', 'UTILITY_ELECTRICITY', 'TRAVEL_CONCUR']
        if source_type not in VALID_SOURCES:
            return Response(
                {'error': f'source_type must be one of {VALID_SOURCES}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        client, _ = Client.objects.get_or_create(
            slug=client_slug,
            defaults={'name': 'Acme Manufacturing Pvt Ltd'}
        )

        content = file.read()
        fhash = file_hash(content)

        # Duplicate upload detection
        if IngestionBatch.objects.filter(file_hash=fhash, client=client).exists():
            return Response(
                {'error': 'This file has already been uploaded'},
                status=status.HTTP_409_CONFLICT
            )

        batch = IngestionBatch.objects.create(
            client=client,
            source_type=source_type,
            file_name=file.name,
            file_hash=fhash,
            status='PROCESSING',
            ingested_by=request.data.get('uploaded_by', 'analyst'),
        )

        try:
            if source_type == 'SAP_FUEL':
                parse_sap(content, batch, client)
            elif source_type == 'UTILITY_ELECTRICITY':
                parse_utility(content, batch, client)
            elif source_type == 'TRAVEL_CONCUR':
                parse_travel(content, batch, client)
        except Exception as e:
            batch.status = 'FAILED'
            batch.save()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'batch_id': str(batch.id),
            'status': batch.status,
            'row_count': batch.row_count,
            'error_count': batch.error_count,
        }, status=status.HTTP_201_CREATED)


# ─── Dashboard View ───────────────────────────────────────────────────

class DashboardView(APIView):
    def get(self, request):
        client_slug = request.query_params.get('client_slug', 'acme-manufacturing')
        try:
            client = Client.objects.get(slug=client_slug)
        except Client.DoesNotExist:
            return Response({'error': 'Client not found'}, status=404)

        records = EmissionRecord.objects.filter(client=client).select_related(
            'raw_row', 'raw_row__batch', 'factor'
        ).order_by('-created_at')

        status_filter = request.query_params.get('status')
        scope_filter = request.query_params.get('scope')
        source_filter = request.query_params.get('source_type')

        if status_filter:
            records = records.filter(status=status_filter)
        if scope_filter:
            records = records.filter(scope=scope_filter)
        if source_filter:
            records = records.filter(source_type=source_filter)

        data = []
        for r in records:
            data.append({
                'id': str(r.id),
                'scope': r.scope,
                'category': r.category,
                'source_type': r.source_type,
                'period_start': r.period_start,
                'period_end': r.period_end,
                'quantity_raw': r.quantity_raw,
                'unit_raw': r.unit_raw,
                'quantity_norm': r.quantity_norm,
                'unit_norm': r.unit_norm,
                'co2e_kg': round(r.co2e_kg, 3),
                'status': r.status,
                'flagged_reason': r.flagged_reason,
                'is_edited': r.is_edited,
                'batch_id': str(r.raw_row.batch.id) if r.raw_row else None,
                'file_name': r.raw_row.batch.file_name if r.raw_row else None,
                'row_number': r.raw_row.row_number if r.raw_row else None,
                'raw_data': r.raw_row.raw_data if r.raw_row else None,
            })

        summary = {
            'total': records.count(),
            'pending': records.filter(status='PENDING_REVIEW').count(),
            'approved': records.filter(status='APPROVED').count(),
            'rejected': records.filter(status='REJECTED').count(),
            'flagged': records.exclude(flagged_reason='').count(),
            'total_co2e_kg': sum(r.co2e_kg for r in records),
        }

        return Response({'summary': summary, 'records': data})


# ─── Approve / Reject View ────────────────────────────────────────────

class ReviewView(APIView):
    def post(self, request, record_id):
        try:
            record = EmissionRecord.objects.get(id=record_id)
        except EmissionRecord.DoesNotExist:
            return Response({'error': 'Record not found'}, status=404)

        action = request.data.get('action')  # 'approve' or 'reject'
        actor = request.data.get('actor', 'analyst')

        if action not in ['approve', 'reject']:
            return Response({'error': 'action must be approve or reject'}, status=400)

        before = {'status': record.status}

        if action == 'approve':
            record.status = 'APPROVED'
            record.approved_by = actor
            record.approved_at = timezone.now()
        else:
            record.status = 'REJECTED'

        record.save()

        AuditEvent.objects.create(
            record=record,
            actor=actor,
            action=action.upper(),
            before_state=before,
            after_state={'status': record.status},
        )

        return Response({'id': str(record.id), 'status': record.status})


# ─── Edit View ────────────────────────────────────────────────────────

class EditView(APIView):
    def post(self, request, record_id):
        try:
            record = EmissionRecord.objects.get(id=record_id)
        except EmissionRecord.DoesNotExist:
            return Response({'error': 'Record not found'}, status=404)

        actor = request.data.get('actor', 'analyst')
        new_quantity = request.data.get('quantity_norm')
        new_co2e = request.data.get('co2e_kg')

        before = {
            'quantity_norm': record.quantity_norm,
            'co2e_kg': record.co2e_kg,
        }

        history = record.edit_history or []
        history.append({
            'edited_at': timezone.now().isoformat(),
            'edited_by': actor,
            'before': before,
        })

        if new_quantity is not None:
            record.quantity_norm = float(new_quantity)
        if new_co2e is not None:
            record.co2e_kg = float(new_co2e)

        record.is_edited = True
        record.edit_history = history
        record.save()

        AuditEvent.objects.create(
            record=record,
            actor=actor,
            action='EDIT',
            before_state=before,
            after_state={'quantity_norm': record.quantity_norm, 'co2e_kg': record.co2e_kg},
        )

        return Response({'id': str(record.id), 'co2e_kg': record.co2e_kg})


# ─── Batches View ─────────────────────────────────────────────────────

class BatchListView(APIView):
    def get(self, request):
        client_slug = request.query_params.get('client_slug', 'acme-manufacturing')
        try:
            client = Client.objects.get(slug=client_slug)
        except Client.DoesNotExist:
            return Response({'error': 'Client not found'}, status=404)

        batches = IngestionBatch.objects.filter(client=client).order_by('-ingested_at')
        data = [{
            'id': str(b.id),
            'source_type': b.source_type,
            'file_name': b.file_name,
            'status': b.status,
            'row_count': b.row_count,
            'error_count': b.error_count,
            'ingested_at': b.ingested_at,
            'ingested_by': b.ingested_by,
        } for b in batches]

        return Response(data)