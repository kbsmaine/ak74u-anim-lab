#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, struct, json, re, hashlib

MAGIC = bytes.fromhex('b7756362')

def u32be(b, o): return int.from_bytes(b[o:o+4], 'big')
def u64be(b, o): return int.from_bytes(b[o:o+8], 'big')

def ascii_strings(data: bytes, min_len=4):
    return [m.group().decode('ascii','replace') for m in re.finditer(rb'[ -~]{%d,}' % min_len, data)]

def utf16le_strings(data: bytes, min_len=4):
    out=[]
    # printable ASCII range encoded UTF-16LE
    pat=rb'(?:[ -~]\x00){%d,}' % min_len
    for m in re.finditer(pat,data):
        try: out.append(m.group().decode('utf-16le'))
        except Exception: pass
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('asset')
    ap.add_argument('--out', default='output')
    args=ap.parse_args()
    src=Path(args.asset); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    data=src.read_bytes()
    cb_off=data.find(MAGIC)
    if cb_off < 0:
        raise SystemExit('FCompressedBuffer magic b7756362 not found in package')
    h=data[cb_off:cb_off+64]
    if len(h)<64: raise SystemExit('Truncated FCompressedBuffer header')
    magic=u32be(h,0); crc=u32be(h,4)
    method=h[8]; compressor=h[9]; level=h[10]; block_exp=h[11]
    block_count=u32be(h,12); raw_total=u64be(h,16); compressed_total=u64be(h,24)
    raw_hash=h[32:52].hex(); tail=h[52:64].hex()
    sizes=[]; table_off=cb_off+64
    for i in range(block_count): sizes.append(u32be(data, table_off+i*4))
    block_data_off=table_off+4*block_count

    print('Package:', src)
    print('Package bytes:', len(data))
    print('FCompressedBuffer offset:', cb_off)
    print('magic:',hex(magic),'crc32:',hex(crc))
    print('method:',method,'compressor:',compressor,'level:',level,'blockSizeExponent:',block_exp)
    print('blockCount:',block_count,'rawTotal:',raw_total,'compressedTotal:',compressed_total)
    print('block compressed sizes:',sizes)
    print('raw hash:',raw_hash)

    # kraken-decompressor exposes decompress(src: bytes, dst_len: int) -> bytes
    from kraken_decompressor import decompress
    raw_parts=[]; pos=block_data_off; remaining=raw_total; block_raw_max=1<<block_exp
    for bi,csize in enumerate(sizes):
        block=data[pos:pos+csize]; pos+=csize
        expected=min(block_raw_max, remaining)
        if len(block)!=csize: raise RuntimeError(f'truncated compressed block {bi}')
        dec=decompress(block, expected)
        if len(dec)!=expected:
            raise RuntimeError(f'block {bi}: expected {expected} decoded bytes, got {len(dec)}')
        raw_parts.append(dec); remaining-=len(dec)
        print(f'block {bi}: {csize} -> {len(dec)} bytes')
    raw=b''.join(raw_parts)
    if len(raw)!=raw_total: raise RuntimeError(f'expected rawTotal {raw_total}, got {len(raw)}')

    raw_path=out/'SM_AKS74U_Magazine_MeshDescription.bin'
    raw_path.write_bytes(raw)
    (out/'SM_AKS74U_Magazine_FCompressedBuffer.bin').write_bytes(data[cb_off:pos])
    strings=ascii_strings(raw)+utf16le_strings(raw)
    # stable de-dupe, preserve order
    strings=list(dict.fromkeys(strings))
    (out/'meshdescription_strings.txt').write_text('\n'.join(strings),encoding='utf-8')
    report={
      'sourceFile':src.name,
      'packageBytes':len(data),
      'compressedBufferOffset':cb_off,
      'magic':hex(magic),'crc32':hex(crc),
      'method':method,'compressor':compressor,'level':level,
      'blockSizeExponent':block_exp,'blockCount':block_count,
      'rawTotal':raw_total,'compressedTotal':compressed_total,
      'blockCompressedSizes':sizes,'rawHash':raw_hash,
      'headerTail':tail,
      'decodedSha256':hashlib.sha256(raw).hexdigest(),
      'decodedBytes':len(raw),
      'expectedMeshMetadata':{'vertices':638,'triangles':636,'uvChannels':2,'materials':1},
      'note':'Decoded bytes are the original Unreal FMeshDescription payload for SM_AKS74U_Magazine, not a reconstructed proxy.'
    }
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('WROTE',raw_path, len(raw),'bytes')
    print('SHA256',report['decodedSha256'])
    print('Extracted strings:',len(strings))

if __name__=='__main__': main()
