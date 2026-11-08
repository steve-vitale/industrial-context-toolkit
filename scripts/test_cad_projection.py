"""Reject cached CAD context that does not match its complete retained source."""
import importlib.util
import json
from pathlib import Path
import unittest
import cad_handoff as ch
import test_cad_handoff as prior

class ProjectionSourceBinding(unittest.TestCase):
    setUp = prior.Handoff.setUp

    def projection(self):
        path=Path(__file__).resolve().parents[1]/'examples/cad-handoff/project_to_map.py'
        spec=importlib.util.spec_from_file_location('source_bound_cad_projection',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def refuse_changed_context(self,change):
        packet=self.root/'context';ch.write_packet(self.source,ch.snapshot(self.source),packet)
        path=packet/'cad_context.json';value=json.loads(path.read_bytes());mapping=dict(site='S',plant='P',unit='U',
            assets=[dict(id='fixture/valve-01',tag='FV-101',section='instruments')])
        change(value,mapping);path.write_text(json.dumps(value),encoding='utf-8')
        with self.assertRaises(ValueError):self.projection().project(packet,mapping,self.root/'projected')
        self.assertFalse((self.root/'projected').exists())

    def test_projection_refuses_context_attribute_with_unchanged_source_hash(self):
        self.refuse_changed_context(lambda v,m:v['nodes'][0]['attributes'].update(MODEL='BORROWED HASH'))

    def test_projection_refuses_context_handle_with_unchanged_source_hash(self):
        self.refuse_changed_context(lambda v,m:v['nodes'][0]['source'].update(insert_handle='DEADBEEF'))

    def test_projection_refuses_omitted_asset_and_matching_omitted_mapping(self):
        def omit(value,mapping):value['nodes'].clear();mapping['assets'].clear()
        self.refuse_changed_context(omit)

    def test_projection_refuses_invented_review_status(self):
        self.refuse_changed_context(lambda v,m:v['nodes'][0].update(status='verified'))

    def test_projection_retains_both_multiasset_encoding_cases(self):
        root=Path(__file__).resolve().parents[1]
        for case in ('validation-cp1251','validation-braces'):
            with self.subTest(case=case):
                source=root/'examples/cad-handoff/qualification/validation-2/authored'/(case+'.dxf')
                snapshot=ch.snapshot(source);packet=self.root/case
                ch.write_packet(source,snapshot,packet)
                mapping=dict(site='S',plant='P',unit='U',assets=[dict(id=a['id'],tag=a['attributes']['TAG'],section='instruments') for a in snapshot['assets']])
                target=self.root/(case+'-projection');self.projection().project(packet,mapping,target)
                actual=json.loads((target/'sheet.json').read_bytes())['instruments']
                self.assertEqual(len(actual),2);self.assertEqual((target/'cad-source.dxf').read_bytes(),source.read_bytes())
                for row,asset in zip(actual,snapshot['assets']):
                    for key,value in asset['attributes'].items():self.assertEqual(row['attributes']['cad_'+key.lower()],value)


if __name__ == '__main__': unittest.main()
