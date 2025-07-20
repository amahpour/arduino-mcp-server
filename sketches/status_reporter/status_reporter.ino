// Status Reporter Example for MCP Server Validation
// Periodically prints a status message over serial

unsigned long lastReport = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial) { ; }
  Serial.println("[STATUS_REPORTER] Ready");
}

void loop() {
  unsigned long now = millis();
  if (now - lastReport > 2000) {
    Serial.print("[STATUS_REPORTER] Uptime (ms): ");
    Serial.println(now);
    lastReport = now;
  }
} 