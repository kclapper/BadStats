from matplotlib.figure import Figure
from io import BytesIO
import base64

def album(kind, tracks):
    album = tracks['album']

    tracks = tracks['tracks']
    labels = [x['name'] for x in tracks]

    values = [track[f'{kind}'] for track in tracks]

    plot = BarPlot(labels, values, kind, album)

    return plot.render()

def playlist(kind, tracks, playlist):

    labels = [track['name'] for track in tracks]
    values = [track[f'{kind}'] for track in tracks]

    plot = BarPlot(labels, values, kind, playlist)

    return plot.render()

class BarPlot:

    _barWidth = 0.5
    _barPadding = 0.1

    _labelWidth = _barWidth - _barPadding

    def __init__(self, labels: list, values: list, kind: str, title: str=None):

        if len(labels) != len(values):
            raise Exception("Different number of labels and values in plot.")

        self._figure = Figure()
        self._axis = self._figure.subplots()
        
        self._labels = labels
        self._values = values
        self._kind = kind
        self._title = title
        
        self.setLabelOrientation("horizontal")
        self._addBarstoChartAxis()
        self._formatPlot()
        
    def _addBarstoChartAxis(self):

        labelPositions = [(self._barWidth * i) for i in range(len(self._labels))]
        
        self._createBars(
            labelPositions,
            self._values,
        )
    
    def _formatPlot(self):

        # Add some text for labels, title and custom x-axis tick labels, etc.
        self._setValueAxisTitle(f'{self._kind}'.capitalize())
        if self._title:
            self._axis.set_title(f'"{self._title}" {self._kind.capitalize()}')
        else:
            self._axis.set_title(f'{self._kind.capitalize()}')

        self._setTicks([((self._labelWidth/2) + (x * self._barWidth)) for x in range(len(self._labels))])
        self._setLabels(self._labels, rotation=self._labelOrientation)

        self._figure.tight_layout()

        if len(self._labels) * 0.278 > 4.8:
            self._figure.set_figheight((len(self._labels) * 0.278))

    def setLabelOrientation(self, orientation: str):

        if orientation == "vertical":
            self._labelOrientation = "horizontal"

            self._createBars = lambda labels, values: self._axis.barh(
                labels,
                values,
                height=self._labelWidth,
                align='edge'
            )

            self._setValueAxisTitle = self._axis.set_xlabel
            
            self._setLabels = self._axis.set_yticklabels
            self._setTicks = self._axis.set_yticks
            self._axis.invert_yaxis()

        elif orientation == "horizontal":
            self._labelOrientation = "vertical"

            self._createBars = lambda labels, values: self._axis.bar(
                labels,
                values,
                self._labelWidth,
                align='edge'
            )

            self._setValueAxisTitle = self._axis.set_ylabel

            self._setLabels = self._axis.set_xticklabels
            self._setTicks = self._axis.set_xticks

    def render(self):
        figfile = BytesIO() # Where to save figure

        self._figure.savefig(figfile, format='png') # Save the current figure
        figfile.seek(0)  # rewind to beginning of file
        figdata_png = base64.b64encode(figfile.getvalue()) # Base64 encode figure

        return figdata_png