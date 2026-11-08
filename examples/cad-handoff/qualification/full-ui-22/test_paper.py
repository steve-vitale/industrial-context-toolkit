"""Challenge saved paper evidence after local packet inventories are recomputed."""
import copy
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import check_paper as paper


class PaperEvidence(unittest.TestCase):
    def test_complete_original_result_reproduces(self):
        self.assertEqual(paper.check(paper.HERE/'paper-render-1'), paper.read(paper.HERE/'PAPER-COMPARISON-1.json'))

    def test_reindexed_camera_coverage_terminal_and_source_fail(self):
        original_read=paper.read
        for fault in ('camera','omitted_command','failed_container','replaced_source'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory(prefix='ict-paper-control-') as temporary:
                folder=Path(temporary)/'packet'
                shutil.copytree(paper.HERE/'paper-render-1',folder)
                if fault in ('camera','omitted_command'):
                    path=folder/'native/commands.json'
                    rows=original_read(path)
                    if fault=='camera':
                        index=next(i for i,v in enumerate(rows[0]['command']) if v.startswith('-window='))
                        rows[0]['command'][index]='-window=0,0,1,1'
                    else:rows.pop()
                    paper.write(path,rows)
                elif fault=='failed_container':
                    path=folder/'host/AFTER.json';rows=original_read(path)
                    rows[0]['State']['ExitCode']=1;paper.write(path,rows)
                else:
                    path=folder/'inputs/cp1251-original.dxf'
                    path.write_bytes(path.read_bytes()+b'999\nAn undeclared replacement\n')
                retained=copy.deepcopy(original_read(paper.HERE/'PAPER-RETAINED-1.json'))
                retained['files']={p.relative_to(folder).as_posix():dict(bytes=p.stat().st_size,sha256=paper.sha(p)) for p in folder.rglob('*') if p.is_file()}
                def repinned_read(path):
                    return retained if path==paper.HERE/'PAPER-RETAINED-1.json' else original_read(path)
                expected={'camera':'command/window/profile','omitted_command':'commands omitted/reordered',
                          'failed_container':'did not terminate normally','replaced_source':'Retained paper input differs'}[fault]
                with patch.object(paper,'read',side_effect=repinned_read), self.assertRaisesRegex(ValueError,expected):
                    paper.check(folder)


if __name__=='__main__':
    unittest.main()
