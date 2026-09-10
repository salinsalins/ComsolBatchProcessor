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
print(f'Find duplicates in "{file_dir}"')

files = Path(file_dir).rglob('*.mph')
files = list(files)
duplicates = []
print('Total files:')

for file in files:
    size = file.stat().st_size
    print(f'{length:4d} "{file}" {sizes[-1]:_d} bytes')

print('Duplicate files:')
