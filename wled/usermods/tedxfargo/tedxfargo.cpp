// TEDxFargo CHARGE usermod — registers the geometry-aware custom effects.
// Effect logic lives in charge_fx.h (shared with the browser simulator);
// this file is the firmware-only glue: effect registration + audio access.
#include "wled.h"
#include "charge_fx.h"

// Audio glue for charge_fx.h: read the audioreactive usermod's shared data
// (same handshake stock AR effects use — FX.cpp getAudioData()); WLED's
// simulateSound() provides a synthetic signal when no mic data is flowing.
static um_data_t* charge_um() {
  um_data_t *um;
  if (!UsermodManager::getUMData(&um, USERMOD_ID_AUDIOREACTIVE))
    um = simulateSound(SEGMENT.soundSim);
  return um;
}

uint8_t charge_audio() {
  float v = *(float*)charge_um()->u_data[0];   // volumeSmth, 0..255-ish
  if (v < 0.0f) v = 0.0f;
  if (v > 255.0f) v = 255.0f;
  return (uint8_t)v;
}

uint8_t charge_audio_peak() {
  return *(uint8_t*)charge_um()->u_data[3];    // samplePeak
}

class TedxFargoUsermod : public Usermod {
 public:
  void setup() override {
    for (uint8_t e = 0; e < CHARGE_FX_COUNT; e++) {
      uint8_t id = strip.addEffect(255, CHARGE_FX_LIST[e].fn, CHARGE_FX_LIST[e].meta);
      if (id == 255) DEBUG_PRINTLN(F("[tedxfargo] addEffect failed (list full)"));
    }
  }
  void loop() override {}
};

static TedxFargoUsermod tedxfargo;
REGISTER_USERMOD(tedxfargo);
