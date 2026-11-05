#include <zephyr/kernel.h>
#include <zmk/endpoints.h>
#include <zmk/pointing/resolution_multipliers.h>

#include "scroll_resolution.h"

struct scroll_profile_state {
    struct velvet_scroll_axis_state horizontal;
    struct velvet_scroll_axis_state vertical;
};

static struct scroll_profile_state profiles[ZMK_ENDPOINT_COUNT];
static struct k_spinlock profile_lock;

/* Both physical input and runtime inertia reach the shared HID set/update API.
 * Keep fractional movement separate for USB and every Bluetooth profile. */
void velvet_scroll_resolution_scale(int16_t *hwheel, int16_t *wheel) {
    struct zmk_endpoint_instance endpoint = zmk_endpoint_get_selected();
    int index = zmk_endpoint_instance_to_index(endpoint);
    if (index < 0 || index >= ZMK_ENDPOINT_COUNT) {
        *hwheel = 0;
        *wheel = 0;
        return;
    }
    struct zmk_pointing_resolution_multipliers resolution =
        zmk_pointing_resolution_multipliers_get_profile(endpoint);
    k_spinlock_key_t key = k_spin_lock(&profile_lock);
    *hwheel = velvet_scroll_scale(&profiles[index].horizontal, *hwheel, resolution.hor_wheel);
    *wheel = velvet_scroll_scale(&profiles[index].vertical, *wheel, resolution.wheel);
    k_spin_unlock(&profile_lock, key);
}
