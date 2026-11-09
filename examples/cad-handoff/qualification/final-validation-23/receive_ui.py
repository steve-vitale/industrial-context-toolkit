"""Restore every original UI byte, reusing only an exact already-retained config."""
import hashlib
import tempfile
from pathlib import Path
from campaign import HERE, read, sha, require, binding
from retain import check_pin
from evidence import unpack
from recheck_native_revisions import restore
from native_ui import receiving
from receive import equal


def check_return_parents():
    launch=read(HERE/'RECEIVING-LAUNCH.json')
    require(sha(HERE/'UI-RETURNS.json')==launch['returns_sha256'] and
            sha(HERE/'UI-SAVED-RETAINED.json')==launch['retained_sha256'] and
            sha(HERE/'UI-PREPARATION.json')==launch['ui_preparation_sha256'],'Pre-launch fresh receiver parent identities differ')
    parents=read(HERE/'UI-SAVED-RETAINED.json')['attempts'];returns=read(HERE/'UI-RETURNS.json')['cases']
    require(set(returns)==set(launch['cases'])=={'public-air-water','final-foreign'} and
            set(parents)=={c+'-'+r for c in returns for r in ('baseline','edited')},'Pre-launch native save cohort differs')
    for case,pins in returns.items():
        for role in ('baseline','edited'):
            name=case+'-'+role;raw=check_pin(HERE/'ui-evidence'/name,parents[name])['attempt/job/returned.dxf']
            require(hashlib.sha256(raw).hexdigest()==pins[role+'_sha256'],'Fresh receiver return differs from completed original save')


def restore_packet(name,root):
    pin=read(HERE/'UI-RETAINED.json')['attempts'][name];packet=HERE/'ui-evidence'/name
    saved=check_pin(packet,pin)
    require(sha(packet/'RESULT.json')==pin['result_sha256'],'External native UI receipt differs')
    support_pin=read(HERE/'UI-SUPPORT-RETAINED.json');support=check_pin(HERE/'ui-support',support_pin)
    prefix=name+'/'
    for key,raw in support.items():
        if key.startswith(prefix):
            member=key[len(prefix):];require(member not in saved,'Support overwrites a retained file');saved[member]=raw
    if 'runtime_support' in pin:
        extra=check_pin(packet/'runtime-support',pin['runtime_support'])
        for member,raw in extra.items():
            require(member.startswith('attempt/job/__pycache__/') and member not in saved,'Unexpected/overwriting runtime support member')
            saved[member]=raw
    # Final PLAN keeps configuration contents out of new packets. This exact
    # profile is already retained in the public pre-final second-receiver packet.
    parent=HERE.parent/'full-ui-22';key='cp1251-second-receiving-1'
    prior=parent/'second-development-1'/key;prior_pin=read(parent/'SECOND-RETAINED-2.json')['attempts'][key]
    from campaign import lf
    require(lf(prior/'INVENTORY.json')==prior_pin['inventory_sha256_lf'] and sha(prior/'evidence.tar.xz')==prior_pin['archive_sha256'],'Previously retained configuration parent differs')
    raw=unpack(prior)['attempt/job/.configuration/QCAD3.conf']
    require(hashlib.sha256(raw).hexdigest()==binding()['configuration_sha256'],'Previously retained configuration identity differs')
    saved['attempt/job/.configuration/QCAD3.conf']=raw
    restore(saved,root)
    # The unchanged receiver checks complete inventory equality, including every
    # restored cache/config byte. Nothing is excluded from that comparison.
    return receiving(root/'attempt'),saved


def check(name):
    packet=HERE/'ui-evidence'/name
    with tempfile.TemporaryDirectory(prefix='ict-final-native-ui-') as temporary:
        root=Path(temporary);result,saved=restore_packet(name,root)
        require(equal(result,read(packet/'RESULT.json')) and equal(result,read(root/'receiving/RESULT.json')) and read(root/'execution/EXIT.json')['exit']==0,'Complete final UI receiving result differs')
        launch=read(HERE/'NATIVE-LAUNCH.json')
        if result['role']!='receiving':require(sha(root/'execution/SCRIPT.py')==launch['host_wrappers']['run_final_ui_host.py'],'Pre-execution original UI wrapper differs')
        else:
            from campaign import lf
            require(lf(root/'execution/SCRIPT.py')==read(HERE/'RECEIVING-LAUNCH.json')['driver_sha256_lf'],'Pre-execution fresh receiver wrapper differs')
            check_return_parents()
        return result
