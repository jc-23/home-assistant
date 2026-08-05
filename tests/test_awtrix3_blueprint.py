import copy
import json
import unittest

from blueprint_helpers import (
    REPOSITORY_ROOT,
    event_trigger,
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
            "weather_warning_var": "sensor.dwd_warning",
            "weather_preliminary_warning_var": "",
            "warnings_count": attributes.get("warning_count", 0),
            "preliminary_warnings_count": preliminary_attributes.get(
                "warning_count", 0
            ),
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
        self.assertNotIn("app_name", inputs)
        self.assertEqual(self.blueprint["variables"]["app_topic"], "jc-23")
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
        preliminary = inputs["weather_preliminary_warning_var"]
        self.assertEqual(preliminary["default"], "")
        self.assertFalse(preliminary["selector"]["entity"]["multiple"])

    def test_optional_preliminary_sensor_uses_filtered_event_trigger(self):
        preliminary_trigger = next(
            trigger
            for trigger in self.blueprint["triggers"]
            if trigger["id"] == "preliminary_changed"
        )

        self.assertEqual(preliminary_trigger["trigger"], "event")
        self.assertEqual(preliminary_trigger["event_type"], "state_changed")
        self.assertEqual(
            preliminary_trigger["event_data"]["entity_id"],
            "weather_preliminary_warning_var",
        )

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

    def test_no_warning_renders_empty_payload(self):
        rendered = self.render_variable(
            "payload", **self.payload_context(attributes={"warning_count": 0})
        )

        self.assertEqual(rendered, "")

    def test_preliminary_warning_renders_as_second_frame(self):
        context = self.payload_context(
            preliminary_attributes=self.sample,
            weather_preliminary_warning_var="sensor.dwd_preliminary",
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

    def test_preliminary_change_detection_uses_event_state(self):
        previous = copy.deepcopy(self.sample)
        current = copy.deepcopy(self.sample)
        current["warning_1_level"] = 2

        should_publish = self.render_boolean(
            "should_publish",
            send_on_change_only=True,
            show_details=False,
            warning_level_to_show=1,
            trigger=event_trigger("preliminary_changed", current, previous),
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
            trigger=event_trigger(
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
