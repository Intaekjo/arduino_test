namespace {
constexpr unsigned long BAUD_RATE = 115200;
constexpr uint8_t PRESSURE_PIN = A0;
constexpr uint8_t RELAY_PIN = 8;
constexpr bool RELAY_ACTIVE_HIGH = true;

constexpr unsigned long SAMPLE_INTERVAL_US = 12500;
constexpr unsigned long DATA_INTERVAL_MS = 100;
constexpr unsigned long HEARTBEAT_TIMEOUT_MS = 2000;
constexpr size_t SAMPLE_COUNT = 8;
constexpr size_t LINE_BUFFER_SIZE = 64;

constexpr char FW_VERSION[] = "1.0.0";

char lineBuffer[LINE_BUFFER_SIZE];
size_t lineLength = 0;

int sampleBuffer[SAMPLE_COUNT];
long sampleTotal = 0;
size_t sampleIndex = 0;

bool streamEnabled = false;
bool relayOn = false;

unsigned long lastHeartbeatMs = 0;
unsigned long lastSampleUs = 0;
unsigned long lastDataMs = 0;
}  // namespace

void initializeSamples();
void captureSample();
void readSerialCommands();
void processCommand(const char* command);
void setRelayState(bool enabled);
void writeStatus();
void writeData(unsigned long nowMs);
void writeError(const char* code, const char* message);
float averageAdc();
float currentVoltage();
float currentPressureBar();
bool intervalElapsed(unsigned long nowValue, unsigned long lastValue, unsigned long interval);

void setup() {
  pinMode(RELAY_PIN, OUTPUT);
  setRelayState(false);

  Serial.begin(BAUD_RATE);
  initializeSamples();

  lastHeartbeatMs = millis();
  lastDataMs = millis();
  lastSampleUs = micros();
}

void loop() {
  readSerialCommands();

  const unsigned long nowUs = micros();
  if (intervalElapsed(nowUs, lastSampleUs, SAMPLE_INTERVAL_US)) {
    lastSampleUs += SAMPLE_INTERVAL_US;
    captureSample();
  }

  const unsigned long nowMs = millis();
  if (relayOn && intervalElapsed(nowMs, lastHeartbeatMs, HEARTBEAT_TIMEOUT_MS)) {
    setRelayState(false);
    writeStatus();
  }

  if (streamEnabled && intervalElapsed(nowMs, lastDataMs, DATA_INTERVAL_MS)) {
    lastDataMs += DATA_INTERVAL_MS;
    writeData(nowMs);
  }
}

void initializeSamples() {
  const int initial = analogRead(PRESSURE_PIN);
  sampleTotal = 0;
  for (size_t index = 0; index < SAMPLE_COUNT; ++index) {
    sampleBuffer[index] = initial;
    sampleTotal += initial;
  }
}

void captureSample() {
  const int raw = analogRead(PRESSURE_PIN);
  sampleTotal -= sampleBuffer[sampleIndex];
  sampleBuffer[sampleIndex] = raw;
  sampleTotal += raw;
  sampleIndex = (sampleIndex + 1) % SAMPLE_COUNT;
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    const char incoming = static_cast<char>(Serial.read());
    if (incoming == '\r') {
      continue;
    }

    if (incoming == '\n') {
      if (lineLength > 0) {
        lineBuffer[lineLength] = '\0';
        processCommand(lineBuffer);
        lineLength = 0;
      }
      continue;
    }

    if (lineLength < LINE_BUFFER_SIZE - 1) {
      lineBuffer[lineLength++] = incoming;
    } else {
      lineLength = 0;
      writeError("LINE_OVF", "Command too long");
    }
  }
}

void processCommand(const char* command) {
  if (strcmp(command, "HELLO") == 0) {
    Serial.print("READY,");
    Serial.println(FW_VERSION);
    return;
  }

  if (strcmp(command, "STATUS") == 0) {
    writeStatus();
    return;
  }

  if (strcmp(command, "HEARTBEAT") == 0) {
    lastHeartbeatMs = millis();
    return;
  }

  if (strcmp(command, "STREAM,1") == 0) {
    streamEnabled = true;
    writeStatus();
    return;
  }

  if (strcmp(command, "STREAM,0") == 0) {
    streamEnabled = false;
    writeStatus();
    return;
  }

  if (strcmp(command, "RELAY,1") == 0) {
    setRelayState(true);
    writeStatus();
    return;
  }

  if (strcmp(command, "RELAY,0") == 0) {
    setRelayState(false);
    writeStatus();
    return;
  }

  writeError("BAD_CMD", command);
}

void setRelayState(bool enabled) {
  relayOn = enabled;
  const uint8_t pinState = (enabled == RELAY_ACTIVE_HIGH) ? HIGH : LOW;
  digitalWrite(RELAY_PIN, pinState);
}

void writeStatus() {
  Serial.print("STATUS,");
  Serial.print(relayOn ? 1 : 0);
  Serial.print(',');
  Serial.print(currentPressureBar(), 3);
  Serial.print(',');
  Serial.print(currentVoltage(), 3);
  Serial.print(',');
  Serial.println(static_cast<int>(averageAdc() + 0.5f));
}

void writeData(unsigned long nowMs) {
  Serial.print("DATA,");
  Serial.print(nowMs);
  Serial.print(',');
  Serial.print(currentPressureBar(), 3);
  Serial.print(',');
  Serial.print(currentVoltage(), 3);
  Serial.print(',');
  Serial.print(static_cast<int>(averageAdc() + 0.5f));
  Serial.print(',');
  Serial.println(relayOn ? 1 : 0);
}

void writeError(const char* code, const char* message) {
  Serial.print("ERROR,");
  Serial.print(code);
  Serial.print(',');
  Serial.println(message);
}

float averageAdc() {
  return static_cast<float>(sampleTotal) / static_cast<float>(SAMPLE_COUNT);
}

float currentVoltage() {
  return averageAdc() * 5.0f / 1023.0f;
}

float currentPressureBar() {
  float pressure = (currentVoltage() / 5.0f) * 10.0f;
  if (pressure < 0.0f) {
    pressure = 0.0f;
  }
  if (pressure > 10.0f) {
    pressure = 10.0f;
  }
  return pressure;
}

bool intervalElapsed(unsigned long nowValue, unsigned long lastValue, unsigned long interval) {
  return static_cast<unsigned long>(nowValue - lastValue) >= interval;
}

