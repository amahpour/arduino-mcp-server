import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
import pytest
import mcp_server
from unittest.mock import patch, MagicMock

def test_validate_path():
    assert mcp_server.validate_path('blink/blink.ino')
    assert not mcp_server.validate_path('/etc/passwd')
    assert not mcp_server.validate_path('../../foo')
    assert not mcp_server.validate_path('foo;rm -rf /')

def test_validate_fqbn():
    assert mcp_server.validate_fqbn('arduino:renesas_uno:unor4wifi')
    assert not mcp_server.validate_fqbn('bad|fqbn')

def test_validate_port():
    assert mcp_server.validate_port('/dev/cu.usbmodem1234')
    assert not mcp_server.validate_port('/etc/passwd')
    assert not mcp_server.validate_port('badport')

def test_validate_baudrate():
    assert mcp_server.validate_baudrate(115200)
    assert not mcp_server.validate_baudrate(42)
    assert not mcp_server.validate_baudrate(1000001)

@patch('mcp_server.subprocess.run')
def test_compile_sketch_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout='ok', stderr='')
    params = {'sketch': 'blink/blink.ino', 'fqbn': 'arduino:renesas_uno:unor4wifi'}
    result = mcp_server.compile_sketch(params)
    assert result['data']['success']
    assert result['data']['stdout'] == 'ok'

@patch('mcp_server.subprocess.run')
def test_upload_sketch_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout='ok', stderr='')
    params = {'sketch': 'blink/blink.ino', 'fqbn': 'arduino:renesas_uno:unor4wifi', 'port': '/dev/cu.usbmodem1234'}
    result = mcp_server.upload_sketch(params)
    assert result['data']['success']
    assert result['data']['stdout'] == 'ok' 