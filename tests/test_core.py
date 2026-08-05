import logging
import importlib
import io
import inspect
from configparser import ConfigParser
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from SpecLog.SpecLog import SpecLog
from SpecLog.SpecMonitor import _build_parser
from SpecLog.debugLog import debugLog
from SpecLog.device import DEVICE, DeviceProtocol
from SpecLog.history import HistoryCache
from SpecLog.config_editor import ConfigEditor
from SpecLog.SpecLogger import (
    _build_parser as build_logger_parser,
    configure_startup,
)
from SpecLog.loggerConfig import loggerConfig

debug_log_module = importlib.import_module("SpecLog.debugLog")
monitor_module = importlib.import_module("SpecLog.monitor")


class LoggerConfigTests(unittest.TestCase):
    def test_command_literals_are_safe_and_lists_keep_their_commas(self):
        config = loggerConfig.__new__(loggerConfig)
        parsed = config._command_analysis(
            "READ?, min = 0, indicators = ['ok', '*fault']"
        )

        self.assertEqual(parsed["min"], 0)
        self.assertEqual(parsed["indicators"], ["ok", "fault"])
        self.assertEqual(parsed["indicators_reverse"], [False, True])

        with self.assertRaises((ValueError, SyntaxError)):
            config._command_analysis(
                "READ?, min = __import__('os').getcwd()"
            )

    def test_invalid_termination_raises_value_error(self):
        config = loggerConfig.__new__(loggerConfig)
        with self.assertRaises(ValueError):
            config._getTermination("invalid")


class SpecLogTests(unittest.TestCase):
    def test_failed_string_conversion_returns_nan(self):
        logger = SpecLog.__new__(SpecLog)
        logger.debugLogger = Mock(spec=logging.Logger)

        self.assertEqual(logger._returnStringConverter("", ",", 2), "nan")


class SpecMonitorCliTests(unittest.TestCase):
    def test_monitor_debug_flag_matches_logger_syntax(self):
        args = _build_parser().parse_args(["-debug", "True"])
        self.assertEqual(args.debug, "True")
        self.assertEqual(args.number_of_file, 10)

    def test_monitor_retains_optional_file_count(self):
        args = _build_parser().parse_args(["25", "-debug", "False"])
        self.assertEqual(args.debug, "False")
        self.assertEqual(args.number_of_file, 25)


class SpecLoggerCliTests(unittest.TestCase):
    def test_config_flag_opens_editor_mode_without_logger_status(self):
        args = build_logger_parser().parse_args(["--config"])
        self.assertTrue(args.config)
        self.assertIsNone(args.status)

    def test_startup_true_creates_system_start_task(self):
        runner = Mock(return_value=SimpleNamespace(returncode=0, stdout="", stderr=""))
        with patch("SpecLog.SpecLogger.os.path.isfile", return_value=True):
            message = configure_startup(True, "C:/SpecLog/runner.exe", runner)

        command = runner.call_args.args[0]
        self.assertEqual(command[0], "schtasks")
        self.assertIn("/Create", command)
        self.assertIn("ONSTART", command)
        self.assertIn("SYSTEM", command)
        self.assertIn("0000:30", command)
        self.assertIn("without login", message)

    def test_startup_false_disables_existing_task(self):
        result = SimpleNamespace(returncode=0, stdout="", stderr="")
        runner = Mock(side_effect=[result, result])

        message = configure_startup(False, runner=runner)

        self.assertIn("/Query", runner.call_args_list[0].args[0])
        self.assertIn("/DISABLE", runner.call_args_list[1].args[0])
        self.assertIn("disabled", message)


class ConfigEditorTests(unittest.TestCase):
    def test_required_settings_validation(self):
        config = ConfigParser()
        config.read_dict(
            {
                "SETTINGS": {
                    "log_interval": "10",
                    "log_folder_location": "C:/Users/Public/",
                    "save_file_size_kb": "1024",
                }
            }
        )
        editor = SimpleNamespace(config=config)
        ConfigEditor._validate_structure(editor)

        config.remove_option("SETTINGS", "log_interval")
        with self.assertRaises(ValueError):
            ConfigEditor._validate_structure(editor)


class MonitorLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = (
            monitor_module.QApplication.instance()
            or monitor_module.QApplication(["monitor-tests"])
        )

    def test_file_discovery_is_sorted_filtered_and_honors_count(self):
        monitor = SimpleNamespace(file_dir="unused", number_of_files=2)
        with patch.object(
            monitor_module.os,
            "listdir",
            return_value=[
                "display_settings.txt",
                "log_20260103.csv",
                "quick_plot_log_old.py",
                "log_20260101.csv",
                "log_20260102.csv",
            ],
        ):
            self.assertTrue(monitor_module.MainWindow.getFiles(monitor))

        self.assertEqual(
            monitor.file_list, ["log_20260102.csv", "log_20260103.csv"]
        )

    def test_bit_conversion_rejects_invalid_data_without_eval(self):
        monitor = SimpleNamespace(_is_missing=monitor_module.MainWindow._is_missing)
        self.assertEqual(
            monitor_module.MainWindow.convertStringtoBit(
                monitor, "12C", bits=9, reverse=True
            ),
            "001101001",
        )
        self.assertEqual(
            monitor_module.MainWindow.convertStringtoBit(
                monitor, "not-a-number", bits=9
            ),
            -1,
        )

    def test_warning_escalates_from_near_limit_to_error(self):
        warning_text = Mock()
        monitor = SimpleNamespace(
            all_data_by_name={
                "Date": ["2026-01-01"],
                "Time": ["00:00:00"],
                "temperature": [10.2],
            },
            command_info_by_name={
                "temperature": [10, 20, None, None]
            },
            warning_level_by_name={"temperature": 0},
            warningText=warning_text,
            _is_missing=monitor_module.MainWindow._is_missing,
        )

        monitor_module.MainWindow.printWarning(monitor)
        self.assertEqual(monitor.warning_level_by_name["temperature"], 1)
        monitor.all_data_by_name["temperature"][-1] = 9
        monitor_module.MainWindow.printWarning(monitor)
        self.assertEqual(monitor.warning_level_by_name["temperature"], 2)
        self.assertEqual(warning_text.appendPlainText.call_count, 2)

    def test_recent_log_activity_detects_pre_mutex_logger(self):
        monitor = SimpleNamespace(
            current_file="log_20260101.csv",
            file_dir="logs",
            log_interval=10,
        )
        with (
            patch.object(monitor_module.os.path, "getmtime", return_value=90),
            patch.object(monitor_module._time, "time", return_value=100),
        ):
            self.assertTrue(
                monitor_module.MainWindow._has_recent_log_activity(monitor)
            )

        with (
            patch.object(monitor_module.os.path, "getmtime", return_value=50),
            patch.object(monitor_module._time, "time", return_value=100),
        ):
            self.assertFalse(
                monitor_module.MainWindow._has_recent_log_activity(monitor)
            )

    def test_eof_poll_preserves_latest_device_reading(self):
        latest = {"temperature": 42.0}
        monitor = SimpleNamespace(
            current_file="log_20260101.csv",
            file_list=["log_20260101.csv"],
            f=io.StringIO(""),
            latest_data=latest,
            plot_type=True,
            livePlot=Mock(),
            staticPlot=Mock(),
        )

        self.assertFalse(monitor_module.MainWindow.updateData(monitor))
        self.assertIs(monitor.latest_data, latest)
        monitor.livePlot.assert_called_once_with()

    def test_history_downsampling_preserves_bucket_extremes(self):
        rows = [
            (1, "2026-01-01", "00:00:01", {"value": "5"}),
            (2, "2026-01-01", "00:00:02", {"value": "-10"}),
            (3, "2026-01-01", "00:00:03", {"value": "100"}),
            (4, "2026-01-01", "00:00:04", {"value": "7"}),
        ]
        envelope = HistoryCache._bucket_envelope(rows)
        self.assertEqual(envelope[0][3]["value"], -10.0)
        self.assertEqual(envelope[1][3]["value"], 100.0)

    def test_adaptive_axis_time_labels_include_date(self):
        axis = monitor_module.MonitorDateAxisItem(utcOffset=0)
        labels = axis.tickStrings([0, 3661], scale=1, spacing=60)
        self.assertEqual(labels[0], "1970-01-01\n00:00")
        self.assertEqual(labels[1], "1970-01-01\n01:01")
        self.assertEqual(axis.style["hideOverlappingLabels"], 70)
        self.assertTrue(
            all("2026-08-05" in level.exampleText for level in axis.zoomLevels.values())
        )

    def test_narrow_axis_falls_back_to_center_tick(self):
        axis = monitor_module.MonitorDateAxisItem(utcOffset=0)
        with patch.object(
            monitor_module.pg.DateAxisItem,
            "tickValues",
            return_value=[],
        ):
            levels = axis.tickValues(100, 200, 100)
        self.assertEqual(levels, [(100, [150])])

    def test_monitor_reserves_space_for_two_line_tick_labels(self):
        source = inspect.getsource(monitor_module.MainWindow.getLine)
        self.assertIn("tickTextHeight=36", source)
        self.assertIn("setHeight(52)", source)

    def test_data_selection_uses_start_plus_duration_in_days(self):
        start = 1_700_000_000
        monitor = SimpleNamespace(
            startTime=SimpleNamespace(text=lambda: "202311142213"),
            durationValue=SimpleNamespace(value=lambda: 2.0),
            durationUnit=SimpleNamespace(currentText=lambda: "Days"),
            warningText=Mock(),
            returnSeconds=lambda value: start,
            _history_loading=True,
        )

        self.assertFalse(
            monitor_module.MainWindow.getSelectedDataRangeByDate(monitor)
        )
        self.assertEqual(
            monitor.static_time_range,
            [start, start + 2 * 24 * 60 * 60],
        )

    def test_duration_requires_start_unless_all_is_selected(self):
        monitor = SimpleNamespace(
            startTime=SimpleNamespace(text=lambda: "yyyymmddHHMM"),
            durationValue=SimpleNamespace(value=lambda: 1.0),
            durationUnit=SimpleNamespace(currentText=lambda: "Hours"),
            warningText=Mock(),
            returnSeconds=lambda value: None,
        )

        self.assertFalse(
            monitor_module.MainWindow.getSelectedDataRangeByDate(monitor)
        )
        monitor.warningText.appendPlainText.assert_called_once()

    def test_reset_clears_data_selection_controls(self):
        monitor = SimpleNamespace(
            plot_type=False,
            selected_data_by_file=True,
            selected_data_by_date=True,
            static_update_request=True,
            startTime=Mock(),
            durationValue=Mock(),
            durationUnit=Mock(),
            statusbar=Mock(),
        )

        monitor_module.MainWindow.setLive(monitor)

        monitor.startTime.clear.assert_called_once_with()
        monitor.durationValue.setValue.assert_called_once_with(0)
        monitor.durationUnit.setCurrentIndex.assert_called_once_with(0)
        self.assertTrue(monitor.plot_type)


