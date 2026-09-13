---
title: What the DJI Mic Mini transmitter button sends, and how to bind it to a macOS hotkey for hands-free dictation
authors:
  - name: Darrin T. Schultz
    orcid: 0000-0003-1190-1122
date: 2026-09-13
license: CC-BY-4.0
node: schultz-evogenome
type: pipeline-note
keywords: [dictation, HID, Karabiner-Elements, DJI Mic Mini, Handy, Claude Code, macOS]
---

# What the DJI Mic Mini transmitter button sends

Measured on a DJI Mic Mini with the receiver plugged into a Mac. The
receiver enumerates as USB HID device `Wireless Mic Rx`, vendor 11427
(0x2CA3), product 16401 (0x4011). The DJI Mic Mini 2 reports the same ids.

- The transmitter's button sends HID consumer-control usage 0xE9
  (`volume_increment`) on report id 6. It is not a keyboard key.
- The receiver's own button sends no HID report at all. There is nothing to
  bind there.
- The receiver's descriptor permits eight consumer usages (0xE9, 0xEA, 0xE2,
  0xCD, 0xB5, 0xB6, 0xB1, 0xB7); only 0xE9 is ever emitted. In
  Karabiner-Elements, `pause` and `stop` must be given as the integers 177
  and 183, not as names.

# Binding it

Karabiner-Elements turns the usage into a keystroke with one complex
modification scoped by `device_if` to vendor 11427 / product 16401, so the
volume keys of other keyboards are untouched. The target key should be F13:
it exists in the keyboard protocol but on no Mac keyboard, so nothing
collides with it, and a dictation app can be switched later without touching
Karabiner.

Do not use an `fn` chord. macOS honours `fn` only from Apple keyboards, and
a keystroke synthesised by Karabiner's virtual keyboard is not one; `fn+space`
falls through as a plain space.

# Handy (local dictation)

Handy (github.com/cjpais/Handy, MIT, runs offline) needs three settings that
fail silently when wrong: `keyboard_implementation` must be `tauri` (the
macOS default `handy_keys` never receives keys from Karabiner's virtual
keyboard); the shortcut must be bound to plain `transcribe`, since Handy
refuses to register `transcribe_with_post_process` while post-processing is
off; and Handy must be restarted after any shortcut is recorded in its UI.
Handy's `tauri` backend logs nothing at registration and only logs the hotkey
when it fires, so an empty log means "not pressed yet", not "broken".

The tool that measures the button and writes the rule and the Handy
settings is github.com/conchoecia/dji-mic-button (MIT).
