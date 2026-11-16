#!/usr/bin/env python3
"""Verify that the saved terrain clip is a lossless source-window copy."""
from pathlib import Path
import hashlib,json
import numpy as np
import rasterio
from rasterio.windows import from_bounds
ROOT=Path(__file__).resolve().parent
def main():
    source=ROOT/'raw/copernicus-n36e127/response.bin';clip=ROOT/'derived/osco-context-dem30m.tif'
    meta=json.loads((ROOT/'dem-extraction-results.json').read_text())
    assert hashlib.sha256(source.read_bytes()).hexdigest()==meta['sourceSha256']
    with rasterio.open(source) as original,rasterio.open(clip) as result:
        window=from_bounds(127.28,36.59,127.39,36.67,original.transform).round_offsets().round_lengths()
        expected=original.read(1,window=window)
        assert result.crs==original.crs and result.transform==original.window_transform(window)
        assert np.array_equal(result.read(1),expected,equal_nan=True)
        assert list(result.shape)==meta['shape']
    assert meta['newSlopeValuesPromoted']==0 and meta['sidewalkSurfaceMeasurement'] is False
    report={'pass':True,'source_sha256':meta['sourceSha256'],'clip_sha256':hashlib.sha256(clip.read_bytes()).hexdigest(),
       'pixels_equal_to_original_window':True,'resampling':False,'surface_grade_derived':False,
       'vertical_datum_source':'Copernicus product documentation, not encoded in tile CRS','field_verified':False}
    (ROOT/'dem-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('DEM clip equals original source window; no resampling or slope promotion')
if __name__=='__main__':main()
