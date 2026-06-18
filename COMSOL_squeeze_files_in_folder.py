import sys

import mph
from open_file import open_directory
from pathlib import Path

def except_info(prefix='Exception:'):
    exc_type, exc_value, exc_traceback = sys.exc_info()
    return f'{prefix} {exc_type} {exc_value}'

def named_int(value: int, tol=3):
    avalue = abs(value)
    sign = " " if value >= 0 else "-"
    if avalue > 1e9:
        return f'{sign}{avalue/1.e9:.{tol}g}G'
    if avalue > 1e6:
        return f'{sign}{avalue/1.e6:.{tol}g}M'
    if avalue > 1e3:
        return f'{sign}{avalue/1.e3:.{tol}g}k'
    return f'{value:{tol+3}d}'

# select folder
init_dir = 'e:\\COMSOL\\TRT\\Beam_Transport\\2026\\Geometry V1'
file_dir = open_directory(initialdir=init_dir)
print(f'Selected folder to squeeze COMSOL files "{file_dir}"')

recur = False
key = input('Press Y<CR> to recursive folder processing ')
if key == 'Y':
    recur = True

print('Files will be squeezed:')
if recur:
    files = Path(file_dir).rglob('*.mph')
else:
    files = Path(file_dir).glob('*.mph')
length = 0
size_in_bytes = 0
files = list(files)
sizes = []
for file in files:
    length += 1
    sizes.append(file.stat().st_size)
    size_in_bytes += sizes[-1]
    print(f'{length:4d} "{file}" {sizes[-1]:_d} bytes')

if length <= 0:
    print('No *.mph files found')
    exit(1)

print(f'Total {size_in_bytes:_d} bytes')

key = input('Press Y<CR> to Squeeze files ')
if key != 'Y':
    print(key, ' - Processing canceled')
    exit(2)

print('Starting mph wrapper ...')
CLIENT = mph.start()

n = 0
new_sizes = []
new_size_in_bytes = 0
for file in files:
    print(f'{n+1:4d} Squeezing "{file}" ...')
    try:
        MODEL = CLIENT.load(file)
        MODEL.clear()
        MODEL.save()
        CLIENT.remove(MODEL)
        CLIENT.clear()
        new_size = file.stat().st_size
        new_sizes.append(new_size)
        new_size_in_bytes += new_size
        print(f'{sizes[n]:_d} -> {new_size:_d} {(sizes[n] - new_size):_d} bytes')
        n += 1
    except:
        print(except_info(f'Error processing file "{file}"'))
print(n, 'files processed')
print(f'Resulting total {new_size_in_bytes:_d} bytes')
print(f'{named_int(size_in_bytes - new_size_in_bytes):_d} bytes squeezed')
