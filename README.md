# AKS-74U No-Unreal Animation Lab

This repo is designed to let you test the supplied **UE5.5 AKS-74U first-person animation pack without installing Unreal Engine**.

It contains two paths:

1. **Immediate fallback tester** — the known-working fallback GLBs under `site/assets/fallback/` let the site work immediately.
2. **Real AKS-74U animation extraction** — GitHub Actions installs .NET, uses CUE4Parse to read the loose UE5.5 `.uasset` files, exports the AKS-74U first-person animation sequences to ActorX PSA, retargets those real animations onto the browser fallback FP arms + weapon GLBs, and deploys the finished tester to GitHub Pages.

Important note: this repo is focused on getting the **real authored AKS-74U animation motion** into a browser test site first. Because loose UE editor skeletal meshes often do not expose cooked RenderData LODs, the visible browser meshes are still the fallback FP arms / weapon GLBs unless direct mesh export succeeds later.

The Unreal source subset included here is copied from the pack supplied for this project. Only use/distribute it if you have the rights to do so.

## Fastest way to test everything

### 1. Upload this folder to GitHub

Create a new GitHub repository and upload **the contents of this folder**, not another folder wrapped around it. You should see these at the repo root:

```text
.github/
site/
tools/
unreal_source/
README.md
```

### 2. Enable GitHub Pages

Go to:

**Repository → Settings → Pages → Build and deployment → Source → GitHub Actions**

You only need to do this once.

### 3. Run the extractor

Go to:

**Repository → Actions → Extract UE5.5 AKS-74U + Build Test Site → Run workflow**

The workflow will:

```text
UE5.5 loose .uasset files
        ↓
CUE4Parse on GitHub's runner
        ↓
ActorX .psa animation exports
        ↓
Python retarget + GLB writer
        ↓
aks74u_fp_arms.glb + aks74u_weapon.glb
        ↓
GitHub Pages browser tester
```

Even if the UE extraction step fails, the workflow still deploys the test site with the known-working fallback GLBs and uploads extraction logs so the failure can be diagnosed.

### 4. Open the published site

After the workflow deploys, the Pages URL is shown on the workflow run and in **Settings → Pages**.

In the site, the **Asset source** menu will show:

- `Current GLB fallback` — always available.
- `UE5.5 AKS-74U retargeted` — enabled automatically when the real extraction/conversion succeeded.

## Browser controls

| Control | Action |
|---|---|
| `R` | normal reload |
| `Shift + R` | empty/full reload |
| `F` | fire |
| `E` | equip |
| `H` | holster |
| `Space` | play/pause |
| Mouse drag | orbit camera |
| Mouse wheel | zoom |

The panel also provides animation dropdowns, timeline scrubbing, playback speed, loop, wireframe, fit/front/side views, and weapon transform controls.

## Animations targeted from the Unreal pack

The extractor queues the AKS-74U FP animation sequences in the supplied animation folder. That includes the important pairs such as:

```text
A_FP_AKS74U_Idle_Pose
A_FP_AKS74U_Idle_Loop
A_FP_AKS74U_Aim_Pose
A_FP_AKS74U_Aim_Loop
A_FP_AKS74U_Walk_F_Loop
A_FP_AKS74U_Walk_F_Loop_Aimed
A_FP_AKS74U_Run_Loop
A_FP_AKS74U_Fire
A_FP_AKS74U_Fire_Aimed
A_FP_AKS74U_Equipe
A_FP_AKS74U_Reload
A_FP_AKS74U_Reload_Aimed
A_FP_AKS74U_Reload_Empty
A_FP_AKS74U_Reload_Empty_Aimed
A_WBP_AKS74U_Reload
A_WBP_AKS74U_Reload_UnEmpty
A_WBP_Reference_Fire
```

The browser tries to pair arm and weapon clips automatically by their names. You can override both dropdowns manually.

## What gets generated

If extraction succeeds:

```text
site/assets/extracted/aks74u_fp_arms.glb
site/assets/extracted/aks74u_weapon.glb
site/extracted-manifest.json
```

The workflow also saves an Actions artifact named:

```text
actorx-extraction-and-logs
```

That artifact contains the raw PSA exports and logs, useful if a bone or animation needs adjustment.

## Test locally without GitHub Pages

If Python is installed, run from the repo root:

```bash
python -m http.server 8000 --directory site
```

Then open:

```text
http://localhost:8000
```

The fallback source works immediately. The real AKS-74U source appears locally after a successful GitHub extraction if you download/copy the generated `site/assets/extracted/` files and `site/extracted-manifest.json` back into the repo.

## Technical notes

- `tools/Extractor/` is a small .NET command-line program using CUE4Parse/CUE4Parse-Conversion.
- Animations are requested as ActorX PSA.
- `tools/actorx_to_glb.py` reads the real exported PSA clips and writes browser-ready GLB files.
- No Blender or Unreal Engine installation is required for the GitHub workflow.
- This build is focused on verifying the **rig, hands, fingers, reload timing, and weapon motion** first.
- The underlying no-Unreal path still depends on CUE4Parse successfully decoding the UE5.5 loose animation assets on GitHub's Linux runner.
