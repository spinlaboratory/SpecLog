# SpecLog

SpecLog records data from connected spectrometer instruments and provides a
desktop monitor for viewing live and historical measurements.

## Quick start

Start the logger:

```text
SpecLogger
```

Open the monitor:

```text
SpecMonitor
```

Keep the logger running while using the monitor. The logger collects and saves
instrument data; the monitor reads and displays those saved measurements.

## Configure SpecLog

Open the configuration editor:

```text
SpecLogger --config
```

The shared configuration is saved at:

```text
C:\Users\Public\LOG_Config\config.cfg
```

Use the section list on the left to select global settings or a device.

### Global settings

The **SETTINGS** section contains options such as:

- Logging interval
- Log-folder location
- Maximum log-file size

### Device communication

For each device, use the **Communication** tab to configure its connection:

- Enable or disable the device
- Protocol
- Address or COM port
- Baud rate
- Termination
- Other serial communication attributes

### Device commands

Use **Commands > Values** for ordinary measurements. Each command can contain:

- Variable name
- Instrument command
- Display alias
- Minimum and maximum limits
- Expected static value

Use **Commands > Status Indicators** for commands that return status bits.
Click the indicators button to add, remove, reorder, or reverse individual
indicators. The editor calculates `bits` and `bit_static` automatically.

Click **Save** after making changes. The editor validates the configuration and
keeps the previous file as `config.cfg.bak`. Restart the logger and monitor to
apply the updated configuration.

## Control the logger

Start or stop the logger from a terminal:

```text
SpecLogger start
SpecLogger stop
```

You can also use **Start** and **Stop** at the bottom of the configuration
editor. Current status is shown as **Running**, **Stopped**, or **Status
unavailable**. Operation results and errors appear in the **Messages** area.

For troubleshooting, start the logger with a visible debug console:

```text
SpecLogger -debug True
```

## Start logging automatically without login

Open a terminal as Administrator and enable system startup:

```text
SpecLogger -startup True
```

The logger will start automatically after the next computer boot. A 30-second
delay allows USB and serial drivers to initialize first.

To run it immediately without rebooting:

```text
SpecLogger start
```

Disable automatic startup from an Administrator terminal:

```text
SpecLogger -startup False
```

The configuration editor also provides **Enable** and **Disable** startup
buttons. Administrator permission is normally required to use them.

If the startup task was created by another administrator, a standard account
may show startup as **Unavailable**. If new log data is still being written, the
logger status displays **Running (log activity)**. Start and Stop remain disabled
until the editor is opened with sufficient permission.

## Use the monitor

Open the monitor normally:

```text
SpecMonitor
```

Use the monitoring-item controls to select which measurements are plotted. Use
**Historical Data** to open a separate historical-data window. Enter a start time
and duration, choose curves from the **Items to plot** checklist, then click
**OK** to plot the selected range in that window. This checklist is independent
of the main monitor's live-item selection. After data is loaded, checking or
unchecking an item updates the historical plot immediately without loading the
files again. The main monitor remains open and
continues displaying live data. Click **Reset** to cancel the current historical
request and clear the selection fields and plot.

The historical plot uses a time-only horizontal axis; its title shows the full
start and end date/time. Click **Save** to export the loaded Date, Time, and
currently checked measurement items to a CSV file.

Click **Load** in the Historical Data window to open an existing SpecLog CSV
file in the historical plot. File loading is kept out of the main monitor so its
graph continues showing live data.

Click **Save Figure** to export the historical plot, including its title, axes,
curves, and legend, as a PNG image.

To load all available history, leave Start Time empty, keep Duration at **All**,
and click **OK**. The first import may take longer; later queries load only new or changed
files.

Start the monitor with a visible debug console when troubleshooting:

```text
SpecMonitor -debug True
```

Monitor curves use a high-contrast subset of the packaged Bruker color palette
that remains visible on a white background. They cycle through solid, dashed,
dotted, and dash-dot line shapes when additional curve styles are needed. Style
assignment is recalculated from the currently selected items, so selections that
fit within the color palette use solid lines only. These
application styles are stored internally in
`SpecLog/config/monitor_config.cfg`; they are separate from the public device
configuration.

Plot legends are displayed below the curves rather than over them. Legend and
axis text use larger fonts, and long legends automatically use additional
columns.

## Common status messages

- **Running**: The logger is active and directly detectable.
- **Running (log activity)**: New data confirms that the logger is active, but
  the current Windows account cannot query the system startup task.
- **Stopped**: The logger is not running.
- **Status unavailable**: The current account cannot verify the logger state and
  no recent log activity was detected.
- **Startup Enabled**: Automatic logging is configured for system boot.
- **Startup Disabled**: The startup task exists but automatic boot startup is
  disabled.
- **Startup Unavailable**: Open the configuration editor as Administrator to
  inspect or control a task created by another administrator.
