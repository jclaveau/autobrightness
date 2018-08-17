#!/usr/bin/env python
import json
import logging
import math
import os
import sys
import time

from PIL import Image, ImageStat


def brightness(im_file):
    im = Image.open(im_file).convert('L')
    stat = ImageStat.Stat(im)
    return stat.rms[0]

def take_camera_sample(camera_sample):
    os.system('fswebcam -p YUYV -r 356x292 -d /dev/video0 %s' % camera_sample)

def take_screen_sample(screen_sample):
    os.system('scrot %s' % screen_sample)

def error_msg(error_type, arg):
    if error_type == 1:
        print 'Error: enter your argument after "%s"' % arg
    if error_type == 2:
        print 'autobrightness: There is no "%s" OPTION.' % arg
    if error_type == 3:
        print 'Invalid Input: Enter only numbers as arguments!'
    print '\nTry "autobrightness --help" for more information'


def load_config(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config

def create_folder(config_folder):
    os.system('mkdir -p %s' % config_folder)

def write_config(config_file, config):
    with open(config_file, 'w') as f:
        json.dump(config, f)

def set_brightness(new_brightness):
    os.system('xbacklight -set %s' % str(new_brightness))

def measure_camera_brightness():
    take_camera_sample(CAMERA_SAMPLE)
    return brightness(CAMERA_SAMPLE)

def measure_screen_brightness():
    take_screen_sample(SCREEN_SAMPLE)
    return brightness(SCREEN_SAMPLE)

def normalize_brightness(brightness, min_value=0, max_value=255):
    normalized_brightness = (
        (brightness - min_value)
        / (max_value - min_value)
    )
    return max(normalized_brightness, 0)

def compute_adjusted_brightness(normalized_camera_brightness, normalized_screen_brightness):
    return (
        (1 - ALPHA_SCREEN) * normalized_camera_brightness
        + ALPHA_SCREEN * (1 - normalized_screen_brightness)
    )

def smooth_value(value):
    def _mean(values):
        from math import fsum
        return math.fsum(values) / len(values)
    global BRIGHTNESS_VALUES
    if len(BRIGHTNESS_VALUES) >= BRIGHTNESS_SMOOTHING_LENGTH:
        BRIGHTNESS_VALUES.pop()
    BRIGHTNESS_VALUES.insert(0, value)
    smoothed_value = _mean(BRIGHTNESS_VALUES)
    return smoothed_value

logging.basicConfig(level=logging.DEBUG)

DEFAULT_SAMPLE_RATE = 1
HOME_FOLDER = os.getenv("HOME")
CONFIG_FOLDER = HOME_FOLDER + '/.config/wildguppy/'
CONFIG_FILE = CONFIG_FOLDER + '/config.json'

DEFAULT_CONFIG = {
    'sample_rate':str(DEFAULT_SAMPLE_RATE),
    'max_brightness':"100",
    'min_brightness':"0",
}

CAMERA_SAMPLE = '/tmp/autobrightness-camera-sample.jpg'
SCREEN_SAMPLE = '/tmp/autobrightness-screen-sample.jpg'

MAX_CAMERA_BRIGHTNESS = 187
MIN_CAMERA_BRIGHTNESS = 30
MAX_SCREEN_BRIGHTNESS = 255
MIN_SCREEN_BRIGHTNESS = 0

ALPHA_SCREEN = 0.005

BRIGHTNESS_VALUES = []
BRIGHTNESS_SMOOTHING_LENGTH = 4

config_file_exists = os.path.isfile(CONFIG_FILE)
if not config_file_exists:
    create_folder(CONFIG_FOLDER)
    write_config(CONFIG_FILE, DEFAULT_CONFIG)

config = load_config(CONFIG_FILE)

class AutoBrightness(object):
    def __init__(self, config):
        self.max_brightness = float(config['max_brightness'])
        self.min_brightness = float(config['min_brightness'])
        self.sample_rate = float(config['sample_rate'])

    def run(self):
        while True:
            self.run_once()
            time.sleep(self.sample_rate)

    def scale_normalized_brightness(self, normalized_brightness):
        return (
            self.min_brightness +
            (self.max_brightness - self.min_brightness) * normalized_brightness
        )

    def compute_new_brightness(self):
        raw_camera_brightness = measure_camera_brightness()
        raw_screen_brightness = measure_screen_brightness()
        camera_brightness = normalize_brightness(
            raw_camera_brightness, min_value=MIN_CAMERA_BRIGHTNESS, max_value=MAX_CAMERA_BRIGHTNESS)
        screen_brightness = normalize_brightness(
            raw_screen_brightness, min_value=MIN_SCREEN_BRIGHTNESS, max_value=MAX_SCREEN_BRIGHTNESS)
        new_brightness = compute_adjusted_brightness(camera_brightness, screen_brightness)
        raw_new_brightness = self.scale_normalized_brightness(new_brightness)
        logging.debug('raw_camera_brightness: %s', str(raw_camera_brightness))
        logging.debug('raw_screen_brightness: %s', str(raw_screen_brightness))
        logging.debug('camera_brightness: %s', str(camera_brightness))
        logging.debug('screen_brightness: %s', str(screen_brightness))
        logging.debug('new_brightness: %s', str(new_brightness))
        logging.debug('raw_new_brightness: %s', str(raw_new_brightness))
        return raw_new_brightness

    def run_once(self):
        raw_new_brightness = self.compute_new_brightness()

        smoothed_brightness = smooth_value(raw_new_brightness)
        logging.debug('BRIGHTNESS_VALUES: %s', BRIGHTNESS_VALUES)
        logging.debug('smoothed_brightness: %s', smoothed_brightness)

        set_brightness(smoothed_brightness)
        return True

if __name__ == "__main__":
    run = False
    args = sys.argv
    if len(args) >= 2:
        for i in xrange(len(args)):
            error = True
            if args[i] == "help" or args[i] == "--help" or args[i] == "-help" or args[i] == "-h":
                print """
USAGE: autobrightness [OPTION]... [VALUE]...

Adjusts a laptop's brightness automatically, by using camera and screen samples taken regularly.

-s, --set              set time between samples to your configuration file
-t, --time             set time between samples for this session
-x, --max              set maximium brightness level to the config file
-n, --min              set minimium brightness level to the config file"""

                sys.exit()

            if args[i] == "-s" or args[i] == "--set":
                error = False
                try:
                    float(args[i+1])
                    config['sample_rate'] = args[i+1]
                    json.dump(config, open('config.json', 'w'))
                    print "Your default time interval is now '%s' seconds\n" % args[i+1]
                except IndexError:
                    error_msg(1, args[i])
                    sys.exit()
                except ValueError:
                    error_msg(3, args[i+1])
                    sys.exit()


            if args[i] == "-x" or args[i] == "--max":
                try:
                    float(args[i+1])
                    config['max_brightness'] = args[i+1]
                    json.dump(config, open('config.json', 'w'))
                    print "Your maximum brightness value is now '%s'\n" % args[i+1]
                except IndexError:
                    error_msg(1, args[i])
                    sys.exit()
                except ValueError:
                    error_msg(3, args[i+1])
                    sys.exit()

            if args[i] == "-n" or args[i] == "--min":
                try:
                    float(args[i+1])
                    config['min_brightness'] = args[i+1]
                    json.dump(config, open('config.json', 'w'))
                    print "Your minimum brightness value is now '%s'\n" % args[i+1]
                except IndexError:
                    error_msg(1, args[i])
                    sys.exit()
                except ValueError:
                    error_msg(3, args[i+1])
                    sys.exit()

            if args[i] == "-t" or args[i] == "--time":
                error = False
                run = True
                try:
                    arg = float(args[i+1])
                    if arg < 0:
                        print "Your sampling rate cannot be a negative number. Resetting to default value"
                    else:
                        sample_rate = arg
                except IndexError:
                    error_msg(1, args[i])
                    sys.exit()
                except ValueError:
                    error_msg(3, args[i+1])
                    sys.exit()
                break
            if args[i] == "-g" or args[i] == "--gui":
                error = False
                dir_path = os.path.dirname(os.path.realpath(__file__))
                os.system('which python')
                os.system(dir_path + '/panel_app.py')

        if error:
            error_msg(2, args[i])
    else:
        run = True

    if run:
        a = AutoBrightness(config)
        a.run()
