import copy

from attrdict import AttrDict
import svgwrite
import diagram

from .compat import StringIO
from .utils import dict_merge

# fretboard = Fretboard(strings=6, frets=(3, 8))
# fretboard.add_string_label(string=1, label='X', color='')
# fretboard.add_barre(fret=1, strings=(0, 5), label='')
# fretboard.add_marker(fret=1, string=1, label='', color='')


class Fretboard(object):
    default_style = AttrDict(diagram.FRETBOARD_STYLE)

    def __init__(
            self,
            strings=None,
            frets=(0, 5),
            inlays=None,
            title=None,
            style=None,
            label_all_frets=False
    ):
        self.frets = list(range(frets[0] - 1, frets[1] + 1))
        self.strings = [AttrDict({
            'color': None,
            'label': None,
            'font_color': None,
            'font_size': None,
        }) for _ in range(strings or self.string_count)]

        self.markers = []

        # Guitars and basses have different inlay patterns than, e.g., ukulele
        # A double inlay will be added at the 12th/24th/... fret regardless.
        self.inlays = inlays or self.inlays

        self.layout = AttrDict()


        self.style = self.default_style + AttrDict(style or {})

        self.title = title

        # strings get thinner from low -> high
        # not everyone wants this, so make it configurable

        self.drawing = None

    def add_string_label(self, string, label, font_color=None):
        self.strings[string].label = label
        self.strings[string].font_color = font_color

    def add_marker(self, string, fret,
                   color=None, label=None, font_color=None):
        self.markers.append(AttrDict({
            'fret': fret,
            'string': string,
            'color': color,
            'label': label,
            'font_color': font_color,
        }))

    def add_barre(self, fret, strings, finger):
        self.add_marker(
            string=(strings[0], strings[1]),
            fret=fret,
            label=finger,
        )

    def calculate_layout(self):
        # Bounding box of our fretboard
        self.layout.x = self.style.drawing.spacing
        # Above the fret box is the title, with padding either side
        self.layout.y = 0
        if self.title:
            self.layout.y += (self.style.drawing.spacing
                              + self.style.title.font_size)

        # Add some extra space on the right for fret indicators
        self.layout.width = (self.style.drawing.width
                             - self.layout.x
                             - self.style.drawing.spacing)
