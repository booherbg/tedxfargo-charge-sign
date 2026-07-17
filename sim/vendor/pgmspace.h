// pgmspace stub for the simulator (host/wasm): PROGMEM is a no-op, exactly as
// on ESP32. Lets WLED's vendored fastled_slim.h compile unmodified.
// fastled_slim.h vendored byte-for-byte from the WLED checkout
// (wled00/src/dependencies/fastled_slim/) — re-copy on WLED upgrades.
#pragma once
#include <stdint.h>
#ifndef PROGMEM
#define PROGMEM
#endif
#ifndef pgm_read_byte
#define pgm_read_byte(addr)  (*(const uint8_t*)(addr))
#define pgm_read_word(addr)  (*(const uint16_t*)(addr))
#define pgm_read_dword(addr) (*(const uint32_t*)(addr))
#endif
