"""Deliberate pixel losses and separate target-region controls; no native launch."""
import copy
import unittest
from PIL import Image
from compare_views import pixel_counts


class PixelControls(unittest.TestCase):
    def test_no_edit_has_no_permitted_change(self):
        a=Image.new('RGB',(20,20));b=a.copy();b.putpixel((5,5),(1,0,0))
        result=pixel_counts(a,b,[],None)
        self.assertEqual((result['changed_pixels'],result['outside_permitted_regions'],result['pixel_status']),(1,1,'failed'))

    def test_separate_label_boxes_do_not_hide_change_between_assets(self):
        a=Image.new('RGB',(20,20));b=a.copy();regions=[dict(rectangle=[1,1,4,4]),dict(rectangle=[15,15,19,19])]
        for point in [(2,2),(16,16),(10,10)]: b.putpixel(point,(255,255,255))
        result=pixel_counts(a,b,regions,None)
        self.assertEqual((result['changed_pixels'],result['outside_permitted_regions'],result['pixel_status']),(3,1,'failed'))

    def test_planned_region_does_not_expand_to_cover_other_changes(self):
        a=Image.new('RGB',(20,20));b=a.copy();regions=[dict(rectangle=[1,1,4,4])];original=copy.deepcopy(regions)
        b.putpixel((2,2),(255,255,255));self.assertEqual(pixel_counts(a,b,regions,None)['pixel_status'],'pass')
        b.putpixel((4,2),(1,1,1));self.assertEqual(pixel_counts(a,b,regions,None)['outside_permitted_regions'],1)
        self.assertEqual(regions,original)


if __name__ == '__main__': unittest.main()
