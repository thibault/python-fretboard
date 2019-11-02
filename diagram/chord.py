from attrdict import AttrDict
import diagram
from .compat import StringIO
from .utils import convert_int


class Chord(object):
    """
    Create a chord diagram.

    positions = string of finger positions, e.g. guitar D = 'xx0232'. If frets
    go above 9, use hyphens to separate all strings, e.g. 'x-x-0-14-15-14'.
    Alternatively, provide a list (array) of positions, for example
    ['x','x', 0, 2, 3, 2] or ['x','x', 0, 14, 15, 14]

    fingers = string of finger labels, e.g. 'T--132' for guitar D/F# '2x0232'.
    or a list as above (handy when reading config from YAML, for example)
    ['T', '-' ,'-', 1, 3, 2]

    barre = int specifying a fret to be completely barred. Minimal barres are
    automatically inserted, so this should be used when you want to override
    this behaviour.
    """
    default_style = AttrDict(diagram.FRETBOARD_STYLE) + AttrDict(diagram.CHORD_STYLE)
    inlays = None
    strings = None

    def __init__(
            self,
            positions=None,
            fingers=None,
            barre=None,
            title=None,
            style=None
    ):

        if positions is None:
            positions = []
        elif isinstance(positions, str):
            if '-' in positions:
                # use - to separate numbers when frets go above 9, e.g., x-x-0-10-10-10
                positions = positions.split('-')
            else:
                positions = list(positions)
        # oops,. did we put in something like 5333 without quoting?
        if isinstance(positions, int):
            positions = list(str(positions))

        try:
            self.positions = [ convert_int(p) for p in positions ]
        except:
            print(positions)

        try:
            self.fingers = list(fingers) if fingers else []
        except TypeError:
            self.fingers = list(str(fingers))

        self.barre = barre

        self.style = self.default_style + AttrDict(style or {})

        self.title = title

        self.fretboard = None

    @property
    def fretboard_cls(self):
        raise NotImplementedError

    def get_fret_range(self):
        fretted_positions = list(filter(lambda pos: isinstance(pos, int), self.positions))
        if max(fretted_positions) < 5:
            first_fret = 0
        else:
            first_fret = min(filter(lambda pos: pos != 0, fretted_positions))
        return (first_fret, first_fret + 4)

    def draw(self):
        self.fretboard = self.fretboard_cls(
            strings=self.strings,
            frets=self.get_fret_range(),
            inlays=self.inlays,
            title=self.title,
            style=self.style
        )

        if self.barre is not None:
            # when barre is overridden, barre all strings.
            self.fretboard.add_barre(
                fret=self.barre,
                strings=(0, self.fretboard.string_count - 1),
                finger=self.fingers[self.positions.index(self.barre)],
            )
        else:
            # Otherwise check for a barred fret
            for index, finger in enumerate(self.fingers):
                if (isinstance(finger, int) or finger.isdigit()) and self.fingers.count(finger) > 1:
                    self.barre = self.positions[index]
                    self.fretboard.add_barre(
                        fret=self.barre,
                        strings=(index, len(self.fingers) - self.fingers[::-1].index(finger) - 1),
                        finger=finger,
                    )
                    break

        for string in range(self.fretboard.string_count):
            # Get the position and fingering
            try:
                fret = self.positions[string]
            except IndexError:
                pos = None

            # Determine if the string is muted or open
            is_muted = False
            is_open = False

            if fret == 0:
                is_open = True
            elif fret is None:
                is_muted = True

            if is_muted or is_open:
                self.fretboard.add_string_label(
                    string=string,
                    label='X' if is_muted else 'O',
                    font_color=self.style.string.muted_font_color if is_muted else self.style.string.open_font_color
                )
            elif fret is not None and fret != self.barre:
                # Add the fret marker
                try:
                    finger = self.fingers[string]
                except IndexError:
                    finger = None

                self.fretboard.add_marker(
                    string=string,
                    fret=fret,
                    label=finger,
                )

    def render(self, output=None):
        self.draw()

        if output is None:
            output = StringIO()

        self.fretboard.render(output)
        return output

    def save(self, filename):
        with open(filename, 'w') as output:
            self.render(output)


class GuitarChord(Chord):
    @property
    def fretboard_cls(self):
        return diagram.GuitarFretboard


class BassChord(Chord):
    @property
    def fretboard_cls(self):
        return diagram.BassFretboard


class UkuleleChord(Chord):
    @property
    def fretboard_cls(self):
        return diagram.UkuleleFretboard

class MultiFingerChord(UkuleleChord):
    """
    A special case of UkuleleChord that can handle
    additional markers (more than one per string)
    """

    def __init__(self, **kwargs):


        # ensure we have only expected args for the parent class
        superargs = {
            'positions': kwargs.get('positions', None),
            'fingers': kwargs.get('fingers', None),
            'barre': kwargs.get('barre', None),
            'title': kwargs.get('title', None),
            'style': kwargs.get('style', None),
            }

        super().__init__(**superargs)

        fretted_positions = list(filter(lambda pos: isinstance(pos, int), self.positions))
        self.maxfret = max(fretted_positions)
        self.minfret = min([p for p in fretted_positions if p > 0 ])
        print("min: {} max: {}".format(self.minfret, self.maxfret))

        # our additional key for extra fingers
        self.extras = kwargs.get('extras')
        fspec = kwargs.get('fret_range')
        # sanity checks
        # 1. is it a 2-tuple or list?
        # 2. arww the values ints
        # 3. is x[0] < x[1]
        if fspec is None:
            self.fretspec = None
        elif not (isinstance(fspec, (tuple,list)) and len(fspec) == 2):
            print("fret range must have 2 entries")
            self.fretspec = None
        elif not all([isinstance(x, int) for x in fspec]):
            print("fret range must consist of integers only")
            self.fretspec = None
        elif not fspec[0] < fspec[1]:
            self.fretspec = None
        elif self.minfret - fspec[0] > 5:
            self.fretspec = None
        elif self.maxfret > fspec[1]:
            print("highest fret is outside fret range")
            self.fretspec = None
        else:
            self.fretspec = fspec


    def get_fret_range(self):
        """
        Work out how many frets to draw and which one to start at
        we want 5 frets, starting at 0 or self.minfret - 1
        """
        # have we overridden this in config?
        if self.fretspec is not None:
            fr = self.fretspec
        # else, calculate based on frets used
        chord_width = self.maxfret - self.minfret
        # the chord fits in the first 5 frets
        if self.maxfret <= 5:
            fr = (0, 5)
        elif chord_width <= 4:
            fr = (self.minfret - 1, self.minfret + 3)
        else:
            fr = (self.minfret, self.maxfret)
        print("{0} fret range: {1}-{2}".format(self.title, *fr))
        return fr


    def draw(self):
        super(MultiFingerChord, self).draw()
        if self.extras is not None:
            for e in self.extras:
                self.fretboard.add_marker(
                        string=e['string'],
                        fret=e['fret'],
                        color=e.get('color'),
                        label=e['finger'],
                        font_color=e.get('font_color')
                        )

