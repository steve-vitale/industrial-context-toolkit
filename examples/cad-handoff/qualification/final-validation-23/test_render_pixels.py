"""Reject palette-dependent false equality in whole-image render analysis."""
import unittest
from PIL import Image
from receive_render import changed_pixels


class RenderPixels(unittest.TestCase):
    def test_one_palette_pixel_changes(self):
        a=Image.new('P',(4,3),0);a.putpalette([255,255,255,0,0,0]+[0]*762)
        b=a.copy();b.putpixel((2,1),1)
        self.assertEqual(changed_pixels(a,b),1)
        self.assertEqual(changed_pixels(a,a.copy()),0)

    def test_palette_reindex_is_same_visible_color(self):
        a=Image.new('P',(2,2),0);a.putpalette([255,255,255,0,0,0]+[0]*762)
        b=Image.new('P',(2,2),1);b.putpalette([0,0,0,255,255,255]+[0]*762)
        self.assertEqual(changed_pixels(a,b),0)
        b.putpixel((0,0),0)
        self.assertEqual(changed_pixels(a,b),1)


if __name__=='__main__':unittest.main()
