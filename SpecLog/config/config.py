"""
global config
"""
import configparser
from pathlib import Path
import warnings
import os
import shutil

import logging

logger = logging.getLogger(__name__)
PUBLIC_CONFIG_DIR = Path("C:/Users/Public/LOG_Config")


def ensure_public_config(configname="config.cfg"):
    """Return the editable public config path, creating it when necessary."""
    PUBLIC_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    public_config = PUBLIC_CONFIG_DIR / configname
    packaged_config = Path(__file__).parent / configname
    if not public_config.exists():
        shutil.copy(packaged_config, public_config)
    return public_config


def _escape_split(s, delim=",", escape="\\"):
    tokens = []
    previous_escape = False
    subtoken = ""
    for k in range(len(s)):
        if s[k] == delim and (not previous_escape):
            if len(subtoken) > 0:
                tokens.append(subtoken)
            subtoken = ""  # reset subtoken
        else:
            # ESCAPE DELIM  -> DELIM
            if previous_escape and s[k] != escape and s[k] == delim:
                subtoken = subtoken[:-1] + s[k]
            else:
                # add to subtoken
                subtoken += s[k]
            # set previous_escape flag:
            # If for current char is escape (True and s[k]=='\\') and previous_escape is False -> set it to True
            # If for current char is escape (True and s[k]=='\\') and previous_escape is True -> case of '\\\\' -> escaping an escape character -> set it back to False
            # if current char is no escape character -> set it to false
            previous_escape = (not previous_escape) and (s[k] == escape)
    if len(subtoken) > 0:
        tokens.append(subtoken)
    return tokens


def _kwarg_converter(s: str):
    tokens = _escape_split(s, ",", escape="\\")
    args = []
    kwargs = {}
    for k in tokens:
        subtokens = _escape_split(k, "=", escape="\\")
        if len(subtokens) == 1:
            args.append(subtokens[0])
        else:
            kwargs[subtokens[0].strip()] = subtokens[1].strip()
    return args, kwargs


def _get_log_config(configname, key=None):
    config = configparser.ConfigParser(
        converters={
            "list": lambda x: list(x.strip("[").strip("]").split(",")),
            "args_kwargs": _kwarg_converter,
        }
    )
    # define three possible locations:
    log_current_config = Path.cwd() / configname
    log_home_config = Path.home() / configname

    log_cfg_folder = str(Path(__file__).parent)  # / configname #.with_name("config"))

    log_global_config = Path(log_cfg_folder) / configname

    if key == "public":
        # copy command to public location
        # check if command location
        log_public_config = ensure_public_config(configname)

        config.read(log_public_config)
    else:
        config_read_list = [log_global_config, log_home_config, log_current_config]

        # user defined takes precedence
        config.read(config_read_list)

    return config


# Loading the package must not create or modify files. The public, editable
# configuration is created only when loggerConfig is actually instantiated.
CONFIG = _get_log_config("config.cfg")
