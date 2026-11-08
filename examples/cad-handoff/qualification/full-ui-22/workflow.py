"""Complete exposed multi-asset native UI method with immutable transport/evidence."""
import copy
import json
from pathlib import Path
import time
import traceback
from bridge_workflow import BridgeWorkflow
from original_workflow import ROOT, write, require, sha
from contract import verify_inventory, verify_selection


class FullWorkflow(BridgeWorkflow):
    def __init__(self):
        self.asset_id = None
        super().__init__()
        self.basis = copy.deepcopy(self.job)

    def record(self, kind, **kw):
        if self.asset_id is not None: kw['asset_id'] = self.asset_id
        super().record(kind, **kw)

    def verify_native(self, path, expected):
        observation = self.observe()
        require(observation['filename'] == path, 'Wrong native drawing')
        groups = verify_inventory(observation, expected)
        self.record('complete_native_inventory', path=path, expected=expected, observation=observation)
        return observation, groups

    def select_asset(self, path, asset, expected, original):
        self.asset_id = asset['id']
        self.job = dict(self.basis, handle=asset['handle'], attributes=asset['attributes'])
        self.focus_canvas(); self.keys('Escape', 'Escape', 't', 'n')
        require(not self.observe()['selected'], 'Native selection was not cleared')
        fields = super().select_and_verify(path, expected[asset['id']], original)
        observation, groups = self.verify_native(path, expected)
        verify_selection(observation, groups[asset['id']])
        self.record('exact_asset_selected', path=path, group=groups[asset['id']], selected=observation['selected'])
        return fields

    def verify_file(self, path, expected, original, label):
        self.verify_native(path, expected)
        for number, asset in enumerate(self.basis['assets'], 1):
            self.select_asset(path, asset, expected, original)
            self.snapshot(label + '-asset-' + str(number))
        self.asset_id = None

    def edit(self, path, expected):
        assets = {a['id']: a for a in self.basis['assets']}
        for number, change in enumerate(self.basis['changes'], 1):
            identity, tag = change['id'], change['attribute']
            require(expected[identity][tag] == change['before'], 'Planned native before value differs')
            fields = self.select_asset(path, assets[identity], expected, True)
            field = fields[tag]
            self.record('native_text_edit_requested', path=path, change=change, observed=field)
            self.command(['python3', '/work/ui_text.py', field['path'], change['before'], change['after']])
            expected[identity][tag] = change['after']
            self.snapshot('edit-' + str(number)); self.fields(expected[identity])
            observation, groups = self.verify_native(path, expected)
            verify_selection(observation, groups[identity])
            require(observation['modified'] is True, 'Native edit was not committed')
            self.record('native_text_edit_committed', path=path, change=change, observation=observation)
        self.asset_id = None

    def run(self):
        self.startup(); expected = {a['id']: dict(a['attributes']) for a in self.basis['assets']}
        after = copy.deepcopy(expected)
        for change in self.basis['changes']: after[change['id']][change['attribute']] = change['after']
        role = self.basis['role']
        if role in ('baseline', 'edited'):
            path = '/work/source.dxf'; self.open_file(path)
            self.verify_file(path, expected, True, 'source'); self.capture(path, 'source')
            if role == 'edited': self.edit(path, expected)
            self.save_as('/work/returned.dxf'); self.close_doc(); self.open_file('/work/returned.dxf')
            self.verify_file('/work/returned.dxf', expected, False, 'reopened')
            self.capture('/work/returned.dxf', 'returned'); self.close_doc()
        else:
            require(role == 'receiving', 'Unknown full UI role')
            for name in ('source', 'baseline', 'edited', 'candidate'):
                path = '/work/' + name + '.dxf'; values = after if name in ('edited', 'candidate') else expected
                self.open_file(path); self.verify_file(path, values, name in ('source', 'candidate'), name)
                self.capture(path, name); self.close_doc()
        self.asset_id = None; self.finish()
        write(self.out / 'RESULT.json', dict(status='controller-complete', role=role, case=self.basis['case'],
              native_ui_only_for_document_actions=True, whole_cad_qualified=False))


if __name__ == '__main__':
    workflow = FullWorkflow()
    try: workflow.run()
    except Exception:
        write(workflow.out / 'FAILURE.json', dict(traceback=traceback.format_exc(), native_pid=workflow.native_pid,
              native_live=workflow.alive(), native_start_identity=workflow.start_identity, run_id=workflow.config['run_id'],
              scope='Failed original full UI development; same native process retained'))
        try: workflow.snapshot('failure')
        except Exception: pass
        raise
