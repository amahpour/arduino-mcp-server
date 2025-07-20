#!/usr/bin/env python3
"""
MCP Server: JSON-RPC 2.0 over line-delimited JSON (stdin/stdout)
- Secure, extensible, and robust for agent-driven Arduino control
"""
import sys
import json
import logging
import serial.tools.list_ports
from typing import Any, Dict
import re
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', stream=sys.stderr)

# JSON-RPC 2.0 error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

SAFE_PATH_RE = re.compile(r'^[\w\-./]+$')


def validate_path(path: str) -> bool:
    """Allow only safe relative/absolute paths (no shell metacharacters, no traversal)"""
    return bool(SAFE_PATH_RE.match(path)) and not ('..' in path or path.startswith('/etc/') or path.startswith('/bin/') or path.startswith('/usr/bin/'))


def validate_fqbn(fqbn: str) -> bool:
    """Validate the fully qualified board name (FQBN)."""
    return bool(re.match(r'^[\w:-]+$', fqbn))


def validate_port(port: str) -> bool:
    """Validate the serial port path."""
    return bool(re.match(r'^/dev/cu\.[\w\d-]+$', port))


def validate_baudrate(baudrate: int) -> bool:
    """Validate the baudrate is within a safe range."""
    return isinstance(baudrate, int) and 300 <= baudrate <= 1000000


