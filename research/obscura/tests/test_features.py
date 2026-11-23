import numpy as np
import pytest
from atmospheric_lab.features import chip_summary, BAND_ORDER


def chip(height=40, width=40):
    values = np.full((14,height,width),2000,dtype=np.uint16)
    values[3] = 1000  # B4 red
    values[7] = 3000  # B8 NIR
    values[12] = 5  # SCL bare/nonvegetated
    values[13] = 0
    return values


def test_official_layout_and_unsigned_ndvi_are_correct():
    values = chip()
    got = chip_summary(values,'official')
    assert len(got) == 54
    assert BAND_ORDER[10:12] == ['B11','B12']
    assert got['c_B4_mean'] == pytest.approx(.1)
    assert got['c_ndvi_p95'] == pytest.approx(.5,abs=2e-6)
    values[7] = 500  # negative index must not wrap uint16
    got = chip_summary(values,'official')
    assert got['c_ndvi_p95'] == pytest.approx(-1/3,abs=3e-6)


def test_cloudy_low_coverage_fallback_is_an_explicit_ablation():
    values = chip()
    values[12] = 9
    values[13] = 99
    baseline = chip_summary(values,'official')
    revised = chip_summary(values,'no_fallback')
    assert baseline['c_B12_mean'] == pytest.approx(.2)
    assert baseline['c_valid_frac'] == 1
    assert np.isnan(revised['c_B12_mean'])
    assert revised['c_valid_frac'] == 0
    assert revised['q_insufficient_clear'] == 1
    assert revised['c_scl_9'] == 1
    assert revised['c_cloudprob'] == 99


def test_all_missing_chip_does_not_masquerade_as_clear_surface():
    values = np.zeros((14,40,40),dtype=np.uint16)
    got = chip_summary(values,'no_fallback',spatial=True)
    assert np.isnan(got['c_B4_mean'])
    assert got['q_insufficient_clear'] == 1
    assert all(np.isnan(v) for k,v in got.items() if k.startswith('s_'))


def test_strict_mask_uses_both_class_and_cloud_probability():
    values = chip()
    values[13,:,:20] = 80
    got = chip_summary(values,'strict')
    assert got['c_valid_frac'] == .5
    assert got['c_B12_mean'] == pytest.approx(.2)
    values[12] = 11  # snow
    assert np.isnan(chip_summary(values,'strict')['c_B12_mean'])


def test_spatial_contrast_is_relative_content_not_georeference():
    values = chip()
    values[11,10:30,10:30] = 5000
    got = chip_summary(values,'no_fallback',spatial=True)
    spatial = {k:v for k,v in got.items() if k.startswith('s_')}
    assert len(spatial) <= 16
    assert got['s_B12_centre_minus_outer'] == pytest.approx(.3)
    assert not any('metre' in k or 'area_m2' in k or 'latitude' in k for k in got)
    assert all(not np.isinf(v) for v in got.values())


def test_bad_layer_count_and_unknown_method_fail():
    with pytest.raises(ValueError): chip_summary(np.zeros((13,40,40)),'official')
    with pytest.raises(ValueError): chip_summary(chip(),'magical')
