# SpecLog
Python Package for Spectrometer Logging

Start the applications normally:

```text
SpecLogger
SpecMonitor
```

Start either application with a visible debug console:

```text
SpecLogger -debug True
SpecMonitor -debug True
```

Edit the shared configuration in `C:\Users\Public\LOG_Config\config.cfg`:

```text
SpecLogger --config
```

The editor validates changes before saving, keeps `config.cfg.bak`, and asks
you to restart the logger and monitor before the new settings take effect.

SpecMonitor opens quickly by loading only recent live files. To plot all
available history, leave both date fields at their defaults and click **Ok**.
Historical CSV files are indexed in `monitor_cache.sqlite` in the log folder;
later queries import only files that are new or changed.
