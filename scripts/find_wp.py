import json
import os

transcript_path = r'C:\Users\USER\.gemini\antigravity\brain\c81ead41-e8e7-4081-a371-dff4938ec20b\.system_generated\logs\transcript_full.jsonl'
with open(transcript_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'WORK PACKAGE 1.0' in line:
            data = json.loads(line)
            print(f'Found at line {i}. Type: {data.get("type")}')
            with open(r'C:\Users\USER\.gemini\antigravity\brain\c81ead41-e8e7-4081-a371-dff4938ec20b\scratch\found_wp.txt', 'w', encoding='utf-8') as out:
                out.write(data.get("content", ""))
