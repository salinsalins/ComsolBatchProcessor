import sys
import time

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
        return f'{sign}{avalue/1.e9:.{tol}g} G'
    if avalue > 1e6:
        return f'{sign}{avalue/1.e6:.{tol}g} M'
    if avalue > 1e3:
        return f'{sign}{avalue/1.e3:.{tol}g} k'
    return f'{value:{tol+3}d}'

def nice_time(value):
    outstr = ''
    days = int(value / 60. / 60. / 24.)
    if days > 0 :
        outstr = f'{days} days '
        value -= days * 60. * 60. * 24.
    hours = int(value / 60. / 60.)
    if hours > 0 :
        outstr += f'{hours} hours '
        value -= hours * 60. * 60.
    minutes = int(value / 60.)
    if minutes > 0 :
        outstr += f'{minutes} minutes '
        value -= minutes * 60.
    seconds = int(value)
    if outstr and seconds > 0 :
        return outstr + f'{seconds} seconds'
    if outstr:
        return outstr
    return 'less than 1 second'

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

print(f'Total {named_int(size_in_bytes)} bytes in {len(files)} files')

key = input(f'Press Y<CR> to Squeeze {len(files)} files ')
if key != 'Y':
    print(key, ' - Processing canceled')
    exit(2)

print('Starting mph wrapper ...')
CLIENT = mph.start()

t0 = time.time()
n = 0
n_total = 0
n_errors = 0
new_sizes = []
new_size_in_bytes = 0
porocessed_in_bytes = 0
for file in files:
    n_total += 1
    print(f'{n_total:4d} of {len(files):4d}')
    print(f'Squeezing "{file}" ...')
    try:
        MODEL = CLIENT.load(file)
        MODEL.clear()
        MODEL.save()
        CLIENT.remove(MODEL)
        CLIENT.clear()
        new_size = file.stat().st_size
        new_sizes.append(new_size)
        new_size_in_bytes += new_size
        porocessed_in_bytes += sizes[n]
        print(f'{sizes[n]:_d} -> {new_size:_d}; removed {named_int(sizes[n] - new_size)} bytes')
        print(f'{int(porocessed_in_bytes * 100. / size_in_bytes):_d}% completed {nice_time(time.time()-t0)} elapsed')
        n += 1
    except:
        n_errors += 1
        print(except_info(f'Error processing file "{file}"'))
print(f'Resulting:')
print(n, 'files processed OK,', n_errors, 'with errors.')
print(f'Total {named_int(size_in_bytes)} bytes processed.')
print(f'Total {named_int(new_size_in_bytes)} bytes in result.')
print(f'{named_int(size_in_bytes - new_size_in_bytes)} bytes squeezed.')
print(f'{nice_time(time.time()-t0)} elapsed.')
