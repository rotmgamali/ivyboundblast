import sys
import json
import logging
import ast

sys.path.append("/Users/mac/Desktop/Ivybound")
from sheets_integration import GoogleSheetsClient

logging.basicConfig(level=logging.INFO)
client = GoogleSheetsClient("Ivy Bound - Scraped Leads")
client.setup_sheets()

worksheet = client.input_sheet
records = worksheet.get_all_records()
headers = worksheet.row_values(1)

if 'custom_data' not in headers:
    print("custom_data column not found in headers.")
    sys.exit(0)

col_index = headers.index('custom_data') + 1

# Convert col_index to A-Z letter (works up to ZZ)
if col_index <= 26:
    col_letter = chr(ord('A') + col_index - 1)
else:
    col_letter = chr(ord('A') + (col_index-1)//26 - 1) + chr(ord('A') + (col_index-1)%26)

batch_updates = []

for idx, record in enumerate(records):
    custom_data_str = record.get('custom_data', '')
    if isinstance(custom_data_str, str) and custom_data_str.startswith("{") and "'" in custom_data_str:
        try:
            # Safely parse python string representation of dict
            parsed_dict = ast.literal_eval(custom_data_str)
            # Dump to strict JSON
            strict_json = json.dumps(parsed_dict)
            batch_updates.append({
                'range': f'{col_letter}{idx+2}',
                'values': [[strict_json]]
            })
        except Exception as e:
            print(f"Failed to parse row {idx+2}: {e}")

if batch_updates:
    worksheet.batch_update(batch_updates)
    print(f"Fixed {len(batch_updates)} rows of malformed custom_data.")
else:
    print("No rows needed fixing.")
