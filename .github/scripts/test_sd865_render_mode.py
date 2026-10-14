"""Compile the candidate's actual A650 predicate; no GPU performance claim."""
import argparse,json,re,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);a=p.parse_args()
s=a.source.read_text()
m=re.search(r'static bool\s+tu_sd865_sysmem_screen\(uint32_t gpu_id\)\s*\{.*?\n\}',s,re.S)
if not m:print('A650 SYSMEM candidate absent');raise SystemExit(2)
assert 'tu_sd865_sysmem_screen(fd_dev_gpu_id(&cmd->device->physical_device->dev_id))' in s
assert 'SD865 experimental forced SYSMEM' in s
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'gate.cpp';o=Path(d)/'gate'
 f.write_text('#include <cstdint>\n#include <cassert>\n'+m.group()+'\nint main(){assert(tu_sd865_sysmem_screen(650));for(unsigned id:{618u,630u,640u,660u,740u,830u})assert(!tu_sd865_sysmem_screen(id));}\n')
 # Range initializer requires its standard declaration explicitly.
 f.write_text('#include <initializer_list>\n'+f.read_text())
 subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror',str(f),'-o',str(o)],check=True)
 subprocess.run([str(o)],check=True)
print(json.dumps({'a650':'forced_sysmem','other_gpus':'unchanged','scope':'Compiled actual predicate and source wiring; not GPU correctness/FPS'}))