def compile_sketch(params: Dict[str, Any]) -> Dict[str, Any]:
    """Compile a sketch using arduino-cli."""
    sketch: Any = params.get('sketch')
    fqbn: Any = params.get('fqbn')
    if not sketch or not fqbn:
        raise ValueError('Missing required parameters: sketch, fqbn')
    if not validate_path(sketch):
        raise ValueError('Invalid sketch path')
    if not validate_fqbn(fqbn):
        raise ValueError('Invalid fqbn')
    logging.info(f"Compiling sketch: {sketch} for fqbn: {fqbn}")
    try:
        result = subprocess.run([
            'arduino-cli', 'compile', '--fqbn', fqbn, sketch
        ], capture_output=True, text=True, timeout=60)
        return {
            'data': {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        }
    except subprocess.TimeoutExpired:
        logging.error('Compile timed out')
        return {'data': {'success': False, 'error': 'Compile timed out'}}
    except Exception as e:
        logging.exception('Compile failed')
        return {'data': {'success': False, 'error': str(e)}}


def upload_sketch(params: Dict[str, Any]) -> Dict[str, Any]:
    """Upload a compiled sketch to the Arduino using arduino-cli."""
    sketch: Any = params.get('sketch')
    fqbn: Any = params.get('fqbn')
    port: Any = params.get('port')
    if not sketch or not fqbn or not port:
        raise ValueError('Missing required parameters: sketch, fqbn, port')
    if not validate_path(sketch):
        raise ValueError('Invalid sketch path')
    if not validate_fqbn(fqbn):
        raise ValueError('Invalid fqbn')
    if not validate_port(port):
        raise ValueError('Invalid port')
    logging.info(f"Uploading sketch: {sketch} to port: {port} for fqbn: {fqbn}")
    try:
        result = subprocess.run([
            'arduino-cli', 'upload', '-p', port, '--fqbn', fqbn, sketch
        ], capture_output=True, text=True, timeout=60)
        return {
            'data': {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        }
    except subprocess.TimeoutExpired:
        logging.error('Upload timed out')
        return {'data': {'success': False, 'error': 'Upload timed out'}}
    except Exception as e:
        logging.exception('Upload failed')
        return {'data': {'success': False, 'error': str(e)}}


def serial_send(params: Dict[str, Any]) -> Dict[str, Any]:
    """Send a message over serial and return the response."""
    port: Any = params.get('port')
    baudrate: int = params.get('baudrate', 115200)
    message: Any = params.get('message')
    timeout: int = params.get('timeout', 2)
    if not port or not message:
        raise ValueError('Missing required parameters: port, message')
    if not validate_port(port):
        raise ValueError('Invalid port')
    if not validate_baudrate(baudrate):
        raise ValueError('Invalid baudrate')
    logging.info(f"Serial send to {port} at {baudrate}: {message}")
    import serial
    try:
        with serial.Serial(port, baudrate, timeout=timeout) as ser:
            ser.write((message + '\n').encode('utf-8'))
            ser.flush()
            response = ser.readline().decode('utf-8', errors='replace').strip()
        return {'data': {'success': True, 'response': response}}
    except Exception as e:
        logging.exception('Serial send failed')
        return {'data': {'success': False, 'error': str(e)}}


def read_serial(params: Dict[str, Any]) -> Dict[str, Any]:
    """Read lines from serial port with overall timeout."""
    import time
    import serial
    port: Any = params.get('port')
    baudrate: int = params.get('baudrate', 115200)
    timeout: int = params.get('timeout', 2)
    lines: Any = params.get('lines')
    if not port:
        raise ValueError('Missing required parameter: port')
    if not validate_port(port):
        raise ValueError('Invalid port')
    if not validate_baudrate(baudrate):
        raise ValueError('Invalid baudrate')
    if lines is not None and (not isinstance(lines, int) or lines <= 0):
        raise ValueError('Invalid lines parameter')
    logging.info(f"Read serial from {port} at {baudrate}, timeout={timeout}, lines={lines}")
    result = {'success': True, 'lines': []}
    per_read_timeout = 0.1
    try:
        with serial.Serial(port, baudrate, timeout=per_read_timeout) as ser:
            start = time.time()
            count = 0
            while True:
                line = ser.readline().decode('utf-8', errors='replace').strip()
                if line:
                    result['lines'].append(line)
                    count += 1
                if lines and count >= lines:
                    break
                if (time.time() - start) > timeout:
                    break
        return {'data': result}
    except Exception as e:
        logging.exception('Read serial failed')
        return {'data': {'success': False, 'error': str(e)}}


def jsonrpc_response(result: Any, id: Any) -> Dict:
    return {"jsonrpc": "2.0", "result": {"version": "1.0", "data": result.get('data', result)}, "id": id}

def jsonrpc_error(code: int, message: str, id: Any = None, data: Any = None) -> Dict:
    err = {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": id}
    if data is not None:
        err["error"]["data"] = data
    return err


def list_ports(params: Dict[str, Any]) -> Dict[str, Any]:
    """List available serial ports."""
    ports = serial.tools.list_ports.comports()
    return {'data': [{
        'device': p.device,
        'description': p.description,
        'hwid': p.hwid
    } for p in ports]}


dispatch = {
    'list_ports': list_ports,
    'compile': compile_sketch,
    'upload': upload_sketch,
    'serial_send': serial_send,
    'read_serial': read_serial,
}

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception as e:
            logging.error(f"Parse error: {e}")
            print(json.dumps(jsonrpc_error(PARSE_ERROR, "Parse error", None)), flush=True)
            continue
        id = req.get('id')
        method = req.get('method')
        params = req.get('params', {})
        if not method or method not in dispatch:
            logging.error(f"Method not found: {method}")
            print(json.dumps(jsonrpc_error(METHOD_NOT_FOUND, f"Method not found: {method}", id)), flush=True)
            continue
        try:
            result = dispatch[method](params)
            print(json.dumps(jsonrpc_response(result, id)), flush=True)
        except ValueError as ve:
            logging.error(f"Invalid params: {ve}")
            print(json.dumps(jsonrpc_error(INVALID_PARAMS, f"Invalid params: {ve}", id)), flush=True)
        except Exception as e:
            logging.exception(f"Internal error in method {method}")
            print(json.dumps(jsonrpc_error(INTERNAL_ERROR, f"Internal error: {e}", id)), flush=True)

if __name__ == '__main__':
    main() 