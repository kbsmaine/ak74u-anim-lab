#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'vendor/CUE4Parse')

# 1) Linux-safe output paths.
p = root / 'CUE4Parse-Conversion' / 'ExportSession.cs'
s = p.read_text(encoding='utf-8-sig')
old = "return fullPath.Replace('/', '\\\\');"
new = "return OperatingSystem.IsWindows() ? fullPath.Replace('/', '\\\\') : fullPath;"
if old in s:
    s = s.replace(old, new)
elif new not in s:
    raise SystemExit(f'Could not locate ExportSession path-normalization line in {p}')
p.write_text(s, encoding='utf-8')
print('Patched Linux-safe ExportSession output paths')

# 2) Force ACL-safe decoding when UE5.5 loose Marketplace animation assets
# reference an ACL plugin settings object that is not included with the project.
# In this pack the .uassets explicitly reference /ACLPlugin/ACLAnimBoneCompressionSettings,
# but the DDC handle can serialize as an empty string. Therefore checking only the
# handle for "ACL" is not sufficient. If the requested codec cannot be resolved and
# an animation byte stream exists, use CUE4Parse's ACL-safe decoder.
p = root / 'CUE4Parse' / 'UE4' / 'Assets' / 'Exports' / 'Animation' / 'UAnimSequence.cs'
s = p.read_text(encoding='utf-8-sig')
old = '''            var boneCompressionCodec = BoneCompressionSettings?.Load<UAnimBoneCompressionSettings>()?.GetCodec(BoneCodecDDCHandle);
            if (boneCompressionCodec != null)
            {
                CompressedDataStructure = boneCompressionCodec.AllocateAnimData();
                CompressedDataStructure.SerializeCompressedData(Ar);
                CompressedDataStructure.Bind(serializedByteStream);
                NumFrames = CompressedDataStructure.CompressedNumberOfFrames;
            }
            else
            {
                Log.Warning("Unknown bone compression codec {0}", BoneCodecDDCHandle);
            }'''
new = '''            var boneCompressionCodec = BoneCompressionSettings?.Load<UAnimBoneCompressionSettings>()?.GetCodec(BoneCodecDDCHandle);
            if (boneCompressionCodec != null)
            {
                CompressedDataStructure = boneCompressionCodec.AllocateAnimData();
                CompressedDataStructure.SerializeCompressedData(Ar);
                CompressedDataStructure.Bind(serializedByteStream);
                NumFrames = CompressedDataStructure.CompressedNumberOfFrames;
            }
            else if (serializedByteStream.Length > 0)
            {
                // This Marketplace pack was authored with the ACL plugin, but loose
                // editor assets don't ship /ACLPlugin/ACLAnimBoneCompressionSettings.
                // The DDC handle may also be blank in UE5.5, so don't key the fallback
                // off the handle string. The stream itself is still present.
                Log.Warning("Bone codec unavailable ({0}); forcing ACL-safe decoder for loose UE5.5 animation", BoneCodecDDCHandle);
                CompressedDataStructure = new UAnimBoneCompressionCodec_ACLSafe().AllocateAnimData();
                CompressedDataStructure.SerializeCompressedData(Ar);
                CompressedDataStructure.Bind(serializedByteStream);
                NumFrames = CompressedDataStructure.CompressedNumberOfFrames;
            }
            else
            {
                Log.Warning("Unknown bone compression codec {0}", BoneCodecDDCHandle);
            }'''
# support previous patched form too
if old in s:
    s = s.replace(old, new)
else:
    start = s.find('            var boneCompressionCodec = BoneCompressionSettings?.Load<UAnimBoneCompressionSettings>()?.GetCodec(BoneCodecDDCHandle);')
    end_marker = '                Log.Warning("Unknown bone compression codec {0}", BoneCodecDDCHandle);\n            }'
    end = s.find(end_marker, start)
    if start >= 0 and end >= 0:
        end += len(end_marker)
        s = s[:start] + new + s[end:]
    elif 'forcing ACL-safe decoder for loose UE5.5 animation' not in s:
        raise SystemExit(f'Could not locate compression-codec block in {p}')
p.write_text(s, encoding='utf-8')
print('Patched unconditional ACL-safe fallback for this loose UE5.5 Marketplace pack')
