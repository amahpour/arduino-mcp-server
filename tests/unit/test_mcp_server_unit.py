import sys
import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from arduino_mcp_server.server import (
    validate_sketch, validate_fqbn, validate_port, 
    list_ports, compile, upload, serial_send
)

class TestValidation:
    def test_validate_sketch_valid(self):
        """Test valid sketch path validation."""
        with patch('os.path.abspath', return_value='/test/sketches/blink/blink.ino'), \
             patch('os.path.exists', return_value=True), \
             patch('os.environ.get', return_value=None), \
             patch('arduino_mcp_server.server.SKETCH_DIR', '/test/sketches'):
            result = validate_sketch('blink/blink.ino')
            assert result == '/test/sketches/blink/blink.ino'

    def test_validate_sketch_outside_dir(self):
        """Test sketch outside allowed directory."""
        with patch('os.path.abspath', return_value='/etc/passwd'), \
             patch('os.environ.get', return_value=None):
            with pytest.raises(ValueError, match="not in the allowed directory"):
                validate_sketch('/etc/passwd')

    def test_validate_sketch_allow_outside(self):
        """Test sketch outside directory when explicitly allowed."""
        with patch('os.path.abspath', return_value='/etc/passwd'), \
             patch('os.path.exists', return_value=True), \
             patch('os.environ.get', return_value='yes'):
            result = validate_sketch('/etc/passwd')
            assert result == '/etc/passwd'

    def test_validate_fqbn_valid(self):
        """Test valid FQBN validation."""
        assert validate_fqbn('arduino:avr:uno') == 'arduino:avr:uno'
        assert validate_fqbn('arduino:renesas_uno:unor4wifi') == 'arduino:renesas_uno:unor4wifi'

    def test_validate_fqbn_invalid(self):
        """Test invalid FQBN validation."""
        with pytest.raises(ValueError, match="Invalid FQBN"):
            validate_fqbn('bad|fqbn')
        with pytest.raises(ValueError, match="Invalid FQBN"):
            validate_fqbn('arduino;avr;uno')

    def test_validate_port_valid(self):
        """Test valid port validation."""
        assert validate_port('/dev/cu.usbmodem1234') == '/dev/cu.usbmodem1234'
        assert validate_port('/dev/ttyACM0') == '/dev/ttyACM0'
        assert validate_port('COM3') == 'COM3'

    def test_validate_port_invalid(self):
        """Test invalid port validation."""
        with pytest.raises(ValueError, match="Invalid port"):
            validate_port('/etc/passwd')
        with pytest.raises(ValueError, match="Invalid port"):
            validate_port('badport')

class TestListPorts:
    @patch('serial.tools.list_ports.comports')
    def test_list_ports(self, mock_comports):
        """Test list_ports function."""
        mock_port1 = MagicMock()
        mock_port1.device = '/dev/cu.usbmodem1234'
        mock_port1.description = 'Arduino Uno'
        mock_port1.hwid = 'USB VID:PID=2341:0043'
        
        mock_port2 = MagicMock()
        mock_port2.device = 'COM3'
        mock_port2.description = 'Arduino Nano'
        mock_port2.hwid = 'USB VID:PID=2341:0010'
        
        mock_comports.return_value = [mock_port1, mock_port2]
        
        result = list_ports()
        
        assert len(result) == 2
        assert result[0]['device'] == '/dev/cu.usbmodem1234'
        assert result[0]['description'] == 'Arduino Uno'
        assert result[1]['device'] == 'COM3'
        assert result[1]['description'] == 'Arduino Nano'

class TestAsyncFunctions:
    @pytest.mark.asyncio
    @patch('arduino_mcp_server.server._run_cli')
    async def test_compile_success(self, mock_run_cli):
        """Test successful compile."""
        mock_run_cli.return_value = {
            'returncode': 0,
            'stdout': 'Compilation successful',
            'stderr': ''
        }
        
        with patch('arduino_mcp_server.server.validate_sketch', return_value='/test/blink.ino'), \
             patch('arduino_mcp_server.server.validate_fqbn', return_value='arduino:avr:uno'):
            result = await compile('blink/blink.ino', 'arduino:avr:uno')
            
            assert result['returncode'] == 0
            assert result['stdout'] == 'Compilation successful'
            mock_run_cli.assert_called_once_with('compile', '--fqbn', 'arduino:avr:uno', '/test/blink.ino')

    @pytest.mark.asyncio
    @patch('arduino_mcp_server.server._run_cli')
    async def test_upload_success(self, mock_run_cli):
        """Test successful upload."""
        mock_run_cli.return_value = {
            'returncode': 0,
            'stdout': 'Upload successful',
            'stderr': ''
        }
        
        with patch('arduino_mcp_server.server.validate_sketch', return_value='/test/blink.ino'), \
             patch('arduino_mcp_server.server.validate_fqbn', return_value='arduino:avr:uno'), \
             patch('arduino_mcp_server.server.validate_port', return_value='/dev/cu.usbmodem1234'):
            result = await upload('blink/blink.ino', 'arduino:avr:uno', '/dev/cu.usbmodem1234')
            
            assert result['returncode'] == 0
            assert result['stdout'] == 'Upload successful'
            mock_run_cli.assert_called_once_with('upload', '-p', '/dev/cu.usbmodem1234', '--fqbn', 'arduino:avr:uno', '/test/blink.ino')

    @pytest.mark.asyncio
    @patch('asyncio.get_event_loop')
    async def test_serial_send_success(self, mock_get_loop):
        """Test successful serial send."""
        mock_loop = MagicMock()
        mock_get_loop.return_value = mock_loop
        mock_loop.run_in_executor.return_value = asyncio.Future()
        mock_loop.run_in_executor.return_value.set_result('Response from Arduino')
        
        with patch('arduino_mcp_server.server.validate_port', return_value='/dev/cu.usbmodem1234'):
            result = await serial_send('/dev/cu.usbmodem1234', 9600, 'Hello Arduino')
            
            assert result == 'Response from Arduino'
            mock_loop.run_in_executor.assert_called_once()

class TestCLI:
    @patch('asyncio.create_subprocess_exec')
    @pytest.mark.asyncio
    async def test_run_cli_success(self, mock_create_subprocess):
        """Test successful CLI execution."""
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b'stdout output', b'stderr output')
        mock_proc.returncode = 0
        mock_create_subprocess.return_value = mock_proc
        
        from arduino_mcp_server.server import _run_cli
        result = await _run_cli('compile', '--fqbn', 'arduino:avr:uno', 'sketch.ino')
        
        assert result['returncode'] == 0
        assert result['stdout'] == 'stdout output'
        assert result['stderr'] == 'stderr output'
        mock_create_subprocess.assert_called_once_with(
            'arduino-cli', 'compile', '--fqbn', 'arduino:avr:uno', 'sketch.ino',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        ) 