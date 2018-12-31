import copy

import attrdict
import diagram
from .compat import StringIO
from .utils import dict_merge


class Chord(object):
    """
    Create a chord diagram.

    positions = string of finger positions, e.g. guitar D = 'xx0232'. If frets
    go above 9, use hyphens to separate all strings, e.g. 'x-x-0-14-15-14'.

    fingers = string of finger labels, e.g. 'T--132' for guitar D/F# '2x0232'.

    barre = int specifying a fret to be completely barred. Minimal barres are
    automatically inserted, so this should be used when you want to override
    this behaviour.
    """
    default_style = dict_merge(
        diagram.CHORD_STYLE,
        diagram.FRETBOARD_STYLE
    )
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
        elif '-' in positions:
            # use - to separate numbers when frets go above 9, e.g., x-x-0-10-10-10
            positions = positions.split('-')
        else:
            positions = list(positions)
        self.positions = list(map(lambda p: int(p) if p.isdigit() else None, positions))

        self.fingers = list(fingers) if fingers else []

        self.barre = barre

        self.style = attrdict.AttrDict(
            dict_merge(
                copy.deepcopy(self.default_style),
                style or {}
            )
        )

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
                if finger.isdigit() and self.fingers.count(finger) > 1:
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

