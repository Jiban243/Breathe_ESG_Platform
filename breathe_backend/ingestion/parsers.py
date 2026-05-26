import csv
import hashlib
import math
import io
from datetime import datetime, date
from .models import (
    Client, Facility, IngestionBatch,
    RawRow, EmissionRecord, EmissionFactor
)

# ─── Unit normalization ───────────────────────────────────────────────

FUEL_UNIT_TO_LITRES = {
    'L': 1.0,
    'LT': 1.0,
    'GAL': 3.78541,
    'KG': 1.0,   # for LPG/furnace oil, kept as KG — different factors apply
}

SAP_MATERIAL_TO_CATEGORY = {
    'DIESEL-001': 'diesel',
    'HSD-FUEL':   'diesel',
    'PETROL-002': 'petrol',
    'LPG-IND':    'lpg',
    'FURNACE-OIL':'furnace_oil',
}

IATA_COORDINATES = {
    'DEL': (28.5665, 77.1031),
    'BOM': (19.0896, 72.8656),
    'BLR': (13.1986, 77.7066),
    'PNQ': (18.5822, 73.9197),
    'MAA': (12.9941, 80.1709),
    'AMD': (23.0772, 72.6347),
    'HYD': (17.2403, 78.4294),
    'CCU': (22.6542, 88.4467),
    'SIN': (1.3644, 103.9915),
    'LHR': (51.4775, -0.4614),
    'DXB': (25.2528, 55.3644),
    'JFK': (40.6413, -73.7781),
    'SYD': (-33.9399, 151.1753),
}

def haversine_km(iata1, iata2):
    if iata1 not in IATA_COORDINATES or iata2 not in IATA_COORDINATES:
        return None
    lat1, lon1 = IATA_COORDINATES[iata1]
    lat2, lon2 = IATA_COORDINATES[iata2]
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def get_factor(source_type, category, region='India'):
    return EmissionFactor.objects.filter(
        source_type=source_type,
        category=category,
        region=region,
        valid_to__isnull=True
    ).first()

def flag_if_anomalous(quantity, category, threshold_multiplier=4.0):
    TYPICAL = {
        'diesel': 2800,
        'petrol': 800,
        'lpg': 500,
        'furnace_oil': 1800,
        'electricity_kwh': 150000,
        'flight_km': 8000,
        'hotel_nights': 5,
        'ground_km': 200,
    }
    typical = TYPICAL.get(category)
    if typical and quantity > typical * threshold_multiplier:
        return f"Quantity {quantity} is over {threshold_multiplier}x typical ({typical}) for {category}"
    return ''


# ─── SAP Parser ──────────────────────────────────────────────────────

def parse_sap(file_content: bytes, batch: IngestionBatch, client: Client):
    CONSUME_MOVEMENT_TYPES = {'201', '261'}
    text = file_content.decode('utf-8', errors='replace')
    reader = csv.DictReader(io.StringIO(text), delimiter=';')

    ok, failed, suspicious = 0, 0, 0

    for i, row in enumerate(reader, start=1):
        raw_data = dict(row)
        try:
            material = row.get('Material', '').strip()
            category = SAP_MATERIAL_TO_CATEGORY.get(material)
            if not category:
                RawRow.objects.create(
                    batch=batch, row_number=i, raw_data=raw_data,
                    parse_status='FAILED',
                    parse_error=f"Unknown material: {material}"
                )
                failed += 1
                continue

            movement = row.get('Bewegungsart', '').strip()
            if movement not in CONSUME_MOVEMENT_TYPES:
                RawRow.objects.create(
                    batch=batch, row_number=i, raw_data=raw_data,
                    parse_status='FAILED',
                    parse_error=f"Skipped movement type: {movement}"
                )
                failed += 1
                continue

            # Parse DD.MM.YYYY date
            date_str = row.get('Buchungsdatum', '').strip()
            try:
                posting_date = datetime.strptime(date_str, '%d.%m.%Y').date()
            except ValueError:
                posting_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            quantity_raw = float(row.get('Menge', '0').replace(',', '.'))
            unit_raw = row.get('Mengeneinheit', '').strip()

            # Normalize to litres where applicable
            if unit_raw == 'KG':
                quantity_norm = quantity_raw
                unit_norm = 'KG'
            else:
                multiplier = FUEL_UNIT_TO_LITRES.get(unit_raw, 1.0)
                quantity_norm = quantity_raw * multiplier
                unit_norm = 'L'

            factor = get_factor('SAP_FUEL', category)
            co2e_kg = quantity_norm * factor.factor_kgco2e if factor else 0.0

            flag = flag_if_anomalous(quantity_norm, category)
            status = 'SUSPICIOUS' if flag else 'OK'

            raw_row = RawRow.objects.create(
                batch=batch, row_number=i, raw_data=raw_data,
                parse_status=status, parse_error=flag
            )

            EmissionRecord.objects.create(
                client=client,
                raw_row=raw_row,
                factor=factor,
                scope='SCOPE_1',
                category=category,
                source_type='SAP_FUEL',
                period_start=posting_date,
                period_end=posting_date,
                quantity_raw=quantity_raw,
                unit_raw=unit_raw,
                quantity_norm=quantity_norm,
                unit_norm=unit_norm,
                co2e_kg=co2e_kg,
                status='PENDING_REVIEW',
                flagged_reason=flag,
            )

            if flag:
                suspicious += 1
            else:
                ok += 1

        except Exception as e:
            RawRow.objects.create(
                batch=batch, row_number=i, raw_data=raw_data,
                parse_status='FAILED', parse_error=str(e)
            )
            failed += 1

    batch.row_count = ok + suspicious
    batch.error_count = failed
    batch.status = 'DONE'
    batch.save()


