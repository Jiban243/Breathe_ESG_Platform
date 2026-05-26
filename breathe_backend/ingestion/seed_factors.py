import os
import django
from datetime import date

# Initialize Django environment within an isolated runtime script
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'breathe_backend.settings')
django.setup()

from ingestion.models import EmissionFactor

def run_production_seeding():
    factors = [
        # SAP Fuel Factors — Scope 1
        dict(source_type='SAPFUEL', category='diesel', region='India', unit='L', factor_kgco2e=2.68, source_name='MoEFCC 2023', version='2023', valid_from=date(2023,1,1)),
        dict(source_type='SAPFUEL', category='petrol', region='India', unit='L', factor_kgco2e=2.31, source_name='MoEFCC 2023', version='2023', valid_from=date(2023,1,1)),
        dict(source_type='SAPFUEL', category='lpg', region='India', unit='KG', factor_kgco2e=2.98, source_name='MoEFCC 2023', version='2023', valid_from=date(2023,1,1)),
        dict(source_type='SAPFUEL', category='furnace_oil', region='India', unit='KG', factor_kgco2e=3.17, source_name='MoEFCC 2023', version='2023', valid_from=date(2023,1,1)),
        
        # Utility Power Factor — Scope 2
        dict(source_type='UTILITYELECTRICITY', category='grid_electricity', region='India', unit='kWh', factor_kgco2e=0.716, source_name='CEA CO2 Baseline 2023', version='2023', valid_from=date(2023,1,1)),
        
        # Corporate Business Travel — Scope 3
        dict(source_type='TRAVELCONCUR', category='flight_economy', region='India', unit='km', factor_kgco2e=0.255, source_name='DEFRA 2023', version='2023', valid_from=date(2023,1,1)),
        dict(source_type='TRAVELCONCUR', category='flight_business', region='India', unit='km', factor_kgco2e=0.765, source_name='DEFRA 2023', version='2023', valid_from=date(2023,1,1)),
        dict(source_type='TRAVELCONCUR', category='hotel_night', region='India', unit='nights', factor_kgco2e=31.0, source_name='DEFRA 2023', version='2023', valid_from=date(2023,1,1)),
        dict(source_type='TRAVELCONCUR', category='ground_transport', region='India', unit='km', factor_kgco2e=0.149, source_name='DEFRA 2023', version='2023', valid_from=date(2023,1,1)),
    ]

    for f in factors:
        EmissionFactor.objects.get_or_create(**f)
    
    print(f"\n>>> Automated Ingestion Pipe Complete: {EmissionFactor.objects.count()} factors verified.")

if __name__ == '__main__':
    run_production_seeding()