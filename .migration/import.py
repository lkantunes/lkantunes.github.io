"""Import the approved public portfolio snapshot, checking every file."""
import concurrent.futures
import hashlib
import json
import pathlib
import urllib.parse
import urllib.request

workspace = pathlib.Path.cwd().resolve()
root = (workspace / '_site').resolve()
root.mkdir(exist_ok=True)
manifest = json.loads((workspace / '.migration/manifest.json').read_text())
origin = manifest['origin']
destination = manifest['destination']
text_extensions = {'.html', '.css', '.js', '.xml', '.txt', '.json', '.svg'}

def acquire(item):
    relative = pathlib.PurePosixPath(item['path'])
    if relative.is_absolute() or '..' in relative.parts or relative.parts[0] in {'.git', '.github', '.migration', '.openai'}:
        raise ValueError('Unsafe import path: ' + item['path'])
    target = root.joinpath(*relative.parts)
    request = urllib.request.Request(origin + '/' + urllib.parse.quote(item['path']), headers={'User-Agent': 'PortfolioSnapshotImport/1.0'})
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != item['sha256']:
        raise ValueError('Published file differs from approved snapshot: ' + item['path'])
    if target.suffix in text_extensions:
        data = data.decode('utf-8').replace(origin, destination).encode('utf-8')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return len(data)

first = next(item for item in manifest['files'] if item['path'] == 'index.html')
print('Checking public access to approved snapshot...', flush=True)
acquire(first)
print('Public access confirmed. Importing site files...', flush=True)
pending = [item for item in manifest['files'] if item is not first]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for count, size in enumerate(pool.map(acquire, pending), start=1):
        if count % 100 == 0:
            print('Imported', count + 1, '/', len(manifest['files']), 'files', flush=True)
(root / '.nojekyll').touch()
print('Import complete. Website origin:', destination, flush=True)