# ─── Utility Parser ───────────────────────────────────────────────────

def parse_utility(file_content: bytes, batch: IngestionBatch, client: Client):
    text = file_content.decode('utf-8', errors='replace')
    reader = csv.DictReader(io.StringIO(text))

    ok, failed, suspicious = 0, 0, 0

    for i, row in enumerate(reader, start=1):
        raw_data = dict(row)
        try:
            kwh_str = row.get('Units Consumed (kWh)', '0').replace(',', '').strip()
            kwh = float(kwh_str)

            # Zero consumption — flag, don't skip
            flag = ''
            if kwh == 0:
                flag = 'Zero consumption — meter may have been offline'

            period_start = datetime.strptime(
                row['Billing Period Start'].strip(), '%d/%m/%Y'
            ).date()
            period_end = datetime.strptime(
                row['Billing Period End'].strip(), '%d/%m/%Y'
            ).date()

            if not flag:
                flag = flag_if_anomalous(kwh, 'electricity_kwh')

            factor = get_factor('UTILITY_ELECTRICITY', 'grid_electricity')
            co2e_kg = kwh * factor.factor_kgco2e if factor else 0.0

            status = 'SUSPICIOUS' if flag else 'OK'

            raw_row = RawRow.objects.create(
                batch=batch, row_number=i, raw_data=raw_data,
                parse_status=status, parse_error=flag
            )

            EmissionRecord.objects.create(
                client=client,
                raw_row=raw_row,
                factor=factor,
                scope='SCOPE_2',
                category='grid_electricity',
                source_type='UTILITY_ELECTRICITY',
                period_start=period_start,
                period_end=period_end,
                quantity_raw=kwh,
                unit_raw='kWh',
                quantity_norm=kwh,
                unit_norm='kWh',
                co2e_kg=co2e_kg,
                status='PENDING_REVIEW',
                flagged_reason=flag,
            )

            if flag:
                suspicious += 1
            else:
                ok += 1

        except Exception as e:
            RawRow.objects.create(
                batch=batch, row_number=i, raw_data=raw_data,
                parse_status='FAILED', parse_error=str(e)
            )
            failed += 1

    batch.row_count = ok + suspicious
    batch.error_count = failed
    batch.status = 'DONE'
    batch.save()


# ─── Travel Parser ────────────────────────────────────────────────────

TRAVEL_EXPENSE_MAP = {
    'Airfare': 'flight',
    'Hotel':   'hotel',
    'Taxi/Cab': 'ground',
    'Car Rental': 'ground',
}

