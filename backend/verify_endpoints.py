import requests, json, sys
base='http://127.0.0.1:8000/api/v1'
# test market indices
try:
    r=requests.get(f'{base}/market/indices')
    print('Market indices status', r.status_code)
    print('Response sample', r.text[:200])
except Exception as e:
    print('Market indices error', e)
# test global indices
try:
    r2=requests.get(f'{base}/global/indices')
    print('Global indices status', r2.status_code)
    print('Response sample', r2.text[:200])
except Exception as e:
    print('Global indices error', e)
