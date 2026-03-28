import subprocess, json, sys
proc = subprocess.Popen([sys.executable, 'database_server.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
for msg in [
    {'jsonrpc': '2.0', 'id': 0, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1.0.0'}}},
    {'jsonrpc': '2.0', 'method': 'notifications/initialized', 'params': {}},
    {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}
]:
    proc.stdin.write((json.dumps(msg) + '\n').encode('utf-8'))
    proc.stdin.flush()
proc.stdin.close()
out, _ = proc.communicate(timeout=10)
for line in out.decode('utf-8', errors='replace').strip().split('\n'):
    try:
        r = json.loads(line)
        if 'result' in r and 'tools' in r['result']:
            tools = [t['name'] for t in r['result']['tools']]
            print(f'Tools: {len(tools)}')
            print(tools)
    except:
        pass
