# NOIR ATELIER — N°01

Interactive 3D prototype (One Motion Bloom).

## Public (Live)

- `index.html` — Produktmodell → https://noir-atelier.com
- `cnc/` — nur Metallgehäuse (CNC) → https://cnc.noir-atelier.com

Deployed via Vercel. Subdomain `cnc.noir-atelier.com` rewrite → `/cnc/` (siehe `vercel.json`).

## Local

```bash
cd ~/Desktop/noir-atelier
python3 -m http.server 8765
```

- Produktmodell: http://localhost:8765  
- Interne Previews (nicht öffentlich, via `.vercelignore` ausgeschlossen):  
  http://localhost:8765/preview/
