"""Reject a legitimate, fully reindexed image attributed to the wrong native view."""
import copy
import json
import importlib.util
import unittest
from campaign import HERE, read
from retain import check_pin
spec=importlib.util.spec_from_file_location('cad_final_replay',HERE/'recheck.py')
replay=importlib.util.module_from_spec(spec);spec.loader.exec_module(replay)
checked_view_member=replay.checked_view_member


class ActualViewBinding(unittest.TestCase):
    def test_other_real_image_cannot_stand_in_for_declared_view(self):
        name='public-air-water-receiving'
        saved=check_pin(HERE/'ui-evidence'/name,read(HERE/'UI-RETAINED.json')['attempts'][name])
        captures={(r['label'],r['frame']):r for r in json.loads(saved['attempt/job/ui/actions.json']) if r['kind']=='capture'}
        views=read(HERE/'UI-VISUAL.json')['cases']['public-air-water']['views']
        target=next(r for r in views if r['label']=='source' and r['frame']=='overview')
        self.assertEqual(checked_view_member(target,captures),target['archive_member'])
        for label,frame in [('source','asset-1'),('candidate','overview')]:
            with self.subTest(other_label=label,other_frame=frame):
                other=next(r for r in views if r['label']==label and r['frame']==frame)
                bad=copy.deepcopy(target)
                # Keep the alternate actual image's complete valid byte/pixel
                # identities. Only its attribution to target is false.
                for key in ('archive_member','sha256','pixel_sha256','mode','size'):bad[key]=other[key]
                with self.assertRaisesRegex(ValueError,'declared label/frame'):checked_view_member(bad,captures)


if __name__=='__main__':unittest.main()
