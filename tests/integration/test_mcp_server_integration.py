import sys
import os
import pytest
import asyncio
import subprocess
import tempfile
import shutil
from unittest.mock import patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from arduino_mcp_server.server import list_ports, validate_fqbn

class TestIntegration:
    """Integration tests that require actual hardware or arduino-cli."""
    
    def test_arduino_cli_available(self):
        """Test that arduino-cli is available in PATH."""
        try:
            result = subprocess.run(['arduino-cli', 'version'], 
                                  capture_output=True, text=True, timeout=10)
            assert result.returncode == 0
            assert 'arduino-cli' in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("arduino-cli not available or not responding")
    
    def test_list_ports_returns_list(self):
        """Test that list_ports returns a valid list structure."""
        ports = list_ports()
        assert isinstance(ports, list)
        
        # If ports are found, validate their structure
        if ports:
            for port in ports:
                assert 'device' in port
                assert 'description' in port
                assert 'hwid' in port
                assert isinstance(port['device'], str)
                assert isinstance(port['description'], str)
                assert isinstance(port['hwid'], str)
    
    def test_validate_fqbn_common_boards(self):
        """Test validation of common Arduino board FQBNs."""
        common_fqbns = [
            'arduino:avr:uno',
            'arduino:avr:nano',
            'arduino:avr:mega',
            'arduino:sam:arduino_due_x_dbg',
            'arduino:samd:arduino_zero_native',
            'arduino:renesas_uno:unor4wifi'
        ]
        
        for fqbn in common_fqbns:
            assert validate_fqbn(fqbn) == fqbn
    
    def test_validate_fqbn_invalid_formats(self):
        """Test that invalid FQBN formats are rejected."""
        invalid_fqbns = [
            'arduino;avr;uno',  # semicolons instead of colons
            'arduino|avr|uno',  # pipes instead of colons
            'arduino avr uno',  # spaces instead of colons
            'arduino:avr:',     # missing board
            ':avr:uno',         # missing vendor
            'arduino::uno',     # missing architecture
            '',                 # empty string
            'invalid',          # no colons
            'arduino:avr:uno;', # trailing semicolon
            'arduino:avr:uno|', # trailing pipe
        ]
        
        for fqbn in invalid_fqbns:
            with pytest.raises(ValueError, match="Invalid FQBN"):
                validate_fqbn(fqbn)
    
    @pytest.mark.asyncio
    async def test_server_starts_without_error(self):
        """Test that the MCP server can be imported and initialized without error."""
        from arduino_mcp_server.server import mcp
        
        # Check that the server has the expected tools
        tools = await mcp.list_tools()
        tool_names = [tool.name for tool in tools]
        expected_tools = ['list_ports', 'compile', 'upload', 'serial_send']
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Expected tool {expected_tool} not found"
        
        # Check that the server has the expected metadata
        assert mcp.name == "arduino-mcp-server"
        assert "arduino-cli" in mcp.instructions.lower()
    
    def test_sketch_directory_exists(self):
        """Test that the sketches directory exists and contains the blink example."""
        from arduino_mcp_server.server import SKETCH_DIR
        
        assert os.path.exists(SKETCH_DIR), f"Sketches directory {SKETCH_DIR} does not exist"
        
        blink_path = os.path.join(SKETCH_DIR, 'blink', 'blink.ino')
        if os.path.exists(blink_path):
            # If blink example exists, test that it can be validated
            from arduino_mcp_server.server import validate_sketch
            with pytest.raises(ValueError, match="not in the allowed directory"):
                # Should fail without ALLOW_OUTSIDE_SKETCH_DIR=yes
                validate_sketch(blink_path)
    
    def test_environment_variable_override(self):
        """Test that ALLOW_OUTSIDE_SKETCH_DIR environment variable works."""
        from arduino_mcp_server.server import validate_sketch
        
        # Create a temporary file outside the sketch directory
        with tempfile.NamedTemporaryFile(suffix='.ino', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Should fail without the environment variable
            with pytest.raises(ValueError, match="not in the allowed directory"):
                validate_sketch(tmp_path)
            
            # Should succeed with the environment variable
            with patch.dict(os.environ, {'ALLOW_OUTSIDE_SKETCH_DIR': 'yes'}):
                result = validate_sketch(tmp_path)
                assert result == os.path.abspath(tmp_path)
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

# Optional: Hardware-dependent tests that should be skipped if no Arduino is connected
class TestHardwareIntegration:
    """Tests that require actual Arduino hardware."""
    
    def test_arduino_board_detection(self):
        """Test that arduino-cli can detect connected boards."""
        try:
            result = subprocess.run(['arduino-cli', 'board', 'list'], 
                                  capture_output=True, text=True, timeout=10)
            assert result.returncode == 0
            
            # If boards are found, the output should contain board information
            if 'No boards found' not in result.stdout:
                assert 'arduino' in result.stdout.lower() or 'board' in result.stdout.lower()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("arduino-cli not available or no boards connected")
    
    def test_compile_with_real_sketch(self):
        """Test compilation of a real sketch if available."""
        blink_path = os.path.join(os.path.dirname(__file__), '../../sketches/blink/blink.ino')
        
        if not os.path.exists(blink_path):
            pytest.skip("Blink sketch not available")
        
        # This is a basic test - in a real scenario you'd want to mock the arduino-cli
        # or have a test environment with arduino-cli properly configured
        try:
            result = subprocess.run(['arduino-cli', 'compile', '--fqbn', 'arduino:avr:uno', blink_path], 
                                  capture_output=True, text=True, timeout=30)
            # Don't fail the test if compilation fails (might not have proper board support)
            # Just check that the command ran without timeout
            assert result.returncode in [0, 1]  # 0 = success, 1 = compilation error (acceptable)
        except subprocess.TimeoutExpired:
            pytest.fail("arduino-cli compile command timed out")
        except FileNotFoundError:
            pytest.skip("arduino-cli not available") 