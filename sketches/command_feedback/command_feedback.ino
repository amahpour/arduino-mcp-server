// Command Feedback Example for MCP Server Validation
// Responds to specific serial commands with unique feedback

void setup() {
  Serial.begin(115200);
  while (!Serial) { ; }
  Serial.println("[COMMAND_FEEDBACK] Ready");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    if (input.equalsIgnoreCase("ping")) {
      Serial.println("[COMMAND_FEEDBACK] pong");
    } else if (input.equalsIgnoreCase("status")) {
      Serial.println("[COMMAND_FEEDBACK] status: OK");
    } else if (input.length() > 0) {
      Serial.print("[COMMAND_FEEDBACK] unknown command: ");
      Serial.println(input);
    }
  }
} 