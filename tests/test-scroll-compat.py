#!/usr/bin/env python3
"""Host checks for scroll math, endpoint isolation, and the pinned source patch.

Run: python3 tests/test-scroll-compat.py /path/to/pinned/zmk/app
The supplied upstream checkout is copied to a temporary directory, never edited.
"""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]

STUBS = {
    "zephyr/kernel.h": """
#pragma once
struct k_spinlock { int unused; };
typedef int k_spinlock_key_t;
static inline k_spinlock_key_t k_spin_lock(struct k_spinlock *lock) { (void)lock; return 0; }
static inline void k_spin_unlock(struct k_spinlock *lock, k_spinlock_key_t key) {
    (void)lock; (void)key;
}
""",
    "zmk/endpoints.h": """
#pragma once
#define ZMK_ENDPOINT_COUNT 3
struct zmk_endpoint_instance { int index; };
struct zmk_endpoint_instance zmk_endpoint_get_selected(void);
int zmk_endpoint_instance_to_index(struct zmk_endpoint_instance endpoint);
""",
    "zmk/pointing/resolution_multipliers.h": """
#pragma once
#include <stdint.h>
#include <zmk/endpoints.h>
struct zmk_pointing_resolution_multipliers { uint8_t wheel, hor_wheel; };
struct zmk_pointing_resolution_multipliers
zmk_pointing_resolution_multipliers_get_profile(struct zmk_endpoint_instance endpoint);
""",
}

