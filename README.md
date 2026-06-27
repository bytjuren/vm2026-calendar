# Fotbolls-VM 2026 kalender - Svensk Fotboll, avsparkstid

Den här versionen använder Svensk Fotbolls sida som källa:

https://www.svenskfotboll.se/nyheter/landslag/2026/05/sa-sands-vm/

## Viktigt

- Kalenderfilen heter fortfarande `docs/fotbolls-vm-2026-tv4-svt.ics`.
- Titlarna har samma stil som tidigare: `🇲🇽Mexiko - 🇸🇪Sverige (TV4)`.
- Händelserna startar vid avspark och är 15 minuter långa.
- Scriptet använder samma UID-format som tidigare TV4-version för att undvika dubbletter i kalenderprenumerationen.

## Uppdatering

Workflowet kör automatiskt var 30:e minut:

```yaml
schedule:
  - cron: "*/30 * * * *"
```

## Behåll samma prenumerationslänk

Om ditt repo heter `vm2026-calendar` och användaren är `bytjuren` ska kalenderlänken fortsätta vara:

```text
https://bytjuren.github.io/vm2026-calendar/fotbolls-vm-2026-tv4-svt.ics
```
