"""Unit tests for GPU / VM software-rendering auto-detection and Chromium flags."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "coconut"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import app  # noqa: E402


def _make_mock_drm(
    root: Path,
    vendors: dict[str, str],
    render_nodes: list[str],
) -> tuple[Path, Path]:
    """Create mock /dev/dri and /sys/class/drm directory trees inside *root*."""
    dri_dir = root / "dri"
    drm_sys = root / "drm_sys"
    dri_dir.mkdir(parents=True, exist_ok=True)
    drm_sys.mkdir(parents=True, exist_ok=True)

    for node in render_nodes:
        (dri_dir / node).touch()

    for card, vendor in vendors.items():
        dev_dir = drm_sys / card / "device"
        dev_dir.mkdir(parents=True, exist_ok=True)
        (dev_dir / "vendor").write_text(f"{vendor}\n", encoding="utf-8")

    return dri_dir, drm_sys


class SoftwareGpuDetectionTests(unittest.TestCase):
    def test_real_gpus_with_render_node_keep_hardware_rendering(self) -> None:
        for vendors in (
            {"card0": "0x1002"},  # AMD
            {"card0": "0x8086"},  # Intel
            {"card0": "0x10de"},  # NVIDIA
            {},  # ARM/SoC with DRM render node and no PCI vendor
        ):
            with tempfile.TemporaryDirectory() as td:
                dri_dir, drm_sys = _make_mock_drm(Path(td), vendors, ["renderD128"])
                self.assertFalse(
                    app.should_use_software_gpu([], env={}, dri_dir=dri_dir, drm_sys=drm_sys),
                    msg=f"Expected hardware rendering for vendors={vendors}",
                )

    def test_virtual_gpus_enable_software_rendering(self) -> None:
        for vendor in ("0x15ad", "0x80ee", "0x1234", "0x1b36"):
            with tempfile.TemporaryDirectory() as td:
                dri_dir, drm_sys = _make_mock_drm(Path(td), {"card0": vendor}, ["renderD128"])
                self.assertTrue(
                    app.should_use_software_gpu([], env={}, dri_dir=dri_dir, drm_sys=drm_sys),
                    msg=f"Expected software rendering for virtual vendor={vendor}",
                )

    def test_missing_render_node_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.assertTrue(
                app.should_use_software_gpu(
                    [], env={}, dri_dir=root / "no_dri", drm_sys=root / "no_sys"
                )
            )
            dri_dir, drm_sys = _make_mock_drm(root, {"card0": "0x1002"}, [])
            self.assertTrue(
                app.should_use_software_gpu([], env={}, dri_dir=dri_dir, drm_sys=drm_sys)
            )

        with tempfile.TemporaryDirectory() as td:
            dri_dir, drm_sys = _make_mock_drm(Path(td), {"card0": "0x10de"}, [])
            self.assertFalse(
                app.should_use_software_gpu([], env={}, dri_dir=dri_dir, drm_sys=drm_sys)
            )

    def test_dual_gpu_with_real_adapter_keeps_hardware_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dri_dir, drm_sys = _make_mock_drm(
                Path(td), {"card0": "0x15ad", "card1": "0x1002"}, ["renderD128"]
            )
            self.assertFalse(
                app.should_use_software_gpu([], env={}, dri_dir=dri_dir, drm_sys=drm_sys)
            )

    def test_cli_and_env_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            hw_dri, hw_sys = _make_mock_drm(root / "hw", {"card0": "0x1002"}, ["renderD128"])
            vm_dri, vm_sys = _make_mock_drm(root / "vm", {"card0": "0x15ad"}, [])

            self.assertTrue(
                app.should_use_software_gpu(
                    ["--software-gpu"],
                    env={"COCONUT_SOFTWARE_GPU": "0"},
                    dri_dir=hw_dri,
                    drm_sys=hw_sys,
                )
            )
            self.assertFalse(
                app.should_use_software_gpu(
                    ["--hardware-gpu"],
                    env={"COCONUT_SOFTWARE_GPU": "1"},
                    dri_dir=vm_dri,
                    drm_sys=vm_sys,
                )
            )
            self.assertTrue(
                app.should_use_software_gpu(
                    [], env={"COCONUT_SOFTWARE_GPU": "1"}, dri_dir=hw_dri, drm_sys=hw_sys
                )
            )
            self.assertFalse(
                app.should_use_software_gpu(
                    [], env={"COCONUT_SOFTWARE_GPU": "0"}, dri_dir=vm_dri, drm_sys=vm_sys
                )
            )

    def test_configure_gpu_env_appends_deduplicates_and_preserves_existing_flags(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            hw_dri, hw_sys = _make_mock_drm(root / "hw", {"card0": "0x1002"}, ["renderD128"])
            vm_dri, vm_sys = _make_mock_drm(root / "vm", {"card0": "0x15ad"}, [])

            hw_env: dict[str, str] = {"QTWEBENGINE_CHROMIUM_FLAGS": "--enable-features=Foo"}
            self.assertFalse(app.configure_gpu_env([], env=hw_env, dri_dir=hw_dri, drm_sys=hw_sys))
            self.assertEqual(hw_env["QTWEBENGINE_CHROMIUM_FLAGS"], "--enable-features=Foo")

            vm_env: dict[str, str] = {"QTWEBENGINE_CHROMIUM_FLAGS": "--enable-features=Bar --disable-gpu"}
            self.assertTrue(app.configure_gpu_env([], env=vm_env, dri_dir=vm_dri, drm_sys=vm_sys))
            self.assertEqual(
                vm_env["QTWEBENGINE_CHROMIUM_FLAGS"].split(),
                ["--enable-features=Bar", "--disable-gpu", "--disable-gpu-compositing"],
            )
            self.assertTrue(app.configure_gpu_env([], env=vm_env, dri_dir=vm_dri, drm_sys=vm_sys))
            self.assertEqual(
                vm_env["QTWEBENGINE_CHROMIUM_FLAGS"].split(),
                ["--enable-features=Bar", "--disable-gpu", "--disable-gpu-compositing"],
            )


if __name__ == "__main__":
    unittest.main()
