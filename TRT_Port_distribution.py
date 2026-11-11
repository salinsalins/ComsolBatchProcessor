import logging
import os
import sys
import time

import mph
from open_file import open_directory, open_file
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

t00 = time.time()

# configure logging
LOG_FORMAT_STRING = "%(asctime)s,%(msecs)3d %(levelname)-7s %(filename)s %(funcName)s(%(lineno)s) %(message)s"
LOGGER = logging.getLogger()
log_formatter = logging.Formatter(LOG_FORMAT_STRING, datefmt="%H:%M:%S")
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
LOGGER.addHandler(console_handler)
LOGGER.setLevel(logging.INFO)

print("")
LOGGER.info("TRT entrance port beam properties")
print("")

# select data file
# FILE_DIR = "c://Users//WinAdmin//Documents//2026//Плазменная мишень" 
# FILE_PATH = open_file(initialdir=FILE_DIR, filetypes=[("csv Files", "*.csv")])
# FILE_PATH = "d:\\COMSOL\\TRT\\Beam_Transport\\2026\\Geometry V1\\HEBT\\processed\\520\\HEBT_D_I_9A_U5_400kV_alpha_0.01_1763622902782699972.png" 
FILE_PATH = "d:\\data.txt"
if not FILE_PATH:
    exit(0)
print(f"Selected file: '{FILE_PATH}'")
FILE_DIR = Path(FILE_PATH).parent
os.chdir(FILE_DIR)
print(f"Current dir set to '{os.getcwd()}'")

import numpy as np
import matplotlib.pyplot as plt

data = np.loadtxt(FILE_PATH, comments="%")

i = data[:, 0]
x = data[:, 1]              # mm
y = data[:, 2]              # mm
z = data[:, 3]              # mm
vx = data[:, 4]             # m/s
vy = data[:, 5]             # m/s
vz = data[:, 6]             # m/s

nonnan = ~np.isnan(x)
x = x[nonnan]
y = y[nonnan]
z = z[nonnan]
vx = vx[nonnan]
vy = vy[nonnan]
vz = vz[nonnan]

# rotate to angle of single line injection
fi0 = 1.5 / 180. * np.pi # 1.5 degreese
cfi = np.cos(fi0)
sfi = np.sin(fi0)
z0 = 12690.          # mm

z2 = z - z0

x3 = x*cfi - z2*sfi
z3 = z2*cfi + x*sfi

z4 = z3 + z0
x4 = x3
y4 = y

vx4 = vx*cfi - vz*sfi
vz4 = vz*cfi + vx*sfi
vy4 = vy


# plot raw data
# plt.figure(figsize=(8, 5))
# plt.scatter(x, y)
# plt.xlabel("X, mm")
# plt.ylabel("Y, mm")
# plt.title("Initial data at last t")
# plt.grid(True, linestyle="--", alpha=0.6)
# plt.legend()
# plt.show()
# plt.cla()

# recalculate to z = z0
# z0 = z0 - 4000.       # uncomment for  port enrance
dt = (z4 - z0) / vz4
x5 = x4 - vx4 * dt 
y5 = y4 - vy4 * dt 
z5 = z4 - vz4 * dt 

# filter passed to plasma
passed = np.where(z >= (z0 + 1.))
x = x5[passed]
y = y5[passed]
z = z5[passed]
vx = vx4[passed]
vy = vy4[passed]
vz = vz4[passed]

# plt.figure(figsize=(8, 5))
# plt.scatter(x, y)
# plt.scatter(x1, y1)
# plt.xlabel("X, mm")
# plt.ylabel("Y, mm")
# plt.title("At plasma entrance (orange)")
# plt.grid(True, linestyle="--", alpha=0.6)
# plt.legend()
# plt.show()

n_bins = 20

plt.figure(figsize=(8, 5))
plt.hist(x5, bins=n_bins)
xcounts, xbins = np.histogram(x5, bins=n_bins)
# plt.stairs(counts, bins, fill=True) # plt.stairs отлично подходит для готовых bins/counts
pxbins = (xbins[1:] + xbins[:-1])/2.
plt.plot(pxbins, xcounts)
plt.xlabel("X, mm")
plt.ylabel("Count")
plt.title("X profile")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.show(block=False)

plt.figure(figsize=(8, 5))
plt.hist(y5, bins=n_bins, density=True)
ycounts, ybins = np.histogram(y5, bins=n_bins, density=True)
# plt.stairs(counts, bins, fill=True) # plt.stairs отлично подходит для готовых bins/counts
pybins = (ybins[1:] + ybins[:-1])/2.
plt.plot(pybins, ycounts)
plt.xlabel("Y, mm")
plt.ylabel("Count")
plt.title("Y profile")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.show(block=False)

data1 = np.column_stack((x5, y5, z5-z0, vx4, vy4, vz4))

comment_lines = "Coordinates and velocities of D0 atoms at the entarance palne\nx, mm; y, mm; z, mm; vx, m/s; vy, m/s; vz, m/s"

np.savetxt("d:\\result.txt", data1, delimiter="; ", header=comment_lines)

pass
