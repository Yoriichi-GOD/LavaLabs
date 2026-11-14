"""Restore only hash-identified demo members inside this independent project.

No network, original-app access, deletion, shared links or credential copying.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,zipfile

ROOT=Path(__file__).resolve().parents[1]

def digest(path):
 with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def contained(name,root=ROOT):
 destination=(root/name).resolve()
 if Path(name).is_absolute() or '\\' in name or not destination.is_relative_to(root.resolve()):raise ValueError('Archive member escapes the project')
 allowed=('.runtime/jai/terrain/','.runtime/research-release/terrain-exposure/','components/floodlab/artifacts/runs/','components/floodlab/data/optical/','components/floodlab/data/automatic/')
 if not name.startswith(allowed):raise ValueError('Archive member is outside the demo data stores')
 return destination

def bootstrap(verify=False):
 folder=ROOT/'data/demo';manifest_path=folder/'manifest.json'
 if not manifest_path.is_file():raise FileNotFoundError('Bundled demo is missing; restore data/demo from the LavaLabs repository.')
 manifest=json.loads(manifest_path.read_text());archive_name=manifest['archive'];records=manifest['files']
 if Path(archive_name).name!=archive_name or '\\' in archive_name:raise ValueError('Invalid demo archive name')
 archive=folder/archive_name
 missing=[name for name,metadata in records.items() if not contained(name).is_file() or contained(name).stat().st_size!=metadata['bytes']]
 if missing:
  if digest(archive)!=manifest['archive_sha256']:raise ValueError('Bundled demo archive checksum mismatch')
  with zipfile.ZipFile(archive) as source:
   members={item.filename:item for item in source.infolist()}
   if len(members)!=len(source.infolist()) or set(members)!=set(records) or sum(item.file_size for item in members.values())>1024**3:raise ValueError('Unexpected demo archive members or size')
   for name in missing:
    target=contained(name);metadata=records[name];item=members[name]
    if ((item.external_attr>>16)&0o170000)==0o120000 or item.file_size!=metadata['bytes']:raise ValueError('Unsafe archive member')
    if target.exists():raise FileExistsError('Refusing to overwrite differing local evidence: '+name)
    target.parent.mkdir(parents=True,exist_ok=True);partial=target.with_name(target.name+'.lava-part')
    with source.open(item) as incoming,partial.open('wb') as outgoing:shutil.copyfileobj(incoming,outgoing,1024*1024)
    if digest(partial)!=metadata['sha256']:raise ValueError('Extracted member checksum mismatch')
    os.replace(partial,target)
 if verify:
  for name,metadata in records.items():
   if digest(contained(name))!=metadata['sha256']:raise ValueError('Retained evidence changed: '+name)
 print(f'LavaLabs demo ready: {len(records)} contained members; restored {len(missing)}; full verification {verify}',flush=True)
 return manifest

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');options=parser.parse_args();bootstrap(options.verify)
