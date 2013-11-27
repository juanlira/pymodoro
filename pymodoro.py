#!/usr/bin/env python2
# -*- conding: utf-8 -*-

# pomodoro v0.3, the PYTHON version, with images and sound!
# by Juan Lira.
# a technique for Getting Things Done.
# Based on : http://crunchbanglinux.org/pastebin/948
#            https://gist.github.com/kjmkznr/5972503
 
import pygtk
pygtk.require('2.0')
import pynotify
import sys
import gtk
import gobject
import os
import string
import time
import threading 
from optparse import OptionParser
from datetime import datetime, date, timedelta
from subprocess import Popen

# Options
parser = OptionParser()
parser.set_defaults(work_time=25, play_time=5, break_time=20, rounds=4)
parser.add_option( "-w", "--work-time" , type="int"          , dest="work_time"  , help="How much time to work, in minutes. (default: 25)"          )
parser.add_option( "-p", "--play-time" , type="int"          , dest="play_time"  , help="How much time to break, in minutes. (default: 5)"          )
parser.add_option( "-b", "--break-time", type="int"          , dest="break_time" , help="How long the longer break is, in minutes. (default: 20)"   )
parser.add_option( "-r", "--rounds"    , type="int"          , dest="rounds"     , help="How many pomodoros per break cycle. (default: 4)"          )
parser.add_option(       "--nosound"   , action='store_true' , dest="nosound"    , help="Don't play notification sounds."           , default=False )
(option, args) = parser.parse_args()
 
work_time   = option.work_time  * 60 
play_time   = option.play_time  * 60
break_time  = option.break_time * 60
rounds      = option.rounds

media_path = os.path.dirname(os.path.realpath(__file__)) + '/media/'

class Pomodoro():
 
    def __init__(self, name = 'pomodoro'):
        self.name       = name
        self.sound_play = not(option.nosound)

        self.blocks = { 
                              2 : {
                                    'title'     : 'GET TO WORK!', 
                                    'message'   : 'For %s minutes.' % option.work_time,
                                    'icon'      : media_path + 'pomodoro_play.svg',
                                    'sound'     : media_path + 'drop.ogg',
                                    'sleep_for' : work_time
                                  },
                              1 : {
                                    'title'     : 'TAKE A PAUSE!', 
                                    'message'   : 'For %s minutes.' % option.play_time,
                                    'icon'      : media_path + 'pomodoro_pause.svg',
                                    'sound'     : media_path + 'drop.ogg',
                                    'sleep_for' : play_time
                                  },
                              0 : {
                                    'title'     : 'TAKE A LONG BREAK!', 
                                    'message'   : 'For %s minutes.' % option.break_time,
                                    'icon'      : media_path + 'pomodoro_stop.svg',
                                    'sound'     : media_path + 'beep.ogg',
                                    'sleep_for' : break_time
                                  },
                         'stop' : {
                                    'title'     : 'DONE!', 
                                    'message'   : "You're done, hurray! Good job.",
                                    'icon'      : media_path + 'pomodoro.svg',
                                    'sound'     : media_path + 'beep.ogg',
                                  }
                      }
 
        # Setup context menu
        self.sound = gtk.CheckMenuItem("Play Sounds")
        self.sound.set_active(self.sound_play)
        self.sound.connect('activate', self.toggle_sound_status)
        self.sound.show()

        self.menu = gtk.Menu()
        self.quit = gtk.ImageMenuItem(gtk.STOCK_MEDIA_STOP, "Quit")
        self.quit.connect('activate', self.destroy)
        self.quit.show()

        self.menu.append(self.sound)
        self.menu.append(self.quit)
 
        # Setup Status Icon
        self.statusicon = gtk.StatusIcon()
        self.statusicon.connect('popup-menu', self.popup_menu)
 
        # Starting pomodoro rotation
        worker = threading.Thread(target=self.start)
        worker.setDaemon(True)
        worker.start()
 
    def toggle_sound_status(self, widget):
        self.sound_play = not(self.sound_play)
        self.sound.set_active(self.sound_play)

    def popup_menu(self, status, button, time):
        self.menu.popup(None, None, None, button, time)
 
    def convert_timedelta(self, duration):
        days, seconds = duration.days, duration.seconds
        hours = days * 24 + seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = (seconds % 60)
        return hours, minutes, seconds

    def update_tooltip(self):
        if 'sleep_for' in self.active_block:
            ret = self.block_timestamp + timedelta(seconds = self.active_block['sleep_for']) - datetime.now()

            hours, minutes, seconds = self.convert_timedelta(ret)
            time_left = '{0:02d}:{1:02d}:{2:02d}'.format(hours, minutes, seconds)
            self.statusicon.set_tooltip('Time left: ' + time_left)
 
        return True

    def show_status_icon(self, icon, diff_sec = None):
        self.statusicon.set_from_file(icon)
        self.update_tooltip()

    def notify(self):
        pynotify.Notification(self.active_block['title'], self.active_block['message'], self.active_block['icon']).show()
        if ( self.sound_play ):
            # all the extra arguments are required so that the command is executed and the function doesn't wait for the output
            Popen(['paplay', self.active_block['sound']], shell=False, stdin=None, stdout=None, stderr=None, close_fds=True)

    def set_active_block(self, block_id):
        if block_id in self.blocks:

            self.active_block       = self.blocks[block_id]
            self.block_timestamp    = datetime.now()
            self.notify()

            if 0 <= block_id <= 2:
                self.show_status_icon(self.active_block['icon'])

    def destroy(self, widget, data=None):
        self.set_active_block('stop')
        gtk.main_quit()

    def start(self):
        gobject.timeout_add(1000, self.update_tooltip)
        gobject.threads_init()

        i = 1
        while True:

             # normalize i so that stores 1 through (rounds * 2 - 1) and 0 (end of cycle, therefore break)
            cycle     = i % ( rounds * 2 )                   
            block_id  = ( cycle % 2 ) + ( cycle >= 1 )           # ( cycle % 2 ) = 0 [cycle is even]
                                                                 # ( cycle % 2 ) = 1 [cycle is odd]
            # The results of the previous calculation are:
            # 2 - Work Block  [cycle is odd  and cycle >= 1]
            # 1 - Play Block  [cycle is even and cycle >= 1]
            # 0 - Break Block [cycle = 0]

            # example for rounds = 4
            # |---|-------|----------|-------|
            # | i | cycle | block_id | block |
            # |---|-------|----------|-------|
            # | 1 |   1   |    2     |  work |
            # | 2 |   2   |    1     |  play |
            # | 3 |   3   |    2     |  work |
            # | 4 |   4   |    1     |  play |
            # | 5 |   5   |    2     |  work |
            # | 6 |   6   |    1     |  play |
            # | 7 |   7   |    2     |  work |
            # | 8 |   0   |    0     | break |
            # | 9 |   1   |    2     |  work |

            self.set_active_block(block_id)
            time.sleep(self.active_block['sleep_for'])

            i += 1

if __name__ == '__main__':
    pynotify.init("pomodoro")
    pomodoro = Pomodoro();
    gtk.gdk.threads_init()
    gtk.main()