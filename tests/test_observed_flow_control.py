import unittest
import numpy as np
from research.experiments.observed_flow_control import observed_blocks,score

P={'scoring':{'reference_speed_min_m_s':.1,'block_m':180,'block_min_points':5,'block_min_directional_coherence':.75}}


class ObservedFlowTest(unittest.TestCase):
    def test_slow_rows_are_unknown_not_negative(self):
        rows=np.array([[2015,100+i,100,2,1,0] for i in range(5)]+
                      [[2015,100,100,2,.01,0]],float)
        blocks,cov,eligible=observed_blocks(rows,P)
        self.assertEqual((len(blocks),cov['all_rows'],cov['speed_eligible_rows']),(1,6,5))
        self.assertEqual(blocks[0]['points'],5);self.assertFalse(eligible[-1])
    def test_reversing_currents_fail_coherence(self):
        rows=np.array([[2015,100+i,100,2,1 if i%2 else -1,0] for i in range(10)],float)
        blocks,cov,_=observed_blocks(rows,P)
        self.assertEqual(blocks,[]);self.assertEqual(cov['excluded_blocks']['incoherent'],1)
    def test_years_are_separate_but_not_claimed_independent_basins(self):
        rows=np.array([[year,100+i,100,2,1,0] for year in [2015,2016] for i in range(5)],float)
        blocks,_,_=observed_blocks(rows,P)
        self.assertEqual(len(blocks),2)
    def test_minimum_points_and_unknown_vector_scoring(self):
        rows=np.array([[2015,100+i,100,2,1,0] for i in range(4)],float)
        blocks,cov,_=observed_blocks(rows,P)
        self.assertEqual(len(blocks),0);self.assertEqual(cov['excluded_blocks']['below_minimum_points'],1)
        r=score([[1,0],None],[[1,0],[1,0]])
        self.assertEqual((r['reference_units'],r['available'],r['positive_cosine']),(2,1,1))


if __name__=='__main__':unittest.main()
