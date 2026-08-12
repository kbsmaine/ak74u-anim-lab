import json, sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'mesh_json')
terms = [
    'MeshDescription', 'MeshDescriptionBulkData', 'SourceModel', 'SourceModels',
    'RawMesh', 'BulkData', 'BulkDataFlags', 'BulkDataSizeOnDisk',
    'Vertices', 'Vertex', 'VertexPositions', 'VertexInstance', 'Triangles',
    'Polygon', 'PolygonGroup', 'Edges', 'UV', 'Normals', 'Tangents',
    'SkinWeight', 'BoneMap', 'Influence', 'LODInfo', 'ImportedModel',
    'SkeletalMeshModel', 'ReferenceSkeleton', 'Materials'
]

def walk(x, path=''):
    if isinstance(x, dict):
        for k, v in x.items():
            p = f'{path}.{k}' if path else str(k)
            yield p, k, v
            yield from walk(v, p)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            p = f'{path}[{i}]'
            yield from walk(v, p)

for fp in sorted(root.glob('*.json')):
    print(f'\n=== {fp.name} ({fp.stat().st_size:,} bytes) ===')
    try:
        data = json.loads(fp.read_text(encoding='utf-8-sig', errors='replace'))
    except Exception as e:
        print('JSON ERROR:', repr(e))
        continue
    hits = []
    for path, key, value in walk(data):
        lk = str(key).lower()
        if any(t.lower() in lk for t in terms):
            desc = type(value).__name__
            if isinstance(value, (str, int, float, bool)) or value is None:
                s = repr(value)
                if len(s) > 180: s = s[:177] + '...'
                desc += ' ' + s
            elif isinstance(value, list):
                desc += f' len={len(value)}'
            elif isinstance(value, dict):
                desc += f' keys={len(value)}'
            hits.append((path, desc))
    print(f'interesting fields: {len(hits)}')
    for p, d in hits[:500]:
        print(f'{p} => {d}')
    if len(hits) > 500:
        print(f'... {len(hits)-500} more hits omitted')
