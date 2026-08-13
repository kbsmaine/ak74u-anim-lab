# AKS-74U Actual UE Browser Tester

This tester was built from the supplied UE5.5 editor JSON dump, using the same editor-curve approach that succeeded on the M4A1 pack.

## What is real from the AK pack
- `SK_AK74U` source geometry: 13,361 vertices / 12,837 triangles
- AK weapon controls: root, grip, trigger, bolt and magazine
- all 14 `A_FP_AKS74U_*` first-person authored animation clips
- weapon-side reload/fire Control Rig curves
- tactical reload and empty reload are paired with their matching weapon animation

## Arms
The visible arm mesh is the already-recovered actual UE first-person arms mesh from the M4 workflow. The AK pack's UE5 Manny Control Rig uses matching UE5 bone/control names, so all 89 AK arm controls are baked directly onto this skeleton with no Mixamo approximation.

## Magazine note
The AK pack stores the magazine as a separate `SM_AKS74U_Magazine` editor static mesh. Its source bulk mesh bytes were not serialized into this JSON artifact, so this first browser build uses a generated magazine proxy attached to the **real authored Magazine control**. The AK rifle body, bolt, trigger, arm motion and weapon motion are from the source assets.

## Controls
- R: tactical reload
- Shift+R: empty reload
- F: fire
- E: equip
- Space: play/pause
- mouse drag/wheel: orbit/zoom


MAGAZINE UPDATE
- Replaced the old staircase placeholder with a cleaner curved AK-style magazine proxy attached to the real authored Magazine_CONTROL animation.
- The original static mesh vertex payload for SM_AKS74U_Magazine still was not present in the editor JSON dump, so this is a visual proxy, not the exact marketplace magazine geometry.
