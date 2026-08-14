# AKS-74U Actual UE Browser Tester — REAL Magazine Build

This build replaces the temporary magazine proxy with the **actual `SM_AKS74U_Magazine` mesh data recovered from the original UE5.5 package payload**.

## What is real from the AK pack
- `SK_AK74U` source geometry: 13,361 vertices / 12,837 triangles
- `SM_AKS74U_Magazine` original `FMeshDescription` geometry
- magazine source mesh: 615 source vertices / 1,908 vertex instances / 636 triangles
- original magazine normals and UV0
- AK weapon controls: root, grip, trigger, bolt and magazine
- all 14 `A_FP_AKS74U_*` first-person authored animation clips
- weapon-side reload/fire Control Rig curves
- tactical reload and empty reload paired with their matching weapon animation

Unreal's asset-registry metadata reports 638 render vertices for the magazine. The decoded source `FMeshDescription` contains 615 unique position vertices and 1,908 vertex instances; render-time splits at normal/UV seams account for the differing render-vertex count.

## Magazine extraction
The original `SM_AKS74U_Magazine.uasset` contained an Oodle/Kraken-compressed package payload. It was decompressed to 154,805 bytes and the `FMeshDescription` attributes were decoded directly:
- `Position`
- `VertexIndex`
- `TextureCoordinate`
- `Normal`
- triangle `VertexInstanceIndex`

Those real vertices are now skinned to the existing AK `Magazine` joint and therefore follow the authored `Magazine_CONTROL` motion during tactical and empty reloads. **No proxy magazine remains.**

## Arms
The visible arm mesh is the already-recovered actual UE first-person arms mesh used by the M4 workflow. The AK pack's UE5 Manny Control Rig uses matching UE5 bone/control names, so the AK arm curves are baked directly onto that skeleton.

## Controls
- R: tactical reload
- Shift+R: empty reload
- F: fire
- E: equip
- Space: play/pause
- mouse drag/wheel: orbit/zoom
