# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-07-18

First stable release. Earlier 0.0.x and 0.1.x releases were unstable and have
been withdrawn; the integration was rewritten from the ground up.

### Features

- Planned and unplanned outages for a single address, from the public Tauron
  Dystrybucja web API. The integration can be added several times for several
  addresses.
- **Calendar entity** exposing every outage as an event, so a calendar trigger
  with an offset can warn you any amount of time before an outage starts.
- **Event entity** that fires once when Tauron announces a previously unknown
  outage, usually days ahead.
- **Status sensor**: no outages / outage announced / outage in progress.
- Dedicated sensors for the start, end, duration and description of the relevant
  outage, plus a counter with the full list in its attributes. Each fact is its
  own entity, so dashboards need no templating.
- Binary sensor that is `on` while an outage is ongoing.
- Configurable polling interval (15-1440 minutes, default 60).
- Polish and English translations, including attribute names and enum states.
- Config entry diagnostics, with the house number redacted.

### Notes on the rewrite

The previous releases could not start at all: the sensor platform file was named
`sensors.py`, so Home Assistant raised `ModuleNotFoundError`. Beyond that, the
config flow stored city and street *names* while the outage API requires numeric
GAIDs, the street lookup passed `cityName` to an endpoint that requires
`ownerGAID` set to the city GAID, and outage parsing read a `Name` field from
what is an object containing an `OutageItems` list. A blocking `requests` call
ran inside the event loop.

Two behaviours worth knowing about, both found by testing against live data:

- Tauron reuses a single `OutageId` for separate time slots of the same works,
  so occurrences are keyed by id *and* start time.
- Outage descriptions can exceed the 255-character state limit (264 observed),
  so the description sensor truncates its state and keeps the complete text in
  the `full_description` attribute.

[0.3.0]: https://github.com/Eales/tauron-dystrybucja/releases/tag/v0.3.0
