from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools.base import Tool
from mcp.server.stdio import stdio_server
import serial.tools.list_ports, subprocess, asyncio, logging, os, re, sys

# Configure logging to stderr only to keep stdout clean for JSON-RPC
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    stream=sys.stderr,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

SKETCH_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../sketches'))
FQBN_RE = re.compile(r'^[\w]+:[\w]+:[\w]+$')
# Cross-platform port regex: Windows COM ports, Linux /dev/tty*, macOS /dev/cu.*
PORT_RE = re.compile(r'^(COM\d+|/dev/(tty|cu)[\w\d.-]+)$')


def validate_sketch(sketch: str):
    sketch_path = os.path.abspath(sketch)
    # Allow outside sketch directory if explicitly enabled
    if not os.environ.get("ALLOW_OUTSIDE_SKETCH_DIR") == "yes":
        if not sketch_path.startswith(SKETCH_DIR):
            raise ValueError(f"Sketch path {sketch} is not in the allowed directory. Set ALLOW_OUTSIDE_SKETCH_DIR=yes to override.")
    if not os.path.exists(sketch_path):
        raise ValueError(f"Sketch {sketch} does not exist.")
    return sketch_path

def validate_fqbn(fqbn: str):
    if not FQBN_RE.match(fqbn):
        raise ValueError(f"Invalid FQBN: {fqbn}")
    return fqbn

def validate_port(port: str):
    if not PORT_RE.match(port):
        raise ValueError(f"Invalid port: {port}")
    return port


def list_ports() -> list[dict]:
    """Return USB/serial ports."""
    logging.info("list_ports called")
    return [
        {"device": p.device, "description": p.description, "hwid": p.hwid}
        for p in serial.tools.list_ports.comports()
    ]

async def compile(sketch: str, fqbn: str):
    """arduino-cli compile"""
    logging.info(f"compile called: {sketch}, {fqbn}")
    sketch_path = validate_sketch(sketch)
    fqbn = validate_fqbn(fqbn)
    return await _run_cli("compile", "--fqbn", fqbn, sketch_path)

async def upload(sketch: str, fqbn: str, port: str):
    """arduino-cli upload"""
    logging.info(f"upload called: {sketch}, {fqbn}, {port}")
    sketch_path = validate_sketch(sketch)
    fqbn = validate_fqbn(fqbn)
    port = validate_port(port)
    return await _run_cli("upload", "-p", port, "--fqbn", fqbn, sketch_path)

async def serial_send(port: str, baud: int, message: str, timeout: float = 2):
    """Write a line, read one response."""
    logging.info(f"serial_send called: {port}, {baud}, {message}")
    port = validate_port(port)
    import serial
    loop = asyncio.get_event_loop()
    def _io():
        with serial.Serial(port, baud, timeout=timeout) as ser:
            ser.write((message + "\n").encode())
            ser.flush()
            return ser.readline().decode(errors="replace").strip()
    return await loop.run_in_executor(None, _io)

async def _run_cli(*args):
    proc = await asyncio.create_subprocess_exec(
        "arduino-cli", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    return {"returncode": proc.returncode, "stdout": out.decode(), "stderr": err.decode()}

mcp = FastMCP(
    name="arduino-mcp-server",
    instructions="Expose arduino-cli and serial over MCP.",
    tools=[
        Tool.from_function(list_ports),
        Tool.from_function(compile),
        Tool.from_function(upload),
        Tool.from_function(serial_send)
    ]
)

def main():
    """Entry point for the console script."""
    stdio_server(mcp)

if __name__ == "__main__":
    main() 