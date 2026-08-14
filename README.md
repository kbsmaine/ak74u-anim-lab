# AKS-74U REAL Magazine Payload Extractor

This is the next extraction step for the AKS-74U browser conversion.

It targets the **actual** Marketplace asset:

`SM_AKS74U_Magazine.uasset`

The package metadata reports **638 vertices / 636 triangles / 2 UV channels**. The actual editor `FMeshDescription` is stored in the package trailer as an Oodle/Kraken-compressed payload, so the ordinary UAssetGUI JSON dump only exposed the payload reference rather than the vertex buffer.

## Run it

1. Create a GitHub repo (or replace the files in the temporary AK extraction repo).
2. Upload the **contents** of this folder.
3. Open **Actions**.
4. Select **Extract REAL AKS-74U Magazine Payload**.
5. Click **Run workflow**.
6. When it completes, download the artifact named:

`aks74u-real-mag-payload`

7. Upload that artifact ZIP back to ChatGPT.

## What the action does

It locates the original Unreal `FCompressedBuffer` inside the `.uasset`, installs the Kraken decompressor on GitHub's Linux runner, decompresses the original payload, verifies the expected **154,805-byte** result, and uploads:

- `SM_AKS74U_Magazine_MeshDescription.bin` — the original decompressed Unreal mesh-description bytes
- `SM_AKS74U_Magazine_FCompressedBuffer.bin` — the original compressed buffer
- `meshdescription_strings.txt` — diagnostics useful for decoding the self-describing mesh attributes
- `report.json`
- `extraction.log`

This does **not** generate another replacement magazine. The output is the real source payload needed to reconstruct the exact mesh and attach it to the authored `Magazine_CONTROL` animation.
