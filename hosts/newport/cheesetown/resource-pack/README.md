# Cheesetown resource pack

Katie Hardy's yellow and pink Hube paintings replace `minecraft:backyard` and
`minecraft:pond` (both 3×4), including existing placements. Full artwork is
preserved; attribution is in `CREDITS.txt`.

Rebuild from this directory:

```bash
python -m zipfile -c ../downloads/cheesetown-paintings-1.0.1.zip pack.mcmeta assets CREDITS.txt
sha1sum ../downloads/cheesetown-paintings-1.0.1.zip
```

Update the Compose URL/version and SHA-1 together. Generated ZIPs stay in ignored
`downloads/`. The pack is optional; declining leaves vanilla paintings unchanged.
