import copy
import json
import unittest
from types import SimpleNamespace

from blueprint_helpers import (
    REPOSITORY_ROOT,
    load_blueprint,
    load_fixture,
    state_trigger,
    template_environment,
)


BLUEPRINT_PATH = (
    REPOSITORY_ROOT / "blueprints/automation/awtrix_ng_weather_warning_dwd.yaml"
)


class AwtrixNgBlueprintTests(unittest.TestCase):
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

    def payload_context(self, entity_attributes, **overrides):
        context = {
            "state_attr": lambda entity_id, attribute: entity_attributes.get(
                entity_id, {}
            ).get(attribute),
            "weather_warning_vars": ["sensor.dwd_warning"],
            "weather_preliminary_warning_vars": [],
            "show_region_name": False,
            "warning_level_to_show": 1,
            "message_repeat": 2,
            "icons_behavior": "push",
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
            "icon_radiation": "ww-radiation",
            "icon_warning": "ww-generic",
        }
        context.update(overrides)
        return context

    def test_schema_targets_awtrix_ng_and_multiple_sensors(self):
        metadata = self.blueprint["blueprint"]
        required = metadata["input"]["required"]["input"]
        behavior = metadata["input"]["behavior"]["input"]
        device_filter = required["awtrix"]["selector"]["device"]["filter"]

        self.assertEqual(metadata["homeassistant"]["min_version"], "2024.11.0")
        self.assertIn("Blueprint version: 1.0.0", metadata["description"])
        self.assertNotIn("app_name", behavior)
        self.assertEqual(self.blueprint["variables"]["app_topic"], "dwd-warnings")
        self.assertTrue(
            required["weather_warning_vars"]["selector"]["entity"]["multiple"]
        )
        preliminary = required["weather_preliminary_warning_vars"]
        self.assertEqual(preliminary["default"], [])
        self.assertTrue(preliminary["selector"]["entity"]["multiple"])
        self.assertEqual(
            device_filter,
            [
                {
                    "integration": "mqtt",
                    "manufacturer": "Blueforcer",
                    "model": "AWTRIX NG",
                }
            ],
        )

    def test_single_region_keeps_compact_warning_text(self):
        context = self.payload_context({"sensor.dwd_warning": self.sample})

        payload = json.loads(self.render_variable("payload", **context))

        self.assertEqual(payload["icon"], "ww-radiation")
        self.assertEqual(payload["iconMode"], "push")
        self.assertEqual(payload["textColor"], "#cc99ff")
        self.assertEqual(
            payload["text"],
            "Warnstufe 1: STARKE HITZE, Mi 11:00 Uhr - Mi 19:00 Uhr",
        )
        self.assertNotIn("pushIcon", payload)
        self.assertNotIn("color", payload)

    def test_multiple_regions_prefix_every_warning_with_short_region(self):
        second_region = copy.deepcopy(self.sample)
        second_region["region_name"] = "Stadt Beispielstadt"
        second_region["warning_1_name"] = "STURM"
        second_region["warning_1_type"] = 51
        entities = {
            "sensor.dwd_warning": self.sample,
            "sensor.dwd_warning_two": second_region,
        }
        context = self.payload_context(
            entities,
            weather_warning_vars=[
                "sensor.dwd_warning",
                "sensor.dwd_warning_two",
            ],
            show_region_name=True,
        )

        payload = json.loads(self.render_variable("payload", **context))

        self.assertEqual(len(payload), 2)
        self.assertTrue(payload[0]["text"].startswith("ABC: Warnstufe 1:"))
        self.assertTrue(
            payload[1]["text"].startswith("Beispielstadt: Warnstufe 1:")
        )

    def test_region_names_are_unique_and_strip_municipality_prefixes(self):
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

    def test_current_and_preliminary_sensor_for_same_region_need_no_prefix(self):
        entities = {
            "sensor.dwd_warning": self.sample,
            "sensor.dwd_preliminary": self.sample,
        }
        context = self.payload_context(
            entities,
            weather_preliminary_warning_vars=["sensor.dwd_preliminary"],
            show_region_name=False,
        )

        payload = json.loads(self.render_variable("payload", **context))

        self.assertEqual(len(payload), 2)
        self.assertTrue(payload[0]["text"].startswith("Warnstufe 1:"))
        self.assertTrue(payload[1]["text"].startswith("Vorwarnstufe 1:"))
        self.assertNotIn("ABC:", payload[0]["text"])
        self.assertNotIn("ABC:", payload[1]["text"])

    def test_no_warning_renders_empty_payload(self):
        context = self.payload_context(
            {"sensor.dwd_warning": {"warning_count": 0}}
        )

        self.assertEqual(self.render_variable("payload", **context), "")

    def test_region_change_is_a_relevant_payload_change(self):
        previous = copy.deepcopy(self.sample)
        current = copy.deepcopy(self.sample)
        current["region_name"] = "Stadt Andere Region"

        should_publish = self.render_boolean(
            "should_publish",
            send_on_change_only=True,
            show_details=False,
            warning_level_to_show=1,
            trigger=state_trigger("warning_changed", current, previous),
        )

        self.assertTrue(should_publish)

    def test_device_prefixes_use_ng_discovery_sensor(self):
        device_entities = {
            "device-one": ["sensor.clock_one_mqtt_prefix", "sensor.clock_one_ip"],
            "device-two": ["sensor.clock_two_mqtt_prefix"],
            "invalid": ["sensor.unrelated"],
        }
        states = {
            "sensor.clock_one_mqtt_prefix": "clock-one",
            "sensor.clock_two_mqtt_prefix": "clock-two",
        }

        rendered = self.render_variable(
            "device_prefixes",
            device_ids=["device-one", "device-two", "invalid"],
            device_entities=lambda device_id: device_entities[device_id],
            states=lambda entity_id: states.get(entity_id, "unknown"),
        )

        self.assertEqual(rendered, "['clock-one', 'clock-two']")

    def test_actions_use_only_awtrix_ng_topics(self):
        rendered_actions = json.dumps(self.blueprint["actions"])

        self.assertIn("/cmd/apps/pushed/", rendered_actions)
        self.assertEqual(rendered_actions.count("/cmd/apps/pushed/"), 1)
        self.assertIn("/cmd/sounds/play", rendered_actions)
        self.assertNotIn("/custom/", rendered_actions)
        self.assertNotIn("/rtttl", rendered_actions)

    def test_availability_trigger_is_limited_to_selected_prefixes(self):
        selected = self.render_boolean(
            "is_selected_device_trigger",
            trigger=SimpleNamespace(
                id="awtrix_online", topic="clock-one/availability"
            ),
            device_prefixes=["clock-one"],
        )
        unrelated = self.render_boolean(
            "is_selected_device_trigger",
            trigger=SimpleNamespace(
                id="awtrix_online", topic="other-clock/availability"
            ),
            device_prefixes=["clock-one"],
        )

        self.assertTrue(selected)
        self.assertFalse(unrelated)


if __name__ == "__main__":
    unittest.main()
