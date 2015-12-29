#!/usr/bin/env python2

# The MIT License (MIT)
#
# Copyright (c) 2015 Marcus Wanner
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
#    The above copyright notice and this permission notice shall be included in all
#    copies or substantial portions of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#    SOFTWARE.

# Based heavily on:
# https://gist.githubusercontent.com/rdb/8864666/raw/415d5cabfc3d98452bb3d1b0c38e3479cc9244aa/js_linux.py
# There's a lot of extra stuff left in for extensibility reasons.

import os, sys, struct, array, time, threading
from fcntl import ioctl
from subprocess import call

#axes to use (in order)
axes = ["x", "y", "z"]
#controls for each axis
chans = ["MPD", "Loop", "Master"]
#range of each mixer control
ranges = [255, 255, 87]
#axes in this list will be inverted
inv = ["z"]

# These constants were borrowed from linux/input.h
axis_names = {
    0x00 : 'x',
    0x01 : 'y',
    0x02 : 'z',
    0x03 : 'rx',
    0x04 : 'ry',
    0x05 : 'rz',
    0x06 : 'trottle',
    0x07 : 'rudder',
    0x08 : 'wheel',
    0x09 : 'gas',
    0x0a : 'brake',
    0x10 : 'hat0x',
    0x11 : 'hat0y',
    0x12 : 'hat1x',
    0x13 : 'hat1y',
    0x14 : 'hat2x',
    0x15 : 'hat2y',
    0x16 : 'hat3x',
    0x17 : 'hat3y',
    0x18 : 'pressure',
    0x19 : 'distance',
    0x1a : 'tilt_x',
    0x1b : 'tilt_y',
    0x1c : 'tool_width',
    0x20 : 'volume',
    0x28 : 'misc',
}

button_names = {
    0x120 : 'trigger',
    0x121 : 'thumb',
    0x122 : 'thumb2',
    0x123 : 'top',
    0x124 : 'top2',
    0x125 : 'pinkie',
    0x126 : 'base',
    0x127 : 'base2',
    0x128 : 'base3',
    0x129 : 'base4',
    0x12a : 'base5',
    0x12b : 'base6',
    0x12f : 'dead',
    0x130 : 'a',
    0x131 : 'b',
    0x132 : 'c',
    0x133 : 'x',
    0x134 : 'y',
    0x135 : 'z',
    0x136 : 'tl',
    0x137 : 'tr',
    0x138 : 'tl2',
    0x139 : 'tr2',
    0x13a : 'select',
    0x13b : 'start',
    0x13c : 'mode',
    0x13d : 'thumbl',
    0x13e : 'thumbr',

    0x220 : 'dpad_up',
    0x221 : 'dpad_down',
    0x222 : 'dpad_left',
    0x223 : 'dpad_right',

    # XBox 360 controller uses these codes.
    0x2c0 : 'dpad_left',
    0x2c1 : 'dpad_right',
    0x2c2 : 'dpad_up',
    0x2c3 : 'dpad_down',
}

axis_map = []
button_map = []

# Open the joystick device.
fn = '/dev/input/js0'
jsdev = open(fn, 'rb')

# Get the device name.
#buf = bytearray(63)
buf = array.array('c', ['\0'] * 64)
ioctl(jsdev, 0x80006a13 + (0x10000 * len(buf)), buf) # JSIOCGNAME(len)
js_name = buf.tostring()
print('Device name: {}'.format(js_name))

# Get number of axes and buttons.
buf = array.array('B', [0])
ioctl(jsdev, 0x80016a11, buf) # JSIOCGAXES
num_axes = buf[0]

buf = array.array('B', [0])
ioctl(jsdev, 0x80016a12, buf) # JSIOCGBUTTONS
num_buttons = buf[0]

# Get the axis map.
buf = array.array('B', [0] * 0x40)
ioctl(jsdev, 0x80406a32, buf) # JSIOCGAXMAP

for axis in buf[:num_axes]:
    axis_name = axis_names.get(axis, 'unknown(0x%02x)' % axis)
    axis_map.append(axis_name)

# Get the button map.
buf = array.array('H', [0] * 200)
ioctl(jsdev, 0x80406a34, buf) # JSIOCGBTNMAP

for btn in buf[:num_buttons]:
    btn_name = button_names.get(btn, 'unknown(0x%03x)' % btn)
    button_map.append(btn_name)

print('{} axes found: {}'.format(num_axes, ', '.join(axis_map)))
print('{} buttons found: {}'.format(num_buttons, ', '.join(button_map)))

#this loop sets the mixer controls
#TODO: use actual semaphores or something so this can sleep when it's not doing anything
val = [0 for e in axes]
class mixthread(threading.Thread):
    daemon = True
    def run(self):
        last = 0
        lastset = [e for e in val]
        while True:

            if time.time() < last+0.1:
                time.sleep(time.time()-last+0.1)

            for i in range(len(val)):
                if lastset[i] != val[i]:
                    call(["amixer", "set", chans[i], str(val[i])], stdout=None, stderr=sys.stderr)
                    lastset[i] = val[i]

            last = time.time()

t = mixthread()
t.start()

#this loop reads joystick events
while True:
    evbuf = jsdev.read(8)
    if evbuf:
        ptime, pvalue, ptype, pnumber = struct.unpack('IhBB', evbuf)

        if ptype & 0x02: #analogue event
            axis = axis_map[pnumber]

            if axis in axes:
                axisid = axes.index(axis)
                fvalue = 0.5 - pvalue / 32767.0 / 2 #scale value to 0-1
                if axis in inv: fvalue = 1-fvalue
                fvalue = int(fvalue*ranges[axisid])
                print("{}: {} -> {}".format(axis, chans[axisid], fvalue))
                val[axisid] = fvalue

    else:
        break