class DeviceProtocolTests(unittest.TestCase):
    class FakeEthernetProtocol(DeviceProtocol):
        def __init__(self):
            self.addresses = ["192.0.2.10:5025"]
            self.connections = []
            self.queries = []
            self.closed = []
            self.fail_queries = False

        def refresh(self):
            pass

        def available_addresses(self):
            return list(self.addresses)

        def connect(self, settings):
            connection = object()
            self.connections.append((settings, connection))
            return connection

        def query(self, connection, command, termination):
            self.queries.append((connection, command, termination))
            if self.fail_queries:
                raise OSError("connection became unusable")
            return "FAKE,DEVICE\n"

        def close(self, connection):
            self.closed.append(connection)

    def test_device_uses_injected_protocol_for_connect_and_query(self):
        ethernet = self.FakeEthernetProtocol()
        config = SimpleNamespace(
            devices={
                "network_device": {
                    "device_status": True,
                    "protocol": "ETHERNET",
                    "address": "192.0.2.10:5025",
                    "id_command": "*IDN?",
                    "termination": "\n",
                }
            }
        )

        devices = DEVICE(
            config,
            Mock(spec=logging.Logger),
            protocols={"ethernet": ethernet},
        )

        self.assertEqual(
            devices.query("network_device", "MEASURE?"), "FAKE,DEVICE\n"
        )
        self.assertEqual(len(ethernet.connections), 1)
        self.assertEqual(
            [query[1] for query in ethernet.queries], ["*IDN?", "MEASURE?"]
        )

    def test_failed_handle_is_closed_and_reopened_with_port_still_visible(self):
        ethernet = self.FakeEthernetProtocol()
        config = SimpleNamespace(
            devices={
                "network_device": {
                    "device_status": True,
                    "protocol": "ethernet",
                    "address": "192.0.2.10:5025",
                    "id_command": "*IDN?",
                    "termination": "\n",
                }
            }
        )
        devices = DEVICE(
            config,
            Mock(spec=logging.Logger),
            protocols={"ethernet": ethernet},
            stabilization_seconds=0,
        )
        failed_connection = devices.device_info["network_device"]["device"]

        ethernet.fail_queries = True
        with self.assertRaises(OSError):
            devices.query("network_device", "MEASURE?")

        info = devices.device_info["network_device"]
        self.assertIsNone(info["device"])
        self.assertEqual(info["state"], "retry_wait")
        self.assertEqual(ethernet.closed, [failed_connection])

        ethernet.fail_queries = False
        info["next_retry_time"] = 0
        self.assertTrue(devices.reconnectDevices())
        self.assertEqual(info["state"], "connected")
        self.assertEqual(info["retry_count"], 0)
        self.assertEqual(len(ethernet.connections), 2)

        devices.close()
        self.assertIsNone(info["device"])
        self.assertEqual(info["state"], "disconnected")


class DebugLogTests(unittest.TestCase):
    def test_reconfiguration_does_not_accumulate_handlers(self):
        fake_config = SimpleNamespace(
            settings={"log_folder_location": "unused"}
        )

        def handler(*args, **kwargs):
            return Mock(spec=logging.Handler)

        with (
            patch.object(debug_log_module, "loggerConfig", return_value=fake_config),
            patch.object(debug_log_module.os.path, "exists", return_value=True),
            patch.object(debug_log_module.logging, "FileHandler", side_effect=handler),
            patch.object(debug_log_module.logging, "StreamHandler", side_effect=handler),
        ):
            first = debugLog("config.cfg").logger
            second = debugLog("config.cfg").logger
            owned_handlers = [
                handler
                for handler in second.handlers
                if getattr(handler, "_speclog_handler", False)
            ]

            self.assertIs(first, second)
            self.assertEqual(len(owned_handlers), 2)

            for handler in list(second.handlers):
                if getattr(handler, "_speclog_handler", False):
                    second.removeHandler(handler)
                    handler.close()


if __name__ == "__main__":
    unittest.main()
