import unittest
import pandas as pd
import numpy as np
from scripts.exploratory import encode,wilson,duration_to_seconds,association

class ExploratoryTests(unittest.TestCase):
    def test_duration_units_and_unparsed_values(self):
        result=duration_to_seconds(pd.Series(['60 sec','1 min','0.5 min','unknown',None]))
        self.assertEqual(result.iloc[:3].tolist(),[60,60,30]);self.assertTrue(result.iloc[3:].isna().all())
    def test_missing_and_extreme_values_are_not_discarded(self):
        values=pd.Series(list(range(30))+[1e10,np.nan]);codes,bins,kind,s=encode(values)
        self.assertEqual(len(codes),len(values));self.assertEqual(codes[-1],len(bins)-1)
        self.assertEqual(sum(np.bincount(codes)),len(values));self.assertEqual(s.max(),1e10)
    def test_rare_categories_are_grouped_explicitly(self):
        values=pd.Series([f'c{i}' for i in range(40)]+[None]);codes,bins,kind,s=encode(values)
        self.assertIn('(Other categories)',[b['label'] for b in bins]);self.assertEqual(len(codes),41)
        self.assertTrue(bins[codes[-1]]['missing'])
    def test_wilson_and_association(self):
        self.assertEqual(wilson(0,0),(None,None))
        for p,n in [(0,10),(10,10),(50,100)]:
            low,high=wilson(p,n);self.assertLessEqual(low,p/n+1e-12);self.assertGreaterEqual(high,p/n-1e-12)
        self.assertAlmostEqual(association([50,50],[25,25]),0)
        self.assertAlmostEqual(association([50,50],[0,50]),1)

if __name__=='__main__':unittest.main()
