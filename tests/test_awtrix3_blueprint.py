import copy
import json
import unittest

from blueprint_helpers import (
    REPOSITORY_ROOT,
    load_blueprint,
    load_fixture,
    state_trigger,
    template_environment,
)


BLUEPRINT_PATH = (
    REPOSITORY_ROOT / "blueprints/automation/awtrix_weather_warning_dwd.yaml"
)


class Awtrix3BlueprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blueprint = load_blueprint(BLUEPRINT_PATH)
        cls.environment = template_environment()
        cls.sample = load_fixture("dwd_warning_attributes.yaml")

    def render_variable(self, name, **context):
        source = self.blueprint["variables"][name]
        return self.environment.from_string(source).render(**context).strip()

    def render_boolean(self, name, **context):
        return self.render_variable(name, **context).lower() == "true"

    def payload_context(self, attributes=None, preliminary_attributes=None, **overrides):
        attributes = self.sample if attributes is None else attributes
        preliminary_attributes = preliminary_attributes or {"warning_count": 0}
        entity_attributes = {
            "sensor.dwd_warning": attributes,
            "sensor.dwd_preliminary": preliminary_attributes,
        }
        context = {
            "state_attr": lambda entity_id, attribute: entity_attributes.get(
                entity_id, {}
            ).get(attribute),
            "weather_warning_vars": ["sensor.dwd_warning"],
            "weather_preliminary_warning_vars": [],
            "show_region_name": False,
            "warning_level_to_show": 1,
            "message_repeat": 2,
            "icons_behavior": "Move with text",
            "full_day_names": False,
            "show_details": False,
            "icon_frost": "ww-frost",
            "icon_thunderstorm": "ww-thunderstorm",
            "icon_pouring": "ww-pouring",
            "icon_snow": "ww-snow",
            "icon_blackice": "ww-blackice",
            "icon_wind": "ww-wind",
            "icon_fog": "ww-fog",
            "icon_thaw": "ww-thaw",
            "icon_radition": "ww-radiation",
            "icon_warning": "ww-generic",
        }
        context.update(overrides)
        return context

    def test_schema_keeps_awtrix_3_compatibility(self):
        metadata = self.blueprint["blueprint"]
        inputs = metadata["input"]
        device_filter = inputs["awtrix"]["selector"]["device"]["filter"]

        self.assertEqual(metadata["homeassistant"]["min_version"], "2024.10.0")
        self.assertIn("Blueprint version: 2.0.0", metadata["description"])
        self.assertEqual(self.blueprint["variables"]["app_topic"], "dwd-warnings")
        self.assertEqual(
            device_filter,
            [
                {
                    "integration": "mqtt",
                    "manufacturer": "Blueforcer",
                    "model": "AWTRIX 3",
                }
            ],
        )
        self.assertTrue(
            inputs["weather_warning_var"]["selector"]["entity"]["multiple"]
        )
        preliminary = inputs["weather_preliminary_warning_var"]
        self.assertEqual(preliminary["default"], [])
        self.assertTrue(preliminary["selector"]["entity"]["multiple"])

    def test_optional_preliminary_sensors_use_state_trigger(self):
        preliminary_trigger = next(
            trigger
            for trigger in self.blueprint["triggers"]
            if trigger["id"] == "preliminary_changed"
        )

        self.assertEqual(preliminary_trigger["trigger"], "state")
        self.assertEqual(
            preliminary_trigger["entity_id"], "weather_preliminary_warning_var"
        )

    def test_legacy_single_sensor_inputs_are_normalized_to_lists(self):
        warnings = self.render_variable(
            "weather_warning_vars", weather_warning_input="sensor.dwd_warning"
        )
        preliminary = self.render_variable(
            "weather_preliminary_warning_vars",
            weather_preliminary_warning_input="sensor.dwd_preliminary",
        )
        no_preliminary = self.render_variable(
            "weather_preliminary_warning_vars",
            weather_preliminary_warning_input="",
        )

        self.assertEqual(warnings, "['sensor.dwd_warning']")
        self.assertEqual(preliminary, "['sensor.dwd_preliminary']")
        self.assertEqual(no_preliminary, "[]")

    def test_warning_renders_awtrix_3_payload(self):
        payload = json.loads(self.render_variable("payload", **self.payload_context()))

        self.assertEqual(payload["icon"], "ww-radiation")
        self.assertEqual(payload["pushIcon"], 2)
        self.assertEqual(payload["repeat"], 2)
        self.assertEqual(payload["color"], "#cc99ff")
        self.assertEqual(
            payload["text"],
            "Warnstufe 1: STARKE HITZE, Mi 11:00 Uhr - Mi 19:00 Uhr",
        )
        self.assertNotIn("rtttl", payload)

    def test_multiple_regions_prefix_every_warning_with_short_region(self):
        second_region = copy.deepcopy(self.sample)
        second_region["region_name"] = "Hansestadt Beispielstadt"
        second_region["warning_1_name"] = "STURM"
        second_region["warning_1_type"] = 51
        entity_attributes = {
            "sensor.dwd_warning": self.sample,
            "sensor.dwd_warning_two": second_region,
        }
        context = self.payload_context(
            weather_warning_vars=[
                "sensor.dwd_warning",
                "sensor.dwd_warning_two",
            ],
            show_region_name=True,
        )
        context["state_attr"] = (
            lambda entity_id, attribute: entity_attributes.get(entity_id, {}).get(
                attribute
            )
        )

        payload = json.loads(self.render_variable("payload", **context))

        self.assertEqual(len(payload), 2)
        self.assertTrue(payload[0]["text"].startswith("ABC: Warnstufe 1:"))
        self.assertTrue(
            payload[1]["text"].startswith("Beispielstadt: Warnstufe 1:")
        )

    def test_region_names_strip_prefixes_and_count_unique_regions(self):
        entities = {
            "sensor.one": {"region_name": "Gemeinde Nord"},
            "sensor.one_preliminary": {"region_name": "Gemeinde Nord"},
            "sensor.two": {"region_name": "Stadt Süd"},
            "sensor.three": {"region_name": "Hansestadt West"},
        }

        rendered = self.render_variable(
            "region_names",
            all_weather_warning_vars=list(entities),
            state_attr=lambda entity_id, attribute: entities[entity_id].get(attribute),
        )

        self.assertEqual(rendered, "['Nord', 'Süd', 'West']")
        self.assertTrue(
            self.render_boolean(
                "show_region_name", region_names=["Nord", "Süd", "West"]
            )
        )
        self.assertFalse(
            self.render_boolean("show_region_name", region_names=["Nord"])
        )

    def test_no_warning_renders_empty_payload(self):
        rendered = self.render_variable(
            "payload", **self.payload_context(attributes={"warning_count": 0})
        )

        self.assertEqual(rendered, "")

    def test_preliminary_warning_renders_as_second_frame(self):
        context = self.payload_context(
            preliminary_attributes=self.sample,
            weather_preliminary_warning_vars=["sensor.dwd_preliminary"],
        )

        payload = json.loads(self.render_variable("payload", **context))

        self.assertEqual(len(payload), 2)
        self.assertTrue(payload[0]["text"].startswith("Warnstufe 1:"))
        self.assertTrue(payload[1]["text"].startswith("Vorwarnstufe 1:"))

    def test_change_detection_ignores_last_update(self):
        previous = copy.deepcopy(self.sample)
        current = copy.deepcopy(self.sample)
        current["last_update"] = "2026-08-05T12:17:26+00:00"

        should_publish = self.render_boolean(
            "should_publish",
            send_on_change_only=True,
            show_details=False,
            warning_level_to_show=1,
            trigger=state_trigger("warning_changed", current, previous),
        )

        self.assertFalse(should_publish)

    def test_preliminary_change_detection_uses_changed_sensor_state(self):
        previous = copy.deepcopy(self.sample)
        current = copy.deepcopy(self.sample)
        current["warning_1_level"] = 2

        should_publish = self.render_boolean(
            "should_publish",
            send_on_change_only=True,
            show_details=False,
            warning_level_to_show=1,
            trigger=state_trigger("preliminary_changed", current, previous),
        )

        self.assertTrue(should_publish)

    def test_beep_only_for_new_or_escalated_warning(self):
        unchanged = self.render_boolean(
            "should_beep",
            play_beep=True,
            warning_level_to_show=1,
            trigger=state_trigger("warning_changed", self.sample, self.sample),
        )
        new_warning = self.render_boolean(
            "should_beep",
            play_beep=True,
            warning_level_to_show=1,
            trigger=state_trigger(
                "warning_changed", self.sample, {"warning_count": 0}
            ),
        )
        escalated = copy.deepcopy(self.sample)
        escalated["warning_1_level"] = 2
        preliminary_escalation = self.render_boolean(
            "should_beep",
            play_beep=True,
            warning_level_to_show=1,
            trigger=state_trigger(
                "preliminary_changed", escalated, self.sample
            ),
        )
        refresh = self.render_boolean(
            "should_beep",
            play_beep=True,
            warning_level_to_show=1,
            trigger=state_trigger("refresh"),
        )

        self.assertFalse(unchanged)
        self.assertTrue(new_warning)
        self.assertTrue(preliminary_escalation)
        self.assertFalse(refresh)


if __name__ == "__main__":
    unittest.main()
