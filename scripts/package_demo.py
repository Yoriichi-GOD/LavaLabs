"""Package exactly the attributed Nepal demonstration and full frozen graph.

Large original graph files are compressed, never truncated or resealed. This
script runs only against the project-owned retained inputs and copies no keys.
"""
from pathlib import Path
import hashlib,json,zipfile

ROOT=Path(__file__).resolve().parents[1]

def digest(path):
 with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def package():
 files={}
 def add(path,expected=None,role='saved demonstration'):
  path=path.resolve()
  if not path.is_relative_to(ROOT) or not path.is_file():raise ValueError('Missing/outside project input '+str(path))
  key=path.relative_to(ROOT).as_posix()
  if path.name.startswith('.env') or path.suffix in {'.key','.pem'}:raise ValueError('Credential material is never a demo input')
  checksum=digest(path)
  if expected and checksum!=expected:raise ValueError('Historical evidence changed: '+key)
  files[key]={'sha256':checksum,'bytes':path.stat().st_size,'role':role}
 for run in ['event-fe47db331390','nepal-syapru-004']:
  folder=ROOT/'components/floodlab/artifacts/runs'/run
  freeze=json.loads((folder/'freeze.json').read_text())
  add(folder/'freeze.json',role='original freeze')
  for name,checksum in freeze['files'].items():
   if Path(name).name!=name:raise ValueError('Unsafe frozen member')
   add(folder/name,checksum,'Sentinel/OSM saved observation, not new accuracy evidence')
  result=json.loads((folder/'result.json').read_text())
  debris=result.get('provenance',{}).get('debris',{})
  for date,checksum in debris.get('source_hashes',{}).items():
   candidates=[ROOT/'components/floodlab/data/automatic'/run/'optical'/date/'default.tif',ROOT/'components/floodlab/data/optical'/date/'default.tif']
   path=next((path for path in candidates if path.is_file() and digest(path)==checksum),None)
   if path:add(path,checksum,'retained optical RGB/index source; Sentinel attribution retained')
 terrain_root=ROOT/'.runtime/jai/terrain'
 for folder in sorted(terrain_root.glob('terrain-*')):
  scene=json.loads((folder/'scene.json').read_text());add(folder/'scene.json',role='original terrain scene metadata')
  for name,checksum in scene['hashes'].items():add(folder/name,checksum,'Copernicus GLO-90 historical DSM')
 folder=ROOT/'.runtime/research-release/terrain-exposure/terrain-exposure-nepal-glo30'
 manifest=json.loads((folder/'manifest.json').read_text());add(folder/'manifest.json',role='original scientific replay manifest')
 for name,checksum in manifest['files'].items():
  if Path(name).name!=name:raise ValueError('Unsafe replay member')
  add(folder/name,checksum,'full Copernicus/OSM terrain-evidence replay; static screening model')
 destination=ROOT/'data/demo';destination.mkdir(parents=True,exist_ok=True)
 archive=destination/'nepal-evidence.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as output:
  for name in sorted(files):output.write(ROOT/name,name)
 if archive.stat().st_size>95*1024*1024:raise ValueError('Demo archive exceeds the ordinary-Git packaging budget')
 record={'schema':1,'archive':archive.name,'archive_sha256':digest(archive),'archive_bytes':archive.stat().st_size,'unpacked_bytes':sum(value['bytes'] for value in files.values()),'files':files,'notice':'Original frozen manifests and data bytes are preserved. Code MIT does not relicense Sentinel, Copernicus or OSM data. See DATA_LICENSES.md.'}
 (destination/'manifest.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({key:record[key] for key in ['archive_bytes','unpacked_bytes','archive_sha256']}),flush=True)
 print('Packed',len(files),'original members without changing historical seals',flush=True)

if __name__=='__main__':package()