#        if self.frets[0] > 0:
# allow for fret labels on ALL diagrams for consistent width
        self.layout.width -= self.style.fret_label.width

        self.layout.height = (self.style.drawing.height
                              - (self.layout.y))

        # Spacing between the strings
        self.layout.string_space = self.layout.width / (len(self.strings) - 1)

        # Spacing between the frets, with room at the top and bottom for the
        # nut
        self.layout.fret_space = (
                (self.layout.height - self.style.nut.size * 2)
                / (len(self.frets) - 1)
        )

    def draw_frets(self):
        top = self.layout.y + self.style.nut.size

        for index, fret in enumerate(self.frets):
            if fret < 0:
                # The first fret is the nut, don't draw it.
                continue
            else:
                self.drawing.add(
                    self.drawing.line(
                        start=(
                            self.layout.x,
                            top + (self.layout.fret_space * index)
                        ),
                        end=(
                            self.layout.x + self.layout.width,
                            top + (self.layout.fret_space * index)
                        ),
                        stroke=self.style.fret.color,
                        stroke_width=self.style.fret.size,
                    )
                )

    def draw_strings(self):
        top = self.layout.y
        bottom = top + self.layout.height
        if self.frets[0] == -1:
            top += self.layout.fret_space

        label_y = (self.layout.y
                   + self.style.drawing.font_size / 2
                   - self.style.drawing.spacing)

        for index, string in enumerate(self.strings):
            # adds a style option so all strings have the same width
            if self.style.string.equal_weight:
                width = self.style.string.size
            else:
                # previous default, strings get thinner from left to right
                # just like real ones.
                width = (self.style.string.size
                         - ((self.style.string.size / (len(self.strings) * 1.5))
                            * index))

            # Offset the first and last strings, so they're not drawn
            # outside the edge of the nut.
            offset = 0
            if index == 0:
                offset = width / 2.
            elif index == len(self.strings) - 1:
                offset = - width / 2.

            x = self.layout.x + (self.layout.string_space * index) + offset

            self.drawing.add(
                self.drawing.line(
                    start=(x, top),
                    end=(x, bottom),
                    stroke=string.color or self.style.string.color,
                    stroke_width=width
                )
            )

            # Draw the label above the string
            if string.label is not None:
                self.drawing.add(
                    self.drawing.text(
                        string.label,
                        insert=(x, label_y),
                        font_family=self.style.string.label_font_family or
                                    self.style.drawing.font_family,
                        font_size=self.style.string.label_font_size or
                                  self.style.drawing.font_size,
                        font_weight='bold',
                        fill=string.font_color or self.style.marker.color,
                        text_anchor='middle',
                        dominant_baseline='hanging'
                    )
                )

    def draw_nut(self):
        if self.frets[0] == -1:
            top = self.layout.y + self.layout.fret_space + (self.style.nut.size / 2)
            self.drawing.add(
                self.drawing.line(
                    start=(self.layout.x, top),
                    end=(self.layout.x + self.layout.width, top),
                    stroke=self.style.nut.color,
                    stroke_width=self.style.nut.size,
                )
            )

    def draw_inlays(self):
        x = self.style.drawing.spacing - (self.style.inlays.radius * 4)

        for index, fret in enumerate(self.frets):
            if index == 0:
                continue

            y = sum((
                self.layout.y,
                self.style.nut.size,
                self.layout.fret_space * index,
            )) - self.layout.fret_space / 2

            if fret % 12 in self.inlays:
                # Single dot inlay
                self.drawing.add(
                    self.drawing.circle(
                        center=(x, y),
                        r=self.style.inlays.radius,
                        fill=self.style.inlays.color,
                    )
                )
            elif fret > 0 and not fret % 12:
                # Double dot inlay
                self.drawing.add(
                    self.drawing.circle(
                        center=(x, y - (self.style.inlays.radius * 2)),
                        r=self.style.inlays.radius,
                        fill=self.style.inlays.color,
                    )
                )
                self.drawing.add(
                    self.drawing.circle(
                        center=(x, y + (self.style.inlays.radius * 2)),
                        r=self.style.inlays.radius,
                        fill=self.style.inlays.color,
                    )
                )

    def draw_fret_label(self):
        """
        draw fret number to the right of the first used fret.
        """
        # no labels in first position
        if self.frets[0] == -1:
            return

        # build a list of frets to label
        # each entry is a 3-tuple: (x, y, text)
        fretlist = []
        # x coordinate
        label_x = sum((
            self.layout.x,                   # left of fretboard
            self.layout.width,               # width of fretboard
            self.style.marker.radius,        # radius of marker or barre
            self.style.marker.stroke_width,  #
            self.style.fret_label.width / 2, # half label width (center-aligned)
        ))

        for i, f in enumerate(self.frets[1:]):
            # this is the part that will be different for each fret
            y = sum((
                self.layout.y,                   # top of fretboard
                self.style.nut.size,             # nut size/weight (configurable)
                self.layout.fret_space / 2,      # middle of fret (vertically)
                self.layout.fret_space * i       # move down 'i' frets
            ))

            fretlist.append((label_x, y, str(f)))

        # if we aren't in open/first position...
        if not self.style.drawing.label_all_frets:
            # ignore all but the first entry
            fretlist = [ fretlist[0] ]
        for x, y, label_text in fretlist:
            # add a new text element at the above coordinates
            self.drawing.add(
                self.drawing.text(
                    label_text,
                    insert=(x, y),
                    font_family=self.style.drawing.font_family,
                    font_size=self.style.fret_label.font_size or
                              self.style.drawing.font_size,
                    font_style=self.style.fret_label.font_style or 'italic',
                    font_weight='bold',
                    fill=self.style.drawing.font_color,
                    text_anchor='middle',
                    alignment_baseline='central',
                    dominant_baseline='middle'
                )
            )

    def draw_markers(self):
        for marker in self.markers:
            if isinstance(marker.string, (list, tuple)):
                self.draw_barre(marker)
            else:
                self.draw_marker(marker)

    def draw_marker(self, marker):
        # Fretted position, add the marker to the fretboard.
        x = (self.style.drawing.spacing
             + (self.layout.string_space * marker.string))
        y = sum((
            self.layout.y,
            self.style.nut.size,
            (self.layout.fret_space * (marker.fret - self.frets[0])
             - self.layout.fret_space / 2)
        ))

        self.drawing.add(
            self.drawing.circle(
                center=(x, y),
                r=self.style.marker.radius,
                fill=marker.color or self.style.marker.color,
                stroke=self.style.marker.border_color,
                stroke_width=self.style.marker.stroke_width
            )
        )

        # Draw the label
        if marker.label is not None:
            self.drawing.add(
                self.drawing.text(
                    marker.label,
                    insert=(x, y),
                    font_family=self.style.drawing.font_family,
                    font_size=self.style.drawing.font_size,
                    font_weight='bold',
                    fill=marker.font_color or self.style.marker.font_color,
                    text_anchor='middle',
                    alignment_baseline='central',
                    dominant_baseline='middle'
                )
            )

    def draw_barre(self, marker):
        start_x = (self.style.drawing.spacing
                   + self.layout.string_space * marker.string[0])
        end_x = (self.style.drawing.spacing
                 + self.layout.string_space * marker.string[1])

        y = sum((
            self.layout.y,
            self.style.nut.size,
            (self.layout.fret_space * (marker.fret - self.frets[0])
             - self.layout.fret_space / 2)
        ))

        # Lines don't support borders, so fake it by drawing
        # a slightly larger line behind it.
        self.drawing.add(
            self.drawing.line(
                start=(start_x, y),
                end=(end_x, y),
                stroke=self.style.marker.border_color,
                stroke_linecap='round',
                stroke_width=(self.style.marker.radius * 2
                              + self.style.marker.stroke_width * 2)
            )
        )

        self.drawing.add(
            self.drawing.line(
                start=(start_x, y),
                end=(end_x, y),
                stroke=self.style.marker.color,
                stroke_linecap='round',
                stroke_width=self.style.marker.radius * 2
            )
        )

        if marker.label is not None:
            self.drawing.add(
                self.drawing.text(
                    marker.label,
                    insert=(start_x, y),
                    font_family=self.style.drawing.font_family,
                    font_size=self.style.drawing.font_size,
                    font_weight='bold',
                    fill=self.style.marker.font_color,
                    text_anchor='middle',
                    alignment_baseline='central',
                    dominant_baseline='middle'
                )
            )

    def draw_title(self):
        if self.title is not None:
            x = self.layout.width/2 + self.style.drawing.spacing
            y = self.style.drawing.spacing
            self.drawing.add(
                self.drawing.text(
                    self.title,
                    insert=(x, y),
                    font_family=self.style.title.font_family,
                    font_size=self.style.title.font_size,
                    font_weight='bold',
                    fill=self.style.title.font_color,
                    text_anchor='middle',
                    alignment_baseline='central',
                    dominant_baseline='hanging'
                )
            )

    def draw(self):
        self.drawing = svgwrite.Drawing(size=(
            self.style.drawing.width,
            self.style.drawing.height
        ))
        self.drawing['class'] = 'fretboard'

        if self.style.drawing.background_color is not None:
            self.drawing.add(
                self.drawing.rect(
                    insert=(0, 0),
                    size=(
                        self.style.drawing.width,
                        self.style.drawing.height
                    ),
                    fill=self.style.drawing.background_color
                )
            )

        self.calculate_layout()
        self.draw_frets()
        self.draw_inlays()
        self.draw_fret_label()
        self.draw_strings()
        self.draw_nut()
        self.draw_markers()
        self.draw_title()

    def render(self, output=None):
        self.draw()

        if output is None:
            output = StringIO()

        self.drawing.write(output)
        return output

    def save(self, filename):
        with open(filename, 'w') as output:
            self.render(output)


class GuitarFretboard(Fretboard):
    string_count = 6
    inlays = (3, 5, 7, 9)


class BassFretboard(Fretboard):
    string_count = 4
    inlays = (3, 5, 7, 9)


class UkuleleFretboard(Fretboard):
    string_count = 4
    inlays = (3, 5, 7, 10)
