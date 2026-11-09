"""PNG compression may differ; any decoded pixel or inventory change must fail."""
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from recheck_second_receiving import exact_generated_files


class ExactPixelArtifacts(unittest.TestCase):
    def test_different_encoding_of_exact_pixels_is_equal(self):
        with tempfile.TemporaryDirectory() as temporary:
            left=Path(temporary)/'a';right=Path(temporary)/'b';left.mkdir();right.mkdir()
            image=Image.new('RGB',(31,23),'black');image.putpixel((3,7),(11,17,101))
            image.save(left/'diff.png',compress_level=0);image.save(right/'diff.png',compress_level=9)
            self.assertNotEqual((left/'diff.png').read_bytes(),(right/'diff.png').read_bytes())
            self.assertTrue(exact_generated_files(left,right))

    def test_one_pixel_or_omitted_image_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            left=Path(temporary)/'a';right=Path(temporary)/'b';left.mkdir();right.mkdir()
            image=Image.new('RGB',(31,23),'black');image.save(left/'diff.png')
            image.putpixel((3,7),(0,0,1));image.save(right/'diff.png')
            self.assertFalse(exact_generated_files(left,right))
            (right/'diff.png').unlink()
            self.assertFalse(exact_generated_files(left,right))


if __name__=='__main__':unittest.main()