def parse_travel(file_content: bytes, batch: IngestionBatch, client: Client):
    text = file_content.decode('utf-8', errors='replace')
    reader = csv.DictReader(io.StringIO(text))

    ok, failed, suspicious = 0, 0, 0

    for i, row in enumerate(reader, start=1):
        raw_data = dict(row)
        try:
            expense_type = row.get('Expense Type', '').strip()
            category = TRAVEL_EXPENSE_MAP.get(expense_type)
            if not category:
                RawRow.objects.create(
                    batch=batch, row_number=i, raw_data=raw_data,
                    parse_status='FAILED',
                    parse_error=f"Unhandled expense type: {expense_type}"
                )
                failed += 1
                continue

            travel_date = datetime.strptime(
                row['Travel Date'].strip(), '%Y-%m-%d'
            ).date()

            flag = ''
            co2e_kg = 0.0
            quantity_norm = 0.0
            unit_norm = ''

            if category == 'flight':
                origin = row.get('Origin Airport', '').strip()
                dest = row.get('Destination Airport', '').strip()
                distance_km = haversine_km(origin, dest)

                if distance_km is None:
                    flag = f"Unknown airport code(s): {origin} → {dest}"
                    RawRow.objects.create(
                        batch=batch, row_number=i, raw_data=raw_data,
                        parse_status='FAILED', parse_error=flag
                    )
                    failed += 1
                    continue

                cabin = row.get('Cabin Class', 'Economy').strip()
                factor_cat = 'flight_business' if cabin == 'Business' else 'flight_economy'
                factor = get_factor('TRAVEL_CONCUR', factor_cat)
                co2e_kg = distance_km * factor.factor_kgco2e if factor else 0.0
                quantity_norm = distance_km
                unit_norm = 'km'
                flag = flag_if_anomalous(distance_km, 'flight_km')

            elif category == 'hotel':
                nights_str = row.get('Hotel Nights', '0').strip()
                nights = float(nights_str) if nights_str else 0.0
                factor = get_factor('TRAVEL_CONCUR', 'hotel_night')
                co2e_kg = nights * factor.factor_kgco2e if factor else 0.0
                quantity_norm = nights
                unit_norm = 'nights'
                flag = flag_if_anomalous(nights, 'hotel_nights')

            elif category == 'ground':
                dist_str = row.get('Distance (km)', '').strip()
                if not dist_str:
                    flag = 'No distance provided — cannot compute ground transport emissions'
                    raw_row = RawRow.objects.create(
                        batch=batch, row_number=i, raw_data=raw_data,
                        parse_status='SUSPICIOUS', parse_error=flag
                    )
                    EmissionRecord.objects.create(
                        client=client, raw_row=raw_row, factor=None,
                        scope='SCOPE_3', category='ground_transport',
                        source_type='TRAVEL_CONCUR',
                        period_start=travel_date, period_end=travel_date,
                        quantity_raw=0, unit_raw='km',
                        quantity_norm=0, unit_norm='km',
                        co2e_kg=0,
                        status='PENDING_REVIEW', flagged_reason=flag,
                    )
                    suspicious += 1
                    continue

                dist_km = float(dist_str)
                factor = get_factor('TRAVEL_CONCUR', 'ground_transport')
                co2e_kg = dist_km * factor.factor_kgco2e if factor else 0.0
                quantity_norm = dist_km
                unit_norm = 'km'
                flag = flag_if_anomalous(dist_km, 'ground_km')

            amount_raw = float(row.get('Amount', '0') or 0)
            status = 'SUSPICIOUS' if flag else 'OK'

            raw_row = RawRow.objects.create(
                batch=batch, row_number=i, raw_data=raw_data,
                parse_status=status, parse_error=flag
            )

            EmissionRecord.objects.create(
                client=client,
                raw_row=raw_row,
                factor=factor if 'factor' in dir() else None,
                scope='SCOPE_3',
                category=category,
                source_type='TRAVEL_CONCUR',
                period_start=travel_date,
                period_end=travel_date,
                quantity_raw=amount_raw,
                unit_raw=row.get('Currency', 'INR').strip(),
                quantity_norm=quantity_norm,
                unit_norm=unit_norm,
                co2e_kg=co2e_kg,
                status='PENDING_REVIEW',
                flagged_reason=flag,
            )

            if flag:
                suspicious += 1
            else:
                ok += 1

        except Exception as e:
            RawRow.objects.create(
                batch=batch, row_number=i, raw_data=raw_data,
                parse_status='FAILED', parse_error=str(e)
            )
            failed += 1

    batch.row_count = ok + suspicious
    batch.error_count = failed
    batch.status = 'DONE'
    batch.save()