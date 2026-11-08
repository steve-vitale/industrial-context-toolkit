"""Keep failed exact-camera checks visible while measuring every retained pixel; no tolerance or mask repair."""
import math

def pixels(analysis,job,out):
    out.mkdir();basis=analysis.read(job/'job.json');result=[]
    for frame in basis['frames']:
        captures={name:analysis.capture(job,name,frame)for name in ('source','baseline','edited','candidate')}
        source=captures['source'][0];camera=[]
        for name,(row,_)in captures.items():
            analysis.require(row['observation']['request']['frame']==basis['frames'][frame],'Diagnostic frame differs')
            left=source['observation']['view'];right=row['observation']['view']
            if left!=right or source['canvas']['rectangle']!=row['canvas']['rectangle']:
                camera.append(dict(role=name,source_view=left,observed_view=right,source_canvas=source['canvas']['rectangle'],observed_canvas=row['canvas']['rectangle']))
        boxes=[]
        for name in ('source','candidate'):
            attributes=captures[name][0]['observation']['attributes'];parents=[a['parent_id']for a in attributes if a['tag']=='ICT_ID'and a['text']==basis['attributes']['ICT_ID']]
            analysis.require(len(parents)==1,'Diagnostic identity ambiguous')
            fields=[a for a in attributes if a['parent_id']==parents[0]and a['tag']=='MANUFACTURER']
            analysis.require(len(fields)==1,'Diagnostic label ambiguous');boxes.append(fields[0]['projected'])
        region=[math.floor(min(b[0]for b in boxes))-2,math.floor(min(b[1]for b in boxes))-2,math.ceil(max(b[2]for b in boxes))+2,math.ceil(max(b[3]for b in boxes))+2]
        for left,right,permitted in [('source','baseline',None),('source','candidate',region),('baseline','edited',region)]:
            a,ai=captures[left];b,bi=captures[right]
            same_size=a['canvas']['rectangle'][2:]==b['canvas']['rectangle'][2:]
            measures=analysis.image_pair(ai,bi,permitted,out/(frame+'-'+left+'-'+right+'.png'))if same_size else dict(status='not-compared',reason='Native canvas dimensions differ; no resizing/cropping correction')
            result.append(dict(frame=frame,left=left,right=right,exact_camera_status='failed'if camera else'pass',camera_differences=camera,diagnostic_only=bool(camera),**measures))
    return result
