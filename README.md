# AKS-74U UE5.5 Editor JSON Dumper

This is the **same extraction route that succeeded on the M4A1 pack** after the CUE4Parse/PSA route failed.

It uses the Windows build of **UAssetGUI/UAssetAPI** to read the uncooked UE5.5 editor assets directly and dump:

- all AKS-74U first-person animation assets (`A_FP_*`)
- AK weapon animation assets (`A_WBP_*`)
- the actual `SK_AK74U` skeletal mesh source data
- the AK skeleton
- the separate AK magazine static mesh
- the supplied `SK_FP_Manny_Simple` first-person mesh
- the UE5 mannequin arms skeleton

## Run it

1. Create a new GitHub repository.
2. Upload the **contents** of this folder to the repository root.
3. Open **Actions**.
4. Select **Dump AKS-74U UE5.5 Editor JSON**.
5. Click **Run workflow**.
6. When it finishes, download the artifact named:

```text
aks74u-ue55-editor-json
```

7. Send that artifact ZIP back to ChatGPT.

## Why this is different from the previous AK lab

The earlier AK test repo retried CUE4Parse's runtime/ActorX animation path. That was the wrong route for this job because these Marketplace files are uncooked editor assets.

This repo instead uses the editor JSON approach that previously exposed the real Sequencer/Control Rig curves and editor mesh source geometry on the M4A1 pack.

Once the artifact is returned, the next step is to bake the actual AKS-74U + FP arms + authored animations into a browser-ready GLB tester, and only after that integrate it into Dead Haul.
