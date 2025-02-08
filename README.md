# alfred-qingping-monitor

![GitHub release (latest by date)](https://img.shields.io/github/v/release/Tan4ek/alfred-qingping-monitor)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-GNU%20GPL%20v3-blue)
![Alfred Workflow](https://img.shields.io/badge/alfred-5.0%2B-purple)

![example.jpg](./example.jpg)

## Features

This Alfred workflow allows you to quickly access your Qingping air quality data directly from Alfred 5. 

Currently supported measurements:
- CO₂ (Carbon Dioxide)
- PM2.5 (Fine particulate matter)
- TVOC (Total Volatile Organic Compounds)
- Temperature
- Humidity

Note: At this time, the workflow only supports data from Qingping Cloud services.

Also, you can configure device data reporting intervals (from 1 minute to 1 hour) directly from Alfred.

## Prerequisite

- Alfred 5
- Python 3.10+
- Qingping air monitor (for example, [Qingping Air Monitor](https://www.qingping.co/air-monitor/overview))

## Configuration

Connect the Qingping Air monitor to the Qingping+ app.
Generate a Qingping Developer API token from [developer.qingping.co/personal/permissionApply | Access Management | Apply Access](https://developer.qingping.co/personal/permissionApply)
