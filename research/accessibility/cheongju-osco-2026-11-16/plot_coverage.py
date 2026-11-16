#!/usr/bin/env python3
"""Static research figure: recorded geometry and coverage, never a navigation route."""
from pathlib import Path
import json,os
os.environ.setdefault('MPLCONFIGDIR','/tmp/osco-matplotlib-cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection,PatchCollection
from matplotlib.patches import Polygon as PatchPolygon,Rectangle
from pyproj import Transformer

ROOT=Path(__file__).resolve().parent
project=Transformer.from_crs(4326,32652,always_xy=True)
cx,cy=project.transform(127.335363,36.6267203)
def xy(coords):
    return [((x-cx)/1000,(y-cy)/1000) for x,y in [project.transform(*p) for p in coords]]
def load(name):return json.loads((ROOT/'derived'/('osm-'+name+'.geojson')).read_text())['features']
def main():
    fig,axs=plt.subplots(1,2,figsize=(14,7.5))
    fig.patch.set_facecolor('#f8faf9')
    roads=load('roads');buildings=load('buildings');facilities=load('facilities');transport=load('transport')
    patches=[];venue=[]
    for f in buildings:
        g=f['geometry']
        if g['type']=='Polygon':
            patch=PatchPolygon(xy(g['coordinates'][0]))
            (venue if f['id']=='way/1423171859' else patches).append(patch)
    for ax,extent,title in zip(axs,[[-5,5,-4.8,4.8],[-1.6,1.6,-1.6,1.6]],['Regional source coverage','OSCO and Osong station surroundings']):
        ax.set_facecolor('#ffffff')
        ax.add_collection(PatchCollection(patches,facecolor='#dce1e4',edgecolor='none',alpha=.8,zorder=1))
        ax.add_collection(PatchCollection(venue,facecolor='#ea7369',edgecolor='#a63a33',linewidth=.8,zorder=4))
        ordinary=[];foot=[]
        for f in roads:
            g=f['geometry'];line=g['coordinates'] if g['type']=='LineString' else g['coordinates'][0]
            (foot if f['properties']['tags'].get('highway') in ['footway','path','pedestrian','steps'] else ordinary).append(xy(line))
        ax.add_collection(LineCollection(ordinary,colors='#a9b6bd',linewidths=.35,zorder=2))
        ax.add_collection(LineCollection(foot,colors='#1a8c85',linewidths=.65,zorder=3))
        for f in facilities:
            if f['geometry']['type']!='Point':continue
            kind=f['properties']['tags'].get('amenity')
            if kind not in ['toilets','bench','shelter']:continue
            x,y=xy([f['geometry']['coordinates']])[0]
            ax.plot(x,y,'o',ms=3.5,color={'toilets':'#4c69b5','bench':'#9a7637','shelter':'#755398'}[kind],zorder=5)
        for f in transport:
            if f['geometry']['type']=='Point' and f['properties']['tags'].get('railway')=='station' and '오송' in f['properties']['tags'].get('name',''):
                x,y=xy([f['geometry']['coordinates']])[0];ax.plot(x,y,'s',color='#373b45',ms=6,zorder=6);ax.annotate('Osong station (OSM)',(x,y),xytext=(5,-15),textcoords='offset points',fontsize=8)
        ax.plot(0,0,'*',color='#c13e35',markersize=12,zorder=7);ax.annotate('OSCO official representative point',(0,0),xytext=(7,9),textcoords='offset points',fontsize=8)
        corners=xy([[127.28,36.59],[127.39,36.59],[127.39,36.67],[127.28,36.67],[127.28,36.59]])
        ax.plot([p[0] for p in corners],[p[1] for p in corners],color='#cd8845',ls='--',lw=1,zorder=8)
        ax.set_xlim(extent[:2]);ax.set_ylim(extent[2:]);ax.set_aspect('equal');ax.grid(color='#dce3e6',lw=.4)
        ax.set_title(title,fontsize=12);ax.set_xlabel('East / west of representative point (km)');ax.set_ylabel('North / south (km)')
    fig.suptitle('Cheongju OSCO — research data coverage',fontsize=17,y=.98)
    fig.text(.06,.085,'Grey: registered roads/buildings   Teal: footway/path/pedestrian/steps   Blue: toilets   Ochre: benches   Purple: shelters',fontsize=9)
    fig.text(.06,.055,'Reference geometry only. Access, sidewalks, entrances, width, surface grade and facility operation are NOT field verified.',fontsize=9,color='#953d38')
    fig.text(.06,.028,'© OpenStreetMap contributors (ODbL-1.0), Geofabrik snapshot 2026-11-15T21:22:28Z. Drawing CRS: UTM52N / EPSG:32652.',fontsize=8)
    fig.subplots_adjust(top=.91,bottom=.16,wspace=.24)
    folder=ROOT/'previews';folder.mkdir(exist_ok=True)
    fig.savefig(folder/'osco-osm-coverage.png',dpi=170,facecolor=fig.get_facecolor())
    fig.savefig(folder/'osco-osm-coverage.svg',facecolor=fig.get_facecolor())
    print('Coverage PNG/SVG generated from recorded source geometry; no basemap API or navigation route used')
if __name__=='__main__':main()
