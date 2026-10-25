import json
import tempfile
import unittest
from pathlib import Path

from spyglass.config import (
    Settings,
    SettingsError,
    list_models,
    load_settings,
    save_settings,
    validate_settings,
)


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.models = self.root / "models"
        self.models.mkdir()
        (self.models / "robots.rpk").touch()
        self.settings_path = self.root / "config" / "settings.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_lists_only_installed_rpk_files(self):
        (self.models / "notes.txt").touch()
        (self.models / "folder.rpk").mkdir()
        self.assertEqual(list_models(self.models), ["robots.rpk"])

    def test_defaults_and_round_trip(self):
        self.assertEqual(load_settings(self.settings_path, self.models), Settings())
        settings = Settings(team_number=578, model="robots.rpk", confidence=0.7)
        save_settings(self.settings_path, self.models, settings)
        self.assertEqual(load_settings(self.settings_path, self.models), settings)

    def test_rejects_uninstalled_model(self):
        with self.assertRaisesRegex(SettingsError, "installed .rpk"):
            validate_settings(Settings(model="outside.rpk"), self.models)

    def test_rejects_model_path_instead_of_file_name(self):
        with self.assertRaisesRegex(SettingsError, "name of an .rpk"):
            validate_settings(Settings(model="../outside.rpk"), self.models)

    def test_loads_settings_when_selected_model_was_removed(self):
        settings = Settings(team_number=578, model="removed.rpk")
        self.settings_path.parent.mkdir()
        self.settings_path.write_text(
            json.dumps(settings.__dict__), encoding="utf-8"
        )
        self.assertEqual(load_settings(self.settings_path, self.models), settings)
        with self.assertRaises(SettingsError):
            save_settings(self.settings_path, self.models, settings)

    def test_rejects_invalid_threshold(self):
        with self.assertRaisesRegex(SettingsError, "Confidence"):
            validate_settings(Settings(confidence=1.1), self.models)

    def test_rejects_invalid_saved_json(self):
        self.settings_path.parent.mkdir()
        self.settings_path.write_text(json.dumps({"unknown": True}), encoding="utf-8")
        with self.assertRaises(SettingsError):
            load_settings(self.settings_path, self.models)


if __name__ == "__main__":
    unittest.main()
