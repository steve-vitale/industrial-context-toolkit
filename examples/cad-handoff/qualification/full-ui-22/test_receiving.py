"""Semantic receiving controls; exact wire bytes remain a separate unchanged gate."""
import copy
import unittest
from receive import equal, text_trace


def sample():
    change = dict(id='one',attribute='MODEL',before='Двигатель',after='Мотор')
    node = dict(path='0.1',name='Dependent Entities',role='text',text=change['before'],rectangle=[10,20,100,24])
    row = dict(change=change,observed=node)
    trace = dict(path=node['path'],name=node['name'],role=node['role'],before=change['before'],expected_before=change['before'],proposed=change['after'],
                 focus_result=True,editable_text_result=True,tab_dispatched=True,active_window='Property Editor',rectangle=node['rectangle'],
                 commands=[dict(command=['xdotool','mousemove','--sync','60','32','click','1'],exit=0,stdout='',stderr=''),
                           dict(command=['xdotool','getactivewindow','getwindowname'],exit=0,stdout='Property Editor\n',stderr=''),
                           dict(command=['xdotool','key','Tab'],exit=0,stdout='',stderr='')],completion=[dict(elapsed=.01,text=change['after'])])
    import json
    command = dict(kind='command',command=['python3','/work/ui_text.py',node['path'],change['before'],change['after']],exit=0,stdout=json.dumps(trace))
    return row,command,trace


class ReceivingControls(unittest.TestCase):
    def test_map_order_is_semantic_but_array_order_and_types_are_exact(self):
        self.assertTrue(equal({'first':1,'second':{'a':2,'b':3}}, {'second':{'b':3,'a':2},'first':1}))
        for left,right in [([1,2],[2,1]),(True,1),(1,1.0),(0.0,-0.0),({'a':1},{'a':1,'b':2})]:
            with self.subTest(left=left,right=right): self.assertFalse(equal(left,right))

    def test_complete_unicode_control_passes(self):
        row,command,_ = sample(); text_trace(row,command)

    def test_wrong_field_before_after_or_dispatch_refuses(self):
        for variant in ('path','before','after','command','exit'):
            with self.subTest(variant=variant):
                row,command,trace = sample()
                if variant == 'path': row['observed']['path'] = '0.9'
                elif variant == 'before': row['change']['before'] = 'different'
                elif variant == 'after': row['change']['after'] = 'different'
                elif variant == 'command': command['command'][-1] = 'different'
                else: command['exit'] = 1
                with self.assertRaises(ValueError): text_trace(row,command)

    def test_lost_focus_edit_result_completion_tab_or_wrong_window_refuses(self):
        import json
        for variant in ('focus_result','editable_text_result','tab_dispatched','active_window','completion','commands','rectangle'):
            with self.subTest(variant=variant):
                row,command,trace = sample()
                if variant in ('focus_result','editable_text_result','tab_dispatched'): trace[variant] = False
                elif variant == 'active_window': trace[variant] = 'Another drawing'
                elif variant == 'completion': trace[variant][-1]['text'] = 'partial'
                elif variant == 'commands': trace[variant][-1]['command'] = ['xdotool','key','Escape']
                else: trace[variant] = [0,0,1,1]
                command['stdout'] = json.dumps(trace)
                with self.assertRaises(ValueError): text_trace(row,command)


if __name__ == '__main__': unittest.main()
