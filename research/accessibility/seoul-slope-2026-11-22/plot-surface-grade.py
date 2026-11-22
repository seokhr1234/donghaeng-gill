"""Render the clipped research raster with the source district boundaries."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
import numpy as np
from osgeo import gdal, ogr, osr


HERE = Path(__file__).resolve().parent
plt.rcParams.update({'font.family': 'Noto Sans CJK KR', 'axes.unicode_minus': False})
gdal.UseExceptions()
raster = gdal.Open(str(HERE / 'seoul-copernicus-surface-grade-pct-30m.tif'))
values = raster.ReadAsArray()
west, dx, _, north, _, dy = raster.GetGeoTransform()
east, south = west + dx * raster.RasterXSize, north + dy * raster.RasterYSize
fig, ax = plt.subplots(figsize=(12, 8), layout='constrained')
colors = ListedColormap(['#f0eece', '#d2dfc5', '#9cbdb4', '#669896', '#3a687b', '#23374c'])
norm = BoundaryNorm([0, 5, 10, 15, 20, 30, np.inf], colors.N)
image = ax.imshow(np.ma.masked_less(values, 0), cmap=colors, norm=norm,
                  extent=(west, east, south, north), interpolation='nearest')
path = HERE.parent / 'seoul-rest-2026-11-20/derived/osm-boundaries.geojson'
boundaries = ogr.Open(str(path))
layer = boundaries.GetLayer()
source = layer.GetSpatialRef().Clone()
target = raster.GetSpatialRef()
for crs in (source, target):
    crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
project = osr.CoordinateTransformation(source, target)
for row in layer:
    geometry = row.GetGeometryRef().Clone()
    geometry.Transform(project)
    polygons = list(geometry) if geometry.GetGeometryCount() > 0 and geometry.GetGeometryName() == 'MULTIPOLYGON' else [geometry]
    city = row['osm_id'] == 'relation/2297418'
    for polygon in polygons:
        edge = np.array(polygon.GetGeometryRef(0).GetPoints())[:, :2]
        ax.plot(*edge.T, color='#294956', alpha=.75, linewidth=.85 if city else .35)
    if not city:
        label = geometry.PointOnSurface()
        ax.text(label.GetX(), label.GetY(), row['name'], ha='center', va='center', fontsize=8,
                bbox={'facecolor': 'white', 'edgecolor': 'none', 'alpha': .76, 'pad': 1.2})
ax.set(xlim=(west, east), ylim=(south, north), aspect='equal')
ax.axis('off')
ax.set_title('서울 25개 자치구의 지표면 경사율', loc='left', fontsize=20, fontweight='bold')
fig.legend([plt.Rectangle((0, 0), 1, 1, color=color) for color in colors.colors],
           ['5% 미만', '5–10%', '10–15%', '15–20%', '20–30%', '30% 이상'],
           loc='outside lower center', ncols=6, frameon=False, fontsize=10)
fig.supxlabel('Copernicus GLO-30에서 산출한 30m 지표면 참고값 · 보도 노면의 실측 경사 미확인', fontsize=10)
fig.savefig(HERE / 'seoul-surface-grade-overview.png', dpi=150, facecolor='white')