HARNESS = r"""
#include <assert.h>
#include <limits.h>
#include <stdint.h>
#include <zmk/endpoints.h>
#include <zmk/pointing/resolution_multipliers.h>
#include "scroll_resolution.h"
static int selected;
static struct zmk_pointing_resolution_multipliers resolutions[3];
struct zmk_endpoint_instance zmk_endpoint_get_selected(void) {
    return (struct zmk_endpoint_instance){selected};
}
int zmk_endpoint_instance_to_index(struct zmk_endpoint_instance endpoint) { return endpoint.index; }
struct zmk_pointing_resolution_multipliers
zmk_pointing_resolution_multipliers_get_profile(struct zmk_endpoint_instance endpoint) {
    assert(endpoint.index >= 0 && endpoint.index < 3);
    return resolutions[endpoint.index];
}
static int emit(int16_t value) {
    int16_t horizontal = 0, vertical = value;
    velvet_scroll_resolution_scale(&horizontal, &vertical);
    assert(horizontal == 0);
    return vertical;
}
int main(void) {
    /* Every HID multiplier, both directions, and long-run distance conservation. */
    for (int resolution = 0; resolution < 16; resolution++) {
        struct velvet_scroll_axis_state state = {0};
        int32_t total = 0;
        for (int i = 0; i < 16000; i++) {
            total += velvet_scroll_scale(&state, 1, resolution);
            assert(velvet_scroll_scale(&state, 0, resolution) == 0);
        }
        assert(total == 1000 * (resolution + 1));
        for (int i = 0; i < 16000; i++) total += velvet_scroll_scale(&state, -1, resolution);
        assert(total == 0 && state.remainder == 0);
        assert(velvet_scroll_scale(&state, INT16_MIN, resolution) == INT16_MIN * (resolution + 1) / 16);
        assert(velvet_scroll_scale(&state, INT16_MAX, resolution) == INT16_MAX * (resolution + 1) / 16);
    }
    struct velvet_scroll_axis_state state = {0};
    assert(velvet_scroll_scale(&state, 15, 0) == 0);
    assert(velvet_scroll_scale(&state, -15, 0) == 0); /* Reverse cancels fractional motion. */
    assert(state.remainder == 0);
    assert(velvet_scroll_scale(&state, 15, 0) == 0);
    assert(velvet_scroll_scale(&state, 1, 7) == 0); /* Resolution change drops old fraction. */
    assert(velvet_scroll_scale(&state, 1, 7) == 1);
    assert(velvet_scroll_scale(&state, 16, 255) == 1); /* Malformed resolution falls back safely. */

    /* Actual production adapter: independent USB/BLE state and independent axes. */
    selected = 0;
    assert(emit(15) == 0);
    assert(emit(0) == 0);
    selected = 1;
    assert(emit(1) == 0);
    selected = 0;
    assert(emit(1) == 1);
    selected = 1;
    assert(emit(15) == 1);
    selected = 2;
    resolutions[2].wheel = 15;
    assert(emit(16) == 16);
    int16_t x = 15, y = 0;
    velvet_scroll_resolution_scale(&x, &y);
    assert(x == 0 && y == 0);
    x = 1; y = 1;
    velvet_scroll_resolution_scale(&x, &y);
    assert(x == 1 && y == 1);
    selected = 99;
    assert(emit(16) == 0); /* Bounds check precedes profile lookup. */
    return 0;
}
"""


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="velvet-scroll-test-") as directory:
        temp = Path(directory)
        for name, content in STUBS.items():
            path = temp / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        (temp / "test.c").write_text(HARNESS)
        binary = temp / "test"
        subprocess.run([
            "cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-fsanitize=undefined",
            "-I", str(temp), "-I", str(ROOT / "src"), str(temp / "test.c"),
            str(ROOT / "src/scroll_resolution.c"), "-o", str(binary),
        ], check=True)
        subprocess.run([str(binary)], check=True)
        if len(sys.argv) > 1:
            upstream = Path(sys.argv[1])
            app = temp / "app"
            spec = importlib.util.spec_from_file_location("patch", ROOT / "scripts/apply-scroll-compat.py")
            patch = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(patch)
            for name in patch.HASHES:
                dest = app / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(upstream / name, dest)
            original_hid = (app / "src/hid.c").read_text()
            output = temp / "generated"
            patch.apply(app, output)
            patch.apply(app, output)  # Reconfiguration must be idempotent.
            assert (app / "src/hid.c").read_text() == original_hid
            hid = (output / "src/hid.c").read_text()
            assert hid.count("velvet_scroll_resolution_scale(&hwheel, &wheel);") == 2
            for operation in ("set", "update"):
                start = original_hid.index(f"void zmk_hid_mouse_movement_{operation}(")
                end = original_hid.index("\n}", start) + 2
                assert original_hid[start:end] in hid
            assert "apply_resolution_scaling" not in (output / "src/pointing/input_listener.c").read_text()
            resolution = (output / "src/pointing/resolution_multipliers.c").read_text()
            assert ".wheel = 0," in resolution and ".hor_wheel = 0," in resolution
            # Model Zephyr's app target living in a different CMake directory,
            # with original ZMK sources added after this module is configured.
            project = temp / "cmake-project"
            (project / "kernel").mkdir(parents=True)
            (project / "kernel/CMakeLists.txt").write_text("add_library(app STATIC)\n")
            original_sources = "\n".join(f'  "{app / name}"' for name in patch.HASHES)
            (project / "CMakeLists.txt").write_text(f"""
cmake_minimum_required(VERSION 3.20)
project(scroll_source_selection C)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(APPLICATION_SOURCE_DIR "{app}")
add_subdirectory(kernel)
add_subdirectory("{ROOT}" velvet)
target_sources(app PRIVATE
{original_sources}
)
""")
            for label, smooth, central in (("central", "ON", "ON"),
                                            ("legacy", "OFF", "ON"),
                                            ("peripheral", "ON", "OFF")):
                build = temp / label
                subprocess.run([
                    "cmake", "-S", str(project), "-B", str(build),
                    f"-DCONFIG_ZMK_POINTING_SMOOTH_SCROLLING={smooth}",
                    "-DCONFIG_ZMK_SPLIT=ON", f"-DCONFIG_ZMK_SPLIT_ROLE_CENTRAL={central}",
                ], check=True, stdout=subprocess.DEVNULL)
                sources = [item["file"] for item in json.loads((build / "compile_commands.json").read_text())]
                if label == "central":
                    assert len(sources) == 4, sources
                    assert str(ROOT / "src/scroll_resolution.c") in sources
                    assert all(str(app / name) not in sources for name in patch.HASHES)
                else:
                    assert set(sources) == {str(app / name) for name in patch.HASHES}, sources
            (app / "src/hid.c").write_text(original_hid + "\n/* Unexpected dependency change. */\n")
            try:
                patch.apply(app, output)
                raise AssertionError("Changed upstream source was silently accepted")
            except RuntimeError:
                pass
    print("Scroll compatibility checks passed")


if __name__ == "__main__":
    main()
