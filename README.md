# MCP Server (Model Context Protocol)

A robust, secure, and extensible server for controlling Arduino devices via the Model Context Protocol (MCP) using JSON-RPC 2.0 over stdin/stdout.

## Features
- JSON-RPC 2.0 protocol with request IDs and versioning
- Secure input validation for all parameters
- Unified response structure
- Logging to stderr
- Core actions: list_ports, compile, upload, serial_send, read_serial

## Installation

This project uses [Poetry](https://python-poetry.org/) for dependency management and testing.

```bash
curl -sSL https://install.python-poetry.org | python3 -
poetry install
```

## Running the MCP Server

```bash
poetry run python mcp_server.py
```

## Running Tests

- **Unit tests (no hardware required):**
  ```bash
  poetry run test-unit
  ```
- **Integration tests (requires Arduino connected):**
  ```bash
  poetry run test-integration
  ```

## Protocol
- **Transport:** Line-delimited JSON (one JSON-RPC 2.0 message per line) over stdin/stdout
- **Request:**
  ```json
  {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "compile",
    "params": {"sketch": "blink/blink.ino", "fqbn": "arduino:renesas_uno:unor4wifi"}
  }
  ```
- **Response:**
  ```json
  {
    "jsonrpc": "2.0",
    "result": {
      "version": "1.0",
      "data": {"success": true, "stdout": "...", "stderr": "..."}
    },
    "id": 1
  }
  ```

## Integrating with VSCode or Cursor

You can use the MCP server as a utility in your development workflow:

- **VSCode Tasks:**
  - Add a task in `.vscode/tasks.json` to run MCP server commands (e.g., compile, upload) via Poetry.
  - Example:
    ```json
    {
      "label": "MCP Compile",
      "type": "shell",
      "command": "echo '{\"jsonrpc\": \"2.0\", \"id\": 1, \"method\": \"compile\", \"params\": {\"sketch\": \"blink/blink.ino\", \"fqbn\": \"arduino:renesas_uno:unor4wifi\"}}' | poetry run python mcp_server.py",
      "problemMatcher": []
    }
    ```
- **Cursor Integration:**
  - Use Cursor's task runner or terminal to invoke MCP server commands as above.
  - You can also write a Cursor extension or script to send JSON-RPC requests and parse responses.

- **Agent Integration:**
  - Any agent or script can communicate with the MCP server by sending line-delimited JSON-RPC requests to its stdin and reading responses from stdout.

## Example Arduino Sketches
See the `sketches/` directory for example sketches that provide serial feedback for end-to-end validation.

## Testing
Run the tests in the `tests/unit` and `tests/integration` directories to validate all server actions. 