# Tauron Dystrybucja Integration

Home Assistant integration that reports planned and unplanned power outages for a
single address, using the public Tauron Dystrybucja web API.

## Installation

### HACS

Search for **Tauron Dystrybucja** in HACS and install it, then restart Home
Assistant.

Until the integration is listed in the HACS default catalogue, add it as a
custom repository: HACS > three-dot menu > `Custom repositories`, URL
`https://github.com/Eales/tauron-dystrybucja`, category `Integration`.

### Manual

Copy `custom_components/tauron_dystrybucja` into your Home Assistant `config`
directory and restart Home Assistant.

## Configuration

1. Go to `Settings` > `Devices & Services` > `Add Integration`.
2. Search for `Tauron Dystrybucja`.
3. Enter at least 3 characters of the city name, then pick your city from the list.
4. Enter at least 3 characters of the street name, then pick your street.
5. Enter your house number.

You can add the integration multiple times to monitor several addresses.

### Polling interval

The API is polled every **60 minutes** by default. Change it under the
integration's `Configure` button (allowed range: 15–1440 minutes).

Tauron announces planned outages days in advance, so polling more often gains
almost nothing. One address at the default interval is ~24 requests per day.

## Entities

Each address creates one device. Every fact about the relevant outage - the
ongoing one, or the next one if none is running - is its own entity, so it can
be placed on a dashboard directly, without templates.

| Entity | Type | Description |
| --- | --- | --- |
| `Status` | sensor (`enum`) | `No outages` / `Outage announced` / `Outage in progress`. The one to look at first. |
| `Outage start` | timestamp sensor | When it starts. |
| `Outage end` | timestamp sensor | When it ends. |
| `Duration` | sensor (`duration`, hours) | How long it lasts. |
| `Outage description` | sensor | Tauron's description. Truncated at 255 characters, the state limit; the `full_description` attribute always holds the complete text. |
| `Announced outages` | sensor | Number of outages in the next 30 days. Attribute `outages` holds the full list. |
| `Power outages` | calendar | Every outage as a calendar event. Supports calendar triggers with an offset. |
| `New outage` | event | Fires once when Tauron announces an outage that was not known before. |
| `Outage in progress` | binary sensor (`problem`) | `on` while an outage is ongoing. |

The four `Outage *` sensors also carry `start`, `end` and `description` as flat
attributes, so an Entities card with `type: attribute` rows works without any
templating.

## Dashboards

### Built-in cards (no templating)

The simplest readable view is the standard **Calendar** card pointed at the
calendar entity - it shows outages in a month or week grid, with the full
description on click:

```yaml
type: calendar
entities:
  - calendar.tauron_twoj_adres_wylaczenia_pradu
```

For a compact summary, a plain **Entities** card over the dedicated sensors:

```yaml
type: entities
title: Wyłączenia prądu
entities:
  - sensor.tauron_twoj_adres_status
  - sensor.tauron_twoj_adres_poczatek_wylaczenia
  - sensor.tauron_twoj_adres_koniec_wylaczenia
  - sensor.tauron_twoj_adres_czas_trwania
  - sensor.tauron_twoj_adres_opis_wylaczenia
```

### Markdown card (all outages at once)

The cards above show the next outage. To render *every* announced outage in one
block, this Markdown card reads the whole list from the counter sensor's
attributes. It needs **one entity ID replaced** - take yours from
`Developer tools` > `States`.

```yaml
type: markdown
content: |
  {% set encja = 'sensor.tauron_twoj_adres_zapowiedziane_wylaczenia' %}
  {% set dni = ['poniedziałek','wtorek','środa','czwartek','piątek','sobota','niedziela'] %}
  {% set lista = state_attr(encja, 'outages') or [] %}
  ## ⚡ Wyłączenia prądu
  {% if lista | count == 0 %}
  Brak zapowiedzianych wyłączeń na najbliższe 30 dni.
  {% else %}
  {% for o in lista %}
  {% set s = o.start if o.start is not string else as_datetime(o.start) %}
  {% set k = o.end if o.end is not string else as_datetime(o.end) %}
  {% set s = s | as_local %}
  {% set k = k | as_local %}
  {% set ile = (s.date() - now().date()).days %}
  {% if s <= now() and now() <= k %}
  ### 🔴 Trwa teraz — do {{ k.strftime('%H:%M') }}
  {% else %}
  ### {{ dni[s.weekday()] }} {{ s.strftime('%d.%m') }}, {{ s.strftime('%H:%M') }}–{{ k.strftime('%H:%M') }}
  {% if ile == 0 %}dzisiaj{% elif ile == 1 %}jutro{% elif ile == 2 %}pojutrze{% else %}za {{ ile }} dni{% endif %}
  {% endif %}

  {{ o.description }}
  {% if not loop.last %}

  ---
  {% endif %}
  {% endfor %}
  {% endif %}
```

Renders as:

```
## ⚡ Wyłączenia prądu

### poniedziałek 20.07, 08:00–16:00
pojutrze

Przykładowa ulica 2 do 6, 3 do 7, 11, 15 do 29, Inna 4 do 6,
Kolejna 3 do 7, Następna 1, 5, działka Nr 000/0.
```

## Automations

The integration deliberately does not send any notifications by itself - it only
exposes standard Home Assistant entities. The examples below are starting points;
change the offset, the notify service and the message to whatever suits you.

Two triggers are available, answering different questions:

- **event entity** - "Tauron has just announced a new outage" (usually days ahead).
- **calendar trigger with an offset** - "the outage starts soon", with the lead
  time you choose.

### Example: notify as soon as a new outage is announced

```yaml
automation:
  - alias: "Tauron - new outage announced"
    triggers:
      - trigger: state
        entity_id: event.tauron_twoj_adres_nowe_wylaczenie
    conditions:
      - condition: template
        value_template: "{{ trigger.to_state.state not in ['unknown', 'unavailable'] }}"
    actions:
      - action: notify.persistent_notification
        data:
          title: "Uwaga - planowane wyłączenie prądu"
          message: >-
            {{ trigger.to_state.attributes.start | as_datetime | as_local
               | as_timestamp | timestamp_custom('%d.%m %H:%M') }}
            - {{ trigger.to_state.attributes.end | as_datetime | as_local
               | as_timestamp | timestamp_custom('%H:%M') }}
            {{ trigger.to_state.attributes.description }}
```

### Example: remind before the outage starts

`offset` sets how far ahead you are warned - `-02:00:00` is two hours, use
`-1 day, 0:00:00` for a day ahead, or any other value.

```yaml
automation:
  - alias: "Tauron - outage starting soon"
    triggers:
      - trigger: calendar
        entity_id: calendar.tauron_twoj_adres_wylaczenia_pradu
        event: start
        offset: "-02:00:00"
    actions:
      - action: notify.persistent_notification
        data:
          title: "Wkrótce nie będzie prądu"
          message: "{{ trigger.calendar_event.description }}"
```

Replace the entity IDs with the ones created for your address (visible under
`Developer tools` > `States`). Anything else Home Assistant can trigger on works
too - the calendar entity is a normal calendar, so it also appears in the
Calendar panel and in dashboard cards.

## Notes

- **Always read the outage description.** Tauron matches outages to an address by
  area, and the `description` text lists the streets actually affected - which may be
  streets other than yours. An outage returned for your address does not
  guarantee your address loses power. The description is the only way to tell,
  which is why the card above shows it in full.
- The Tauron API requires a street to be selected, so addresses in localities
  without named streets are not supported by the upstream API.
- The `New outage` event stays silent on the first refresh after a restart, so
  restarting Home Assistant does not replay outages you already knew about.
