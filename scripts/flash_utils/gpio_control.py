"""
GPIO control module for Raspberry Pi hardware control during flashing.

This module provides optional GPIO control functionality that can be used
to control external hardware (e.g., reset buttons, power switches) during
the firmware flashing process.

On systems without GPIO support, all operations are silently ignored.
"""

import time


class GPIOController:
    """GPIO controller for hardware management during flashing."""

    def __init__(self):
        self.gpio_available = False
        self.gpio = None
        self._init_gpio()

    def _init_gpio(self):
        """Initialize GPIO library if available."""
        try:
            import RPi.GPIO as GPIO

            self.gpio = GPIO
            self.gpio_available = True
            print("🔌 GPIO support detected (Raspberry Pi)")
        except ImportError:
            print("ℹ️  GPIO support not available (running on non-Raspberry Pi system)")
            self.gpio_available = False

    def setup_pin(self, pin: int, mode: str = "OUT") -> bool:
        """Setup GPIO pin for use.

        Args:
            pin: GPIO pin number (BCM numbering)
            mode: Pin mode ("OUT" or "IN")

        Returns:
            True if setup successful, False otherwise
        """
        if not self.gpio_available:
            return False

        try:
            self.gpio.setmode(self.gpio.BCM)
            if mode == "OUT":
                self.gpio.setup(pin, self.gpio.OUT)
            elif mode == "IN":
                self.gpio.setup(pin, self.gpio.IN, pull_up_down=self.gpio.PUD_UP)
            else:
                print(f"⚠️  Unknown GPIO mode: {mode}")
                return False
            return True
        except Exception as e:
            print(f"❌ GPIO setup failed for pin {pin}: {e}")
            return False

    def set_pin(self, pin: int, value: bool) -> bool:
        """Set GPIO pin state.

        Args:
            pin: GPIO pin number
            value: True for HIGH, False for LOW

        Returns:
            True if operation successful, False otherwise
        """
        if not self.gpio_available:
            return False

        try:
            self.gpio.output(pin, self.gpio.HIGH if value else self.gpio.LOW)
            return True
        except Exception as e:
            print(f"❌ GPIO set failed for pin {pin}: {e}")
            return False

    def pulse_pin(
        self, pin: int, duration: float = 0.1, active_low: bool = False
    ) -> bool:
        """Send a pulse signal to GPIO pin.

        Args:
            pin: GPIO pin number
            duration: Pulse duration in seconds
            active_low: If True, pulse is LOW-HIGH-LOW, otherwise HIGH-LOW-HIGH

        Returns:
            True if operation successful, False otherwise
        """
        if not self.gpio_available:
            return False

        try:
            # Set initial state
            initial_state = not active_low
            pulse_state = active_low

            self.set_pin(pin, initial_state)
            time.sleep(0.01)  # Short delay to ensure initial state

            # Send pulse
            self.set_pin(pin, pulse_state)
            time.sleep(duration)

            # Return to initial state
            self.set_pin(pin, initial_state)
            return True
        except Exception as e:
            print(f"❌ GPIO pulse failed for pin {pin}: {e}")
            return False

    def cleanup(self):
        """Clean up GPIO resources."""
        if self.gpio_available and self.gpio:
            try:
                self.gpio.cleanup()
            except Exception as e:
                print(f"⚠️  GPIO cleanup warning: {e}")


