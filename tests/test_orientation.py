import unittest
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union
from image_pipeline import extrude
from model_options import geometry
from preview3d import scene

class OrientationTests(unittest.TestCase):
    def test_road_reference_dimensions_and_building_unchanged(self):
        letters,width=extrude(Polygon([(0,0),(2,0),(2,3),(0,3)]),3,1)
        original=scene(letters,width,3,1)
        referenced=scene(letters,width,3,1,road_reference=True)
        for index in range(4):
            np.testing.assert_array_equal(referenced[index][:-2],original[index])
        road=referenced[0][-2:]
        np.testing.assert_allclose(np.ptp(road.reshape(-1,3),axis=0),[25,0,7])

    def test_asymmetric_letter_keeps_source_direction_on_wall(self):
        # F silhouette: stem at left, bars extending right. A mirror must fail.
        shape=Polygon([(0,0),(1,0),(1,2),(2,2),(2,3),(1,3),(1,4),(3,4),(3,5),(0,5)])
        letters,width=extrude(shape,5,1)
        fronts=[Polygon([(x+1.5,y-1.2) for x,y,z in pts]) for pts,n in letters if n==(0,0,-1)]
        self.assertLess(unary_union(fronts).symmetric_difference(shape).area,1e-8)
        base,shifted,_=geometry(letters,width,5,1,'wall')
        # The wall must remain behind the exposed face, above its foot plinth.
        self.assertGreater(min(z for pts,n in base[:12] for x,y,z in pts),max(z for pts,n in shifted for x,y,z in pts))
        points,_,_,_,_=scene(letters,width,5,1,'wall')
        np.testing.assert_allclose(points[len(base):,:,0],np.array([pts for pts,n in letters])[:,:,0])

if __name__=='__main__':unittest.main()
