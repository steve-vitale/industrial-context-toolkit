"""Separate raw candidate HEADER evidence from an inspection library's load-time diagnostic."""
import hashlib
import json

def raw_header(path):
    lines=path.read_bytes().splitlines(keepends=True)
    if len(lines)%2:raise ValueError('Incomplete raw DXF pairs')
    starts=[i for i in range(0,len(lines)-3,2)if lines[i].strip()==b'0'and lines[i+1].strip()==b'SECTION'
            and lines[i+2].strip()==b'2'and lines[i+3].strip()==b'HEADER']
    if len(starts)!=1:raise ValueError('Missing/ambiguous raw HEADER')
    start=starts[0]
    ends=[i for i in range(start+4,len(lines)-1,2)if lines[i].strip()==b'0'and lines[i+1].strip()==b'ENDSEC']
    if not ends:raise ValueError('Unterminated raw HEADER')
    return b''.join(lines[start:ends[0]+2])

def candidate_report(report,source,candidate,original_parser_flag,destination):
    left,right=raw_header(source),raw_header(candidate)
    if left!=right:raise ValueError('Candidate raw HEADER changed')
    # Keep the actual unchanged comparator report, including its observed bool, outside the stable presentation.
    destination.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    comparison=dict(report);observed=comparison.pop('save_metadata_changed')
    if type(observed)is not bool:raise ValueError('Original parser diagnostic type differs')
    return dict(comparison=comparison,save_metadata=dict(
        basis='Complete raw HEADER bytes, including all save metadata and unrecognized fields',
        source_header_sha256=hashlib.sha256(left).hexdigest(),candidate_header_sha256=hashlib.sha256(right).hexdigest(),
        header_bytes_equal=True,
        parser_flag_status='Not reproducible: ezdxf load replaces $TDCREATE with inspection time; actual flag remains in per-replay comparator report',
        original_published_parser_flag=original_parser_flag,
        actual_parser_report=destination.name))
