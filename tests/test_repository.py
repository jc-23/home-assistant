import re
import unittest

from blueprint_helpers import REPOSITORY_ROOT, load_blueprint


BLUEPRINTS = {
    "AWTRIX 3": (
        REPOSITORY_ROOT / "blueprints/automation/awtrix_weather_warning_dwd.yaml"
    ),
    "AWTRIX NG": (
        REPOSITORY_ROOT
        / "blueprints/automation/awtrix_ng_weather_warning_dwd.yaml"
    ),
}


def iter_blueprint_inputs(input_map):
    for input_value in input_map.values():
        if "input" in input_value:
            yield from iter_blueprint_inputs(input_value["input"])
        else:
            yield input_value


class RepositoryQualityTests(unittest.TestCase):
    def test_default_icons_exist_and_are_valid_8_by_8_gifs(self):
        icon_names = set()
        for blueprint_path in BLUEPRINTS.values():
            blueprint = load_blueprint(blueprint_path)
            for blueprint_input in iter_blueprint_inputs(
                blueprint["blueprint"]["input"]
            ):
                default = blueprint_input.get("default")
                if isinstance(default, str) and default.startswith("ww-"):
                    icon_names.add(default)

        self.assertTrue(icon_names)
        for icon_name in icon_names:
            icon_path = (
                REPOSITORY_ROOT / "icons/weather_warning" / f"{icon_name}.gif"
            )
            self.assertTrue(icon_path.is_file(), f"Missing icon: {icon_path}")
            with icon_path.open("rb") as icon_file:
                header = icon_file.read(10)
            self.assertIn(header[:6], (b"GIF87a", b"GIF89a"))
            width = int.from_bytes(header[6:8], "little")
            height = int.from_bytes(header[8:10], "little")
            self.assertEqual((width, height), (8, 8), icon_path.name)

    def test_blueprint_versions_match_readme_and_changelog(self):
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (REPOSITORY_ROOT / "CHANGELOG.md").read_text(
            encoding="utf-8"
        )

        for firmware, blueprint_path in BLUEPRINTS.items():
            description = load_blueprint(blueprint_path)["blueprint"]["description"]
            match = re.search(r"Blueprint version: (\d+\.\d+\.\d+)", description)
            self.assertIsNotNone(match, blueprint_path.name)
            version = match.group(1)
            self.assertIn(f"| {firmware} | {version} |", readme)
            self.assertIn(f"## {firmware} {version}", changelog)

    def test_published_project_urls_use_main_branch(self):
        paths = [REPOSITORY_ROOT / "README.md", *BLUEPRINTS.values()]

        for path in paths:
            content = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "jc-23/home-assistant/master/", content, path.name
            )


if __name__ == "__main__":
    unittest.main()
