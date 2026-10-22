"""Device-independent configuration checks; no device enumeration or fake driver."""
from .contracts import require


def validate_d405_config(config):
    require(config.get('owner')=='single_capture_process','one D405 capture owner required')
    for key in ('serial','role','sdk_version','color_profile','depth_profile','calibration_version'):
        require(config.get(key) not in (None,'UNCONFIGURED'),f'D405 {key} UNCONFIGURED')
    require(config.get('model')=='D405','D405 model')
    return config


def validate_flexitac_config(config):
    for key in ('protocol','firmware','transport','shape','dtype','device_id','timestamp_semantics'):
        require(config.get(key) not in (None,'UNCONFIGURED'),f'FlexiTac {key} UNCONFIGURED')
    require(config.get('quantity')=='raw_reading','uncalibrated FlexiTac cannot be called force')
    return config


def hardware_parser_status():
    return {'D405':'BLOCKED: SDK/device profile and ownership not verified; no acquisition driver implemented',
            'FlexiTac':'BLOCKED: real protocol unknown; no parser implemented; canonical raw frames supported'}
