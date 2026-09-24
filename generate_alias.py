import re
import json

with open("packages/types/src/index.ts.backup", "r") as f:
    old_index = f.read()

types_needed = []
for line in old_index.split('\n'):
    match = re.search(r'export (interface|type) (\w+)', line)
    if match:
        types_needed.append(match.group(2))

# Let's read the OpenAPI schema to find exact matches or closest matches
with open("backend/openapi.json", "r") as f:
    openapi = json.load(f)

schemas = openapi.get("components", {}).get("schemas", {})

with open("packages/types/src/index.ts", "w") as f:
    f.write('export * from "./zod-schemas";\n')
    f.write('import { components } from "./api";\n')
    f.write('export type { components } from "./api";\n\n')
    f.write("type Schemas = components['schemas'];\n\n")
    
    for t in set(types_needed):
        if t in schemas:
            f.write(f'export type {t} = Schemas["{t}"];\n')
        elif t + "Response" in schemas:
            f.write(f'export type {t} = Schemas["{t}Response"];\n')
        elif t == "Quote":
            f.write(f'export type {t} = Schemas["QuoteResponse"];\n')
        elif t == "HistoryResponse":
            f.write(f'export type {t} = Schemas["HistoryResponse"];\n')
        elif t == "Interval":
            f.write(f'export type Interval = "1m" | "5m" | "15m" | "1h" | "1d";\n')
        else:
            f.write(f'export type {t} = any; // TODO: Fix {t}\n')
