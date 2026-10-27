import unittest
import numpy as np
import pandas as pd
from src.analysis import clean, forecast, metrics, MODELS
from src.generate_data import generate

class TestAnalysis(unittest.TestCase):
    def test_cleaning_and_no_future_leakage(self):
        raw=generate(); full,mask,audit=clean(raw)
        cutoff=pd.Timestamp('2022-12-01')
        prefix,_,_=clean(raw[pd.to_datetime(raw.date)<=cutoff])
        pd.testing.assert_series_equal(full.loc[:cutoff],prefix)
        self.assertEqual(len(full),96)
        self.assertEqual(audit['duplicates'],1)
        self.assertEqual(int(mask.sum()),4)
        self.assertFalse(full.isna().any())
        self.assertTrue((full>=0).all())
    def test_future_changes_do_not_change_forecast(self):
        raw=generate(); y,_,_=clean(raw)
        changed=raw.copy()
        changed.loc[pd.to_datetime(changed.date)>='2025-01-01','demand']=999999
        z,_,_=clean(changed)
        for model in MODELS:
            np.testing.assert_allclose(forecast(y.iloc[:84],12,model),forecast(z.iloc[:84],12,model))
    def test_seasonal_baseline(self):
        y=pd.Series(np.tile(np.arange(1,13),3),index=pd.date_range('2020-01-01',periods=36,freq='MS'))
        np.testing.assert_array_equal(forecast(y,15,MODELS[0]),np.resize(np.arange(1,13),15))
    def test_metrics(self):
        m=metrics([2.,4.],[1.,5.],np.arange(36,dtype=float))
        self.assertAlmostEqual(m['MAE'],1.)
        self.assertAlmostEqual(m['RMSE'],1.)
        self.assertAlmostEqual(m['MASE'],1/12)
        self.assertEqual(metrics([0.],[0.],np.arange(36))['sMAPE'],0.)
    def test_first_missing_rejected(self):
        raw=generate(); raw.loc[pd.to_datetime(raw.date)=='2018-01-01','demand']=np.nan
        with self.assertRaises(ValueError):clean(raw)
    def test_all_models_finite(self):
        y,_,_=clean(generate())
        for model in MODELS:
            p=forecast(y,12,model)
            self.assertEqual(len(p),12)
            self.assertTrue(np.isfinite(p).all())

if __name__=='__main__':unittest.main()
