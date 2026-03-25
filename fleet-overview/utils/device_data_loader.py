import json
import pandas as pd
from datetime import datetime


# Internal/test/demo accounts to exclude from fleet reporting
EXCLUDED_CUSTOMERS = {
    'Mike Vector 8 2',
    'League IoT Dev',
    'Vector 8 Beta',
    'Joel_Vector_Hybrid',
    'APAC_Demo17',
    'PaulB5',
    'BhagyaGopalan',
    'Khidhir_stable',
    'Japan Vector 8',
    'Mike Vector 8',
    'VikasL79',
    'SanghyukDemo',
    'Alex Lowthorpe Cricket ECB',
    'icehockey_shifts',
    'VikasEUL5',
    'Amine Azzouzi Pro',
    'Laura Davies Cricket',
    'Gordon',
    'Vector 8 Beta NAM',
    'John Vector 8',
    'Josh Beta',
    'Julien_OF',
    'internal test',
}


def load_device_json(file_buffer) -> pd.DataFrame:
    """
    Load device/tag data from a JSON file and flatten into a DataFrame.

    The JSON structure is: { "generated_at": ..., "accounts": [ { customer_name, customer_id,
    region, tags: [ { serial, model, fw_version via latest_telemetry, ... } ] } ] }

    Returns a flat DataFrame with one row per device.
    Internal/test accounts in EXCLUDED_CUSTOMERS are filtered out.
    """
    if hasattr(file_buffer, 'read'):
        raw = file_buffer.read()
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8')
        data = json.loads(raw)
    else:
        with open(file_buffer, 'r') as f:
            data = json.load(f)

    rows = []
    for account in data.get('accounts', []):
        customer_name = account.get('customer_name') or ''
        customer_id = str(account.get('customer_id') or '')
        region = account.get('region', '')

        # Normalize region: US_2 -> US
        if region == 'US_2':
            region = 'US'

        for tag in account.get('tags', []):
            telemetry = tag.get('latest_telemetry') or {}

            fw_version = telemetry.get('fw_version') or ''
            last_seen = telemetry.get('updated_at') or tag.get('updated_at') or ''

            rows.append({
                'serial': str(tag.get('serial', '')),
                'customer_name': customer_name,
                'customer_id': customer_id,
                'region': region,
                'model': tag.get('model', ''),
                'generation': tag.get('generation', ''),
                'fw_version': fw_version,
                'last_seen': last_seen,
                'created_at': tag.get('created_at', ''),
            })

    df = pd.DataFrame(rows)

    # Parse datetime columns
    if 'last_seen' in df.columns:
        df['last_seen'] = pd.to_datetime(df['last_seen'], errors='coerce', utc=True)
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce', utc=True)

    # Ensure string columns
    for col in ['serial', 'customer_name', 'customer_id', 'region', 'model', 'generation', 'fw_version']:
        if col in df.columns:
            df[col] = df[col].fillna('')

    # Filter out internal/test/demo accounts
    if 'customer_name' in df.columns:
        df = df[~df['customer_name'].isin(EXCLUDED_CUSTOMERS)].reset_index(drop=True)

    return df
