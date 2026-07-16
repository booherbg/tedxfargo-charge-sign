// TEDxFargo CHARGE usermod — registers the geometry-aware custom effects.
// Effect logic lives in charge_fx.h (shared with the browser simulator);
// this file is the firmware-only glue.
#include "wled.h"
#include "charge_fx.h"

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