class FlashGPIOControl:
    """High-level GPIO control for firmware flashing operations."""

    def __init__(self, gpio_config: dict | None = None):
        """Initialize GPIO control with configuration.

        Args:
            gpio_config: Dictionary with GPIO configuration:
                - reset_pin: GPIO pin for reset control
                - boot_pin: GPIO pin for boot mode control
                - power_pin: GPIO pin for power control
                - reset_duration: Duration for reset pulse (default: 0.1s)
                - boot_duration: Duration for boot pulse (default: 0.1s)
                - reset_active_low: Whether reset is active low (default: True)
                - boot_active_low: Whether boot is active low (default: True)
        """
        self.controller = GPIOController()
        self.config = gpio_config or {}
        self._setup_pins()

    def _setup_pins(self):
        """Setup configured GPIO pins."""
        if not self.config:
            return

        for pin_name in ["reset_pin", "boot_pin", "power_pin"]:
            pin = self.config.get(pin_name)
            if pin is not None:
                if self.controller.setup_pin(pin):
                    print(f"🔌 GPIO pin {pin} setup for {pin_name}")
                else:
                    print(f"⚠️  Failed to setup GPIO pin {pin} for {pin_name}")

    def enter_flash_mode(self) -> bool:
        """Put device into flash mode using GPIO control.

        This typically involves:
        1. Assert boot pin (if configured)
        2. Reset device (if reset pin configured)
        3. Release boot pin after reset

        Returns:
            True if GPIO operations were attempted, False if no GPIO config
        """
        if not self.config:
            return False

        boot_pin = self.config.get("boot_pin")
        reset_pin = self.config.get("reset_pin")

        if not (boot_pin or reset_pin):
            return False

        print("🔌 Entering flash mode via GPIO...")

        try:
            # Step 1: Assert boot pin if configured
            if boot_pin:
                boot_active_low = self.config.get("boot_active_low", True)
                boot_state = not boot_active_low  # Assert boot
                if self.controller.set_pin(boot_pin, boot_state):
                    print(f"🔌 Boot pin {boot_pin} asserted")
                time.sleep(0.1)  # Give time for boot pin to stabilize

            # Step 2: Reset device if reset pin configured
            if reset_pin:
                reset_duration = self.config.get("reset_duration", 0.1)
                reset_active_low = self.config.get("reset_active_low", True)
                if self.controller.pulse_pin(
                    reset_pin, reset_duration, reset_active_low
                ):
                    print(f"🔌 Reset pulse sent on pin {reset_pin}")
                time.sleep(0.2)  # Give time for reset to complete

            # Step 3: Release boot pin after reset
            if boot_pin:
                boot_release_state = boot_active_low  # Release boot
                if self.controller.set_pin(boot_pin, boot_release_state):
                    print(f"🔌 Boot pin {boot_pin} released")
                time.sleep(0.1)

            print("✅ Flash mode entry sequence completed")
            return True

        except Exception as e:
            print(f"❌ Flash mode entry failed: {e}")
            return False

    def exit_flash_mode(self) -> bool:
        """Exit flash mode and return device to normal operation.

        Returns:
            True if GPIO operations were attempted, False if no GPIO config
        """
        if not self.config:
            return False

        reset_pin = self.config.get("reset_pin")

        if not reset_pin:
            return False

        print("🔌 Exiting flash mode via GPIO...")

        try:
            # Reset device to start normal operation
            reset_duration = self.config.get("reset_duration", 0.1)
            reset_active_low = self.config.get("reset_active_low", True)
            if self.controller.pulse_pin(reset_pin, reset_duration, reset_active_low):
                print(f"🔌 Normal reset pulse sent on pin {reset_pin}")
                time.sleep(0.5)  # Give time for device to start
                print("✅ Device should now be in normal operation mode")
                return True
        except Exception as e:
            print(f"❌ Flash mode exit failed: {e}")

        return False

    def power_cycle(self) -> bool:
        """Power cycle the device using GPIO control.

        Returns:
            True if power cycle was attempted, False if no power pin configured
        """
        power_pin = self.config.get("power_pin")
        if not power_pin:
            return False

        print("🔌 Power cycling device via GPIO...")

        try:
            # Turn off power
            if self.controller.set_pin(power_pin, False):
                print(f"🔌 Power OFF on pin {power_pin}")
            time.sleep(1.0)  # Wait for complete power down

            # Turn on power
            if self.controller.set_pin(power_pin, True):
                print(f"🔌 Power ON on pin {power_pin}")
            time.sleep(2.0)  # Wait for device to boot

            print("✅ Power cycle completed")
            return True

        except Exception as e:
            print(f"❌ Power cycle failed: {e}")
            return False

    def cleanup(self):
        """Clean up GPIO resources."""
        self.controller.cleanup()
