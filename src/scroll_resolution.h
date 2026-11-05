#pragma once

#include <stdint.h>

/* Internal scroll values use 16 subdivisions per conventional wheel step. */
struct velvet_scroll_axis_state {
    int16_t remainder;
    uint8_t multiplier;
};

static inline int16_t velvet_scroll_scale(struct velvet_scroll_axis_state *state,
                                         int16_t value, uint8_t logical_resolution) {
    /* The HID descriptor maps logical 0..15 to physical multipliers 1..16. */
    uint8_t multiplier = logical_resolution <= 15 ? logical_resolution + 1 : 1;
    if (state->multiplier != multiplier) {
        state->remainder = 0;
        state->multiplier = multiplier;
    }
    /* HID report clears must never emit a stored fractional movement. */
    if (value == 0) {
        return 0;
    }
    int32_t total = (int32_t)value * multiplier + state->remainder;
    int32_t scaled = total / 16;
    state->remainder = (int16_t)(total - scaled * 16);
    return (int16_t)scaled;
}

void velvet_scroll_resolution_scale(int16_t *hwheel, int16_t *wheel);
