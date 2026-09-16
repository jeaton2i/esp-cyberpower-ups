import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID
from esphome.components.esp32 import add_idf_sdkconfig_option

# ESPHome 2026.9.0 added esp_http_server to the ESP-IDF components that are
# excluded from the build by default. include_builtin_idf_component only exists
# from ESPHome 2026.2.0 on, so keep the import optional.
try:
    from esphome.components.esp32 import include_builtin_idf_component
except ImportError:
    include_builtin_idf_component = None

DEPENDENCIES = ["network"]
CODEOWNERS = []

cyberpower_ups_ns = cg.esphome_ns.namespace("cyberpower_ups")
CyberpowerUpsComponent = cyberpower_ups_ns.class_("CyberpowerUpsComponent", cg.Component)

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(CyberpowerUpsComponent),
    }
).extend(cv.COMPONENT_SCHEMA)

async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    # USB host on ESP32-S3
    add_idf_sdkconfig_option("CONFIG_USB_OTG_SUPPORTED", True)
    add_idf_sdkconfig_option("CONFIG_USB_HOST_CONTROL_TRANSFER_MAX_SIZE", 1024)

    # HTTP server for status web UI
    # Without this, web_ui.h dies on ESPHome 2026.9.0+ with
    # "fatal error: esp_http_server.h: No such file or directory" because the
    # component is neither built nor listed in the REQUIRES of "src".
    if include_builtin_idf_component is not None:
        include_builtin_idf_component("esp_http_server")
    add_idf_sdkconfig_option("CONFIG_HTTPD_MAX_REQ_HDR_LEN", 1024)
    add_idf_sdkconfig_option("CONFIG_LWIP_MAX_SOCKETS", 16)

    # USB HID host support
    # Hub support disabled for now — was preventing device detection entirely
    # Low-speed devices (1.5Mbps UPS) may need a hub, but first get basic detection working
    add_idf_sdkconfig_option("CONFIG_USB_HOST_HUBS_SUPPORTED", False)
    add_idf_sdkconfig_option("CONFIG_USB_HOST_ENABLE_ENUM_FILTER_CALLBACK", True)

    # PSRAM can cause USB host interrupts to be missed (ESP-IDF #9519)
    add_idf_sdkconfig_option("CONFIG_SPIRAM", False)
    add_idf_sdkconfig_option("CONFIG_ESP32S3_SPIRAM_SUPPORT", False)

    # No MQTT needed — uses native ESPHome API for HA integration
