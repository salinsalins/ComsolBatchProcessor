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
LOGGER.info("Neutralizer nl processing started")
print("")

# select COMSOL file
FILE_DIR = "c://Users//WinAdmin//Documents//2026//Плазменная мишень" 
FILE_PATH = open_file(initialdir=FILE_DIR, filetypes=[("csv Files", "*.csv")])
if not FILE_PATH:
    exit(0)
print(f"Selected file: '{FILE_PATH}'")
FILE_DIR = Path(FILE_PATH).parent
os.chdir(FILE_DIR)
print(f"Current dir set to '{os.getcwd()}'")

import numpy as np
import matplotlib.pyplot as plt

# Reads the CSV and automatically determines data types for each column
# data = np.genfromtxt(FILE_PATH, delimiter=',', dtype=float, skip_header=12, names=False, encoding='utf-8')
data = np.loadtxt(FILE_PATH, delimiter=",", skiprows=12)

x = data[:, 0] * 100.e-6    # ms
y = data[:, 1]              # mV
z = data[:, 2]              # mV

ymax = y.max()
ymin = y.min()
zmax = z.max()
zmin = z.min()

# yc = (y - (ymax + ymin)/ 2.0) / (ymax - ymin) * 2.0
# zc = (z - (zmax + zmin)/ 2.0) / (zmax - zmin) * 2.0
yc = y
zc = z

# smooth data
window_size = 100
window = np.ones(window_size) / window_size
ys = np.convolve(yc, window, mode="valid")
zs = np.convolve(zc, window, mode="valid")
xs = x[window_size-1 : ]

# plot raw data
plt.figure(figsize=(8, 5))
# plt.plot(x, y, linestyle="-", color="b")
plt.plot(xs, ys, label="I")
plt.plot(xs, zs, label="Q")

plt.xlabel("time, ms")
plt.ylabel("Signal, mV")
plt.title("Raw signals")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()

plt.show(block=False)

# plt.cla()

plt.figure(figsize=(8, 5))
plt.plot(xs, np.sqrt(ys*ys + zs*zs), label='Amplitude')
plt.xlabel("time, ms")
plt.ylabel("sqrt(I^2 + Q^2), mV")
plt.title("Amplitude")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.show(block=False)

ays = np.abs(ys)
azs = np.abs(zs)
index1 = np.where(ays > azs)
index2 = np.where(ays <= azs)


at = ys.copy()
at[index2] = np.atan(ys[index2]/zs[index2]) 
at[index1] = -1*np.atan(zs[index1]/ys[index1]) + np.pi/2 

plt.figure(figsize=(8, 5))
plt.plot(xs, at, label='arctan')
plt.xlabel("time, ms")
plt.ylabel("arctan(I/Q), rad")
plt.title("arctan(I/Q)")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.show(block=False)

delta = np.diff(at)
index3 = np.where(np.abs(delta) > 2.0)
delta[index3] = 0.0
atc = np.cumsum(delta)

plt.figure(figsize=(8, 5))
plt.plot(xs[0:-1], atc, label='arctan')
plt.xlabel("time, ms")
plt.ylabel("arctan(I/Q), rad")
plt.title("arctan(I/Q) Corrected jumps")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.show(block=False)

eps0 = 8.854e-12 # [Ф/м] диэл. прон. вакуума
m_e = 9.1e-31 # [kg] масса электрона
q_e = 1.6e-19 # [Q] заряд электрона
C = 2.997e8 # [m/s] скорость света
nu = 98e9 # [Hz] частота интерферометра
K = 2. * eps0 * m_e * C / q_e / q_e * 2. * np.pi * nu

NL = atc * K # [m^-2]
plt.figure(figsize=(8, 5))
plt.plot(xs[0:-1], NL, label='nl')
plt.xlabel("time, ms")
plt.ylabel("nl, $m^{-2}$")
plt.title("Plasma tagret depth [$m^{-2}$]")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.show()

