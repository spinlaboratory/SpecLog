"""Load the packaged, non-user-editable monitor plot style."""

from configparser import ConfigParser
import math
from pathlib import Path

from PySide6.QtCore import Qt
import pyqtgraph as pg


MONITOR_CONFIG_PATH = Path(__file__).parent / "config" / "monitor_config.cfg"

LINE_STYLES = {
    "solid": Qt.PenStyle.SolidLine,
    "dash": Qt.PenStyle.DashLine,
    "dot": Qt.PenStyle.DotLine,
    "dash_dot": Qt.PenStyle.DashDotLine,
}


def load_monitor_style(path=MONITOR_CONFIG_PATH):
    config = ConfigParser(interpolation=None)
    config.optionxform = str
    if not config.read(path):
        raise FileNotFoundError(f"Monitor style file was not found: {path}")

    colors = dict(config["Bruker Colors"])
    color_names = [
        name.strip()
        for name in config["Plot"]["color_order"].split(",")
        if name.strip()
    ]
    missing = [name for name in color_names if name not in colors]
    if missing:
        raise ValueError("Unknown monitor colors: " + ", ".join(missing))
    style_names = [
        name.strip().lower()
        for name in config["Plot"]["line_styles"].split(",")
        if name.strip()
    ]
    unknown_styles = [name for name in style_names if name not in LINE_STYLES]
    if unknown_styles:
        raise ValueError("Unknown monitor line styles: " + ", ".join(unknown_styles))
    return {
        "colors": [colors[name] for name in color_names],
        "line_styles": [LINE_STYLES[name] for name in style_names],
        "line_width": float(config["Plot"]["line_width"]),
    }


def make_curve_pens(names, monitor_style):
    """Assign colors and line shapes from the current selection order."""
    colors = monitor_style["colors"]
    line_styles = monitor_style["line_styles"]
    width = monitor_style["line_width"]
    return {
        name: pg.mkPen(
            color=colors[index % len(colors)],
            style=line_styles[(index // len(colors)) % len(line_styles)],
            width=width,
        )
        for index, name in enumerate(names)
    }


def attach_readable_legend(plot_widget):
    """Place a large, opaque legend below the plot instead of over its data."""
    # PyQtGraph enables only the left and bottom axes by default. Use real,
    # value-free axes for the other two edges rather than a ViewBox border;
    # otherwise the left and bottom lines are drawn twice and look thicker.
    axis_pen = pg.mkPen("#A0A0A0", width=1)
    for position in ("left", "bottom", "top", "right"):
        if position in ("top", "right"):
            plot_widget.plotItem.showAxis(position)
        axis = plot_widget.plotItem.getAxis(position)
        axis.setPen(axis_pen)
        if position in ("top", "right"):
            axis.setStyle(showValues=False, tickLength=0)
            # A value-free AxisItem otherwise collapses to zero thickness and
            # its edge can be clipped from both the window and exported image.
            if position == "top":
                axis.setHeight(2)
            else:
                axis.setWidth(2)
    legend = pg.LegendItem(
        horSpacing=10,
        verSpacing=3,
        pen=pg.mkPen("#737373"),
        brush=pg.mkBrush(255, 255, 255, 245),
        labelTextColor="#313331",
        labelTextSize="11pt",
        colCount=1,
    )
    plot_widget.plotItem.layout.addItem(legend, 4, 1)
    return legend


def update_legend_columns(legend, curve_count, force=False):
    # Keep every legend column short enough to scan easily. LegendItem lays
    # entries out by rows, so ceil(count / 4) guarantees at most four rows.
    columns = max(1, math.ceil(curve_count / 4))
    if force and legend.columnCount == columns and legend.items:
        # LegendItem.removeItem leaves empty grid cells when the number of
        # columns is unchanged. Toggle once to rebuild a compact layout.
        legend.setColumnCount(columns + 1)
    if legend.columnCount != columns:
        legend.setColumnCount(columns)
