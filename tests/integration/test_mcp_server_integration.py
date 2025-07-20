import subprocess
import json
import pytest

def run_mcp_server(request):
    proc = subprocess.Popen(['python3', 'src/mcp_server/__init__.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate(json.dumps(request) + '\n', timeout=30)
    return json.loads(stdout.strip()), stderr

def test_list_ports():
    req = {"jsonrpc": "2.0", "id": 1, "method": "list_ports", "params": {}}
    resp, _ = run_mcp_server(req)
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    assert "data" in resp["result"]
    assert isinstance(resp["result"]["data"], list)

def test_compile():
    req = {"jsonrpc": "2.0", "id": 2, "method": "compile", "params": {"sketch": "blink/blink.ino", "fqbn": "arduino:renesas_uno:unor4wifi"}}
    resp, _ = run_mcp_server(req)
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 2
    assert "data" in resp["result"]
    assert "success" in resp["result"]["data"]

def test_upload():
    # This test requires a connected Arduino. Skip if not present.
    req_ports = {"jsonrpc": "2.0", "id": 3, "method": "list_ports", "params": {}}
    resp_ports, _ = run_mcp_server(req_ports)
    ports = resp_ports["result"]["data"]
    arduino_port = None
    for p in ports:
        if "usbmodem" in p["device"]:
            arduino_port = p["device"]
            break
    if not arduino_port:
        pytest.skip("No Arduino connected for upload test.")
    req = {"jsonrpc": "2.0", "id": 4, "method": "upload", "params": {"sketch": "blink/blink.ino", "fqbn": "arduino:renesas_uno:unor4wifi", "port": arduino_port}}
    resp, _ = run_mcp_server(req)
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 4
    assert "data" in resp["result"]
    assert "success" in resp["result"]["data"]

def test_serial_send_and_read():
    # This test requires a sketch that echoes serial commands.
    req_ports = {"jsonrpc": "2.0", "id": 5, "method": "list_ports", "params": {}}
    resp_ports, _ = run_mcp_server(req_ports)
    ports = resp_ports["result"]["data"]
    arduino_port = None
    for p in ports:
        if "usbmodem" in p["device"]:
            arduino_port = p["device"]
            break
    if not arduino_port:
        pytest.skip("No Arduino connected for serial test.")
    # Send a command
    req_send = {"jsonrpc": "2.0", "id": 6, "method": "serial_send", "params": {"port": arduino_port, "baudrate": 115200, "message": "ping"}}
    resp_send, _ = run_mcp_server(req_send)
    assert resp_send["jsonrpc"] == "2.0"
    assert resp_send["id"] == 6
    assert "data" in resp_send["result"]
    # Read serial
    req_read = {"jsonrpc": "2.0", "id": 7, "method": "read_serial", "params": {"port": arduino_port, "baudrate": 115200, "timeout": 2, "lines": 1}}
    resp_read, _ = run_mcp_server(req_read)
    assert resp_read["jsonrpc"] == "2.0"
    assert resp_read["id"] == 7
    assert "data" in resp_read["result"]
    assert "lines" in resp_read["result"]["data"] 