import yaml
import pkg_resources

__version__ = '1.0.0'
__author__ = 'Derek Payton <derek.payton@gmail.com>'
__license__ = 'MIT'

config = yaml.safe_load(pkg_resources.resource_string(__name__, 'config.yml'))
CHORD_STYLE = config['chord']
FRETBOARD_STYLE = config['fretboard']

from .chord import GuitarChord, BassChord, UkuleleChord, MultiFingerChord
from .fretboard import GuitarFretboard, BassFretboard, UkuleleFretboard
