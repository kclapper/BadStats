from matplotlib.figure import Figure
import numpy as np
from io import BytesIO
import base64

def renderPlot(fig):
    figfile = BytesIO() # Where to save figure

    fig.savefig(figfile, format='png') # Save the current figure
    figfile.seek(0)  # rewind to beginning of file
    figdata_png = base64.b64encode(figfile.getvalue()) # Base64 encode figure

    return figdata_png

def album(kind, tracks, regions=['US']):
    album = tracks['album']
    tracks = tracks['tracks']
    fig = Figure()
    ax = fig.subplots()
    labels = [x['name'] for x in tracks]
    songSpace = 0.5 # Space devoted to each track
    barPadding = 0.1
    width = (songSpace - barPadding) / len(regions)  # the width of the bars

    bars = []
    regionN = 0
    for region in regions:
        statistics = [track[f'{kind}'] for track in tracks]
        bars.append(ax.bar([(((songSpace * i) + (width * regionN))) for i in range(len(tracks)) ],
        statistics,
        width,
        label=region,
        align='edge'))
        regionN += 1

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_ylabel(f'{kind}'.capitalize())
    ax.set_title(f'"{album}" {kind.capitalize()}')
    ax.set_xticks([(((songSpace - barPadding)/2) + (x * songSpace)) for x in range(len(tracks))])
    ax.set_xticklabels(labels, rotation='vertical')
    if len(regions) > 1:
        ax.legend()

    fig.tight_layout()

    render = renderPlot(fig)

    return render

def playlist(kind, tracks, playlist):
    fig = Figure()
    ax = fig.subplots()
    labels = [track['name'] for track in tracks]
    songSpace = 0.5 # Space devoted to each track
    barPadding = 0.1
    width = (songSpace - barPadding) # the width of the bars

    bars = []

    statistics = [track[f'{kind}'] for track in tracks]
    bars.append(ax.barh([(songSpace * i) for i in range(len(tracks)) ],
    statistics,
    height=width,
    align='edge'))

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_xlabel(f'{kind}'.capitalize())
    ax.set_title(f'"{playlist}" {kind.capitalize()}')
    ax.set_yticks([(((songSpace - barPadding)/2) + (x * songSpace)) for x in range(len(tracks))])
    ax.set_yticklabels(labels, rotation='horizontal')
    ax.invert_yaxis()

    fig.tight_layout()
    if len(tracks) * 0.278 > 4.8:
        fig.set_figheight((len(tracks) * 0.278))

    render = renderPlot(fig)

    return render