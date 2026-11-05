# Flashing Velvet36

## Download the firmware

1. Open this repository's [Build ZMK firmware workflow](https://github.com/LorNtz/zmk-config-elashvelvet/actions/workflows/build.yml).
2. Choose the successful run for the `36-trackball` branch and the commit you want to install.
3. Download **firmware** from the run's **Artifacts** section and unzip it. Sign in to GitHub if the download is unavailable.

The archive contains `velvet_left.uf2`, `velvet_right.uf2`, and a separate file whose name starts with `settings_reset`. Use the two `velvet_` files for a normal update.

## Flash both halves

1. Disconnect DYA Studio, then connect one half to your computer with a USB data cable.
2. Quickly press that half's reset button twice. A USB drive, normally named **NICENANO**, appears in Finder.
3. Copy `velvet_left.uf2` to the **left** half, or `velvet_right.uf2` to the **right** half. Copy the UF2 itself, not the ZIP archive.
4. Wait for the copy to finish. The drive disappears as the controller restarts.
5. Repeat with the other half and its matching file. Turn both halves on afterward. The right half is the central: connect it to the computer for USB typing and Studio configuration.

## Adopt the compiled keymap and trackball defaults

Flashing normal firmware preserves saved Studio settings and Bluetooth pairings. Saved keymaps and trackball settings can therefore override the defaults in this repository. Perform the following once when you want to adopt newly compiled defaults; it is not necessary after every firmware update.

Before resetting, keep a DYA Studio export of any changes you have not yet copied into the repository.

1. Connect the **right** half to [DYA Studio](https://studio.dya.cormoran.works/) over USB.
2. Open **Keymap → Reset → Reset to initial state**, then confirm **Reset to default**. This installs the keymap built into the newly flashed firmware. On firmware exposing runtime combos, this action also restores those combos to their compiled defaults. It does not clear Bluetooth pairings.
3. Disconnect DYA Studio so that it releases the USB serial port.
4. Open the maintainer's [Runtime Input Processor configuration page](https://cormoran.github.io/zmk-module-runtime-input-processor/), choose **Connect USB**, and select the keyboard.
5. Choose **Reset All** on that page. This restores and saves the compiled defaults for the mouse and scroll processors only. It does not clear Bluetooth pairings. This is different from DYA Studio's general **Reset all settings** action.
6. Disconnect that page and reconnect DYA Studio. Verify the layers and trackball settings, then check cursor movement, SYMBOL scrolling, and temporary MOUSE activation on the keyboard.

Do not import the old backup afterward unless you intend to restore its old overrides. Future Studio edits remain available and can still be saved normally.

## Updating from the earlier November 5 firmware

This version includes the later DYA keymap edits and high-resolution, inertial
trackball scrolling on SYMBOL. Use the selective resets above to adopt the
new compiled settings. In particular, the saved scroll processor settings from
the earlier firmware would otherwise keep momentum disabled and retain the old
scroll scale. The mouse processor defaults have not changed.

After the processor reset, scroll scaling should read **4/15** (about **0.27x**),
and **Invert Y** should be on. These are intentional: scrolling now uses 16
subdivisions per wheel step, and direction inversion is applied before momentum
so the physical movement and its tail travel in the same direction. The effective
scroll sensitivity is still the old 1/60 wheel-step scale. Mouse scaling remains
**39/200** (displayed as **0.20x**), with the same 100/700 ms MOUSE-layer timing.

The MOUSE encoder's old `Behavior 9` override is stored separately from the
keymap and trackball processors. In DYA Studio, select **MOUSE**, click the
encoder's **Counter-clockwise** binding and choose **Trans**, then do the same
for **Clockwise**. These changes save immediately. With both directions
transparent, the encoder inherits BASE's volume controls and 5 ms tap time.
The old MOUSE tap-time display can be ignored when both directions are
transparent. This does not clear Bluetooth pairings.

High-resolution scrolling changes the USB/Bluetooth HID report descriptor.
After flashing, reconnect USB or power-cycle and reconnect Bluetooth. The
normal firmware and selective resets retain Bluetooth bonds. If a Bluetooth
host keeps using the old descriptor and scrolling behaves incorrectly, forget
and re-pair the keyboard on that affected host; do not use the full settings
reset just to refresh the host's descriptor cache.

The firmware offers finer scroll increments when the host enables the HID
resolution multiplier and normal wheel increments otherwise. The visible
smoothness depends on the host and application; high-resolution HID support on
macOS is limited. Test SYMBOL scrolling in your usual applications. Momentum
is restricted to SYMBOL and stops when that layer is released.

## Optional full settings reset

Use this fallback if selective reset is unavailable or the two halves cannot pair. It clears all saved settings, including host and split Bluetooth bonds.

1. Enter bootloader mode and flash the `settings_reset` UF2 to **both halves**, allowing each to reboot. Complete both resets before installing either normal firmware.
2. Enter bootloader mode again and flash `velvet_left.uf2` to the left half and `velvet_right.uf2` to the right half.
3. Power-cycle both halves together so they can pair with each other.
4. Forget the old Velvet36 entry in your computer's Bluetooth settings, then pair again.

The reset firmware cannot operate as a keyboard; the normal firmware must be installed afterward. Do not enable `CONFIG_ZMK_SETTINGS_RESET_ON_START` in normal firmware, because it would clear settings on every boot.

## References

- [nice!nano bootloader and UF2 flashing](https://nicekeyboards.com/docs/nice-nano/getting-started/)
- [ZMK persistent settings and Studio overrides](https://zmk.dev/docs/config/settings)
- [ZMK high-resolution scrolling configuration](https://zmk.dev/docs/config/pointing)
- [HID high-resolution scrolling limitations on macOS (Ploopy)](https://ploopyco.github.io/knob/appendices/macos/)
- [ZMK full split-reset procedure](https://zmk.dev/docs/troubleshooting/connection-issues#reset-split-keyboard-procedure)
- [Runtime input processor storage and Reset All](https://github.com/cormoran/zmk-module-runtime-input-processor#storage-modes-memory-vs-persistent)
