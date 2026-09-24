import json
openapi = json.load(open('backend/openapi.json'))
print(openapi['paths']['/api/v1/predictions/{symbol}']['get']['responses']['200']['content']['application/json']['schema'])
