joymix.py
=========

Control multiple ALSA levels using a joystick!

Set the axes, ranges, and ALSA control names at the top of the script.

Example ~/.asoundrc with two software volume controls (corresponds with script defaults):

    pcm.loop {
        type            softvol
        slave.pcm       "dmix"
        control.name    "Loop"
        control.card    0
    }

    pcm.mpd {
        type            softvol
        slave.pcm       "dmix"
        control.name    "MPD"
        control.card    0
    }
