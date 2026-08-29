const int ECG_PIN = 36;

void setup() {
  Serial.begin(115200);
}

void loop() {
  int ecg = analogRead(ECG_PIN);
  Serial.println(ecg);
  delay(4);
}