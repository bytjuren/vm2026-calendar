[README.md](https://github.com/user-attachments/files/28707563/README.md)
# Fotbolls-VM 2026 kalender - TV4/SVT

Det här paketet skapar en prenumererbar iCal-kalender från TV4:s pressida:

https://press.tv4.se/post/fotbollsfeber-hela-sommaren-sa-sands-fotbolls-vm-2026-pa-tv4

## Vad du får

- `update_calendar.py` hämtar TV4-sidan och bygger `docs/fotbolls-vm-2026-tv4-svt.ics`.
- `.github/workflows/update-calendar.yml` ger dig en knapp i GitHub Actions: **Run workflow**.
- `docs/` kan publiceras via GitHub Pages så kalendern får en fast URL.

## Steg för GitHub Pages

1. Skapa ett nytt publikt GitHub-repo, till exempel `vm2026-calendar`.
2. Ladda upp allt innehåll i den här mappen till repot.
3. Gå till **Settings → Pages**.
4. Under **Build and deployment**, välj:
   - Source: `Deploy from a branch`
   - Branch: `main`
   - Folder: `/docs`
5. Spara.

Efter någon minut får du en URL ungefär så här:

```text
https://DIN-GITHUB-ANVANDARE.github.io/vm2026-calendar/fotbolls-vm-2026-tv4-svt.ics
```

Prenumerera på den URL:en i Apple Kalender, Google Calendar eller Outlook.

## Automatisk uppdatering

Workflowet kör automatiskt var 30:e minut med GitHub Actions och hämtar TV4-sidan igen. Kalenderfilen skrivs över på samma URL när data ändras.

## Viktigt

Kalenderappar bestämmer själva hur ofta de hämtar en prenumererad ICS-fil. Scriptet sätter `X-PUBLISHED-TTL:PT6H`, men Apple/Google/Outlook kan ändå cacha enligt egna regler.

Workflow-filen är inställd på automatisk körning var 30:e minut. Det finns ingen manuell `Run workflow`-knapp eftersom `workflow_dispatch` är borttaget.
