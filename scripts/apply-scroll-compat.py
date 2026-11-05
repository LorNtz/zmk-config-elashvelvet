#!/usr/bin/env python3
"""Generate corrected copies of three files from the pinned ZMK checkout.

The input listener's old conversion both discarded its quotient and missed
runtime inertia, which writes HID directly. Convert once at the shared HID API
instead, and start every host at legacy resolution until it requests otherwise.
Hashes make dependency changes fail explicitly rather than silently mispatch.
Only the build directory is written; other builds can share the west checkout.
"""

import argparse
import hashlib
from pathlib import Path


# cormoran/zmk e5c9b6915b56801193e359dd9bad4a167ce0d1b8 (main+dya).
# Each entry is (original SHA-256, patched SHA-256).
HASHES = {
    "src/hid.c": ("8ec8aef54775765ff9af7534aca59f6aa60060396f373016db2d913ebf8f52ea", "4d7ee9220bb3d338486e0ca91628d949eb5dc543e0a1454495ec966ba0f95a0b"),
    "src/pointing/input_listener.c": ("0e83fb3e6c1cba3d023237ae0495d7340e9fd5716fad900ff9f82ed7c2e8c75e", "a007c541ff15cb92b4d9c47b19b73a6cbed5de0ba5ee108ae6ba8f99c50d12a1"),
    "src/pointing/resolution_multipliers.c": ("48bd8d212c21f9f7d810a60e9dbb351aa480503250efc782ba41e437aba5a0f8", "227524c78e705ca32810f4062729c6033ddc509083c6053db5738a74ca6e3285"),
}


def patch_text(name: str, source: str) -> str:
    if name == "src/hid.c":
        source = source.replace(
            "#include <zmk/hid.h>\n",
            "#include <zmk/hid.h>\n#include <scroll_resolution.h>\n",
            1,
        )
        for operation in ("set", "update"):
            signature = f"void zmk_hid_mouse_scroll_{operation}(int16_t hwheel, int16_t wheel) {{\n"
            source = source.replace(
                signature,
                signature + "    velvet_scroll_resolution_scale(&hwheel, &wheel);\n",
                1,
            )
    elif name == "src/pointing/input_listener.c":
        start = source.index(
            "#if IS_ENABLED(CONFIG_ZMK_POINTING_SMOOTH_SCROLLING)\n"
            "static void apply_resolution_scaling"
        )
        end_marker = "#endif // IS_ENABLED(CONFIG_ZMK_POINTING_SMOOTH_SCROLLING)"
        end = source.index(end_marker, start) + len(end_marker)
        source = source[:start] + source[end:]
        source = source.replace(
            "#if IS_ENABLED(CONFIG_ZMK_POINTING_SMOOTH_SCROLLING)\n"
            "    apply_resolution_scaling(data, evt);\n"
            "#endif // IS_ENABLED(CONFIG_ZMK_POINTING_SMOOTH_SCROLLING)",
            "/* Resolution conversion is shared with runtime inertia in the HID API. */",
            1,
        )
    else:
        source = source.replace(".wheel = 15,", ".wheel = 0,", 1)
        source = source.replace(".hor_wheel = 15,", ".hor_wheel = 0,", 1)
    return source


def apply(app: Path, destination: Path) -> None:
    updates = []
    for name, (original, patched) in HASHES.items():
        path = app / name
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if digest != original:
            raise RuntimeError(
                f"Unexpected ZMK source {path}: {digest}. "
                "Review the compatibility patch before changing the pinned dependency."
            )
        output = patch_text(name, content.decode()).encode()
        if hashlib.sha256(output).hexdigest() != patched:
            raise RuntimeError(f"Scroll patch did not produce the expected source for {path}")
        updates.append((destination / name, output))
    # Validate all inputs before writing generated sources. Reconfiguration is idempotent.
    for path, output in updates:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(output)
    print(f"Velvet scroll compatibility: {len(updates)} corrected source copies generated")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zmk_app", type=Path)
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    apply(arguments.zmk_app, arguments.destination)
