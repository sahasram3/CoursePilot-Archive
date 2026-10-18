"""Source-traceable degree requirement evaluator. No inferred UNC requirements."""
from dataclasses import dataclass
from typing import Tuple, Mapping

@dataclass(frozen=True)
class Requirement:
    id: str
    kind: str  # ALL, ANY, AT_LEAST
    courses: Tuple[str, ...]
    count: int
    source_url: str
    catalog_year: str
    verified: bool = False

@dataclass(frozen=True)
class Program:
    name: str
    kind: str  # major/minor
    requirements: Tuple[Requirement, ...]
    source_url: str
    catalog_year: str
    verified: bool = False

def validate_combination(programs):
    majors=sum(p.kind=='major' for p in programs)
    minors=sum(p.kind=='minor' for p in programs)
    if not (1<=majors<=2 and 0<=minors<=2 and len(programs)<=3 and len({p.name for p in programs})==len(programs)):
        raise ValueError('Unsupported program combination')

def audit(programs, completed, in_progress=(), allow_unverified=False):
    """Return a transparent requirement audit, not an official degree audit.
    completed is an iterable of accepted course codes; no automatic double-counting.
    """
    validate_combination(programs)
    done=set(completed); ongoing=set(in_progress)-done
    output=[]
    for program in programs:
        if not allow_unverified and not program.verified:
            raise ValueError('Unverified program: '+program.name)
        for req in program.requirements:
            if not allow_unverified and (not req.verified or not req.source_url or req.catalog_year!=program.catalog_year):
                raise ValueError('Unverified requirement: '+req.id)
            if req.kind not in ('ALL','ANY','AT_LEAST') or not req.courses or len(set(req.courses))!=len(req.courses):
                raise ValueError('Malformed requirement: '+req.id)
            needed={'ALL':len(req.courses),'ANY':1,'AT_LEAST':req.count}[req.kind]
            if not 1<=needed<=len(req.courses):raise ValueError('Invalid count: '+req.id)
            satisfied=[c for c in req.courses if c in done]
            progressing=[c for c in req.courses if c in ongoing]
            output.append({'program':program.name,'requirement_id':req.id,'status':'satisfied' if len(satisfied)>=needed else 'in_progress' if len(satisfied)+len(progressing)>=needed else 'remaining', 'completed_matches':satisfied,'in_progress_matches':progressing,'still_needed':max(0,needed-len(satisfied)),'options':[c for c in req.courses if c not in done],'source_url':req.source_url,'verified':req.verified})
    return output

def source_coverage(programs):
    reqs=[r for p in programs for r in p.requirements]
    return {'programs':len(programs),'requirements':len(reqs),'verified_requirements':sum(r.verified and bool(r.source_url) for r in reqs),'coverage':sum(r.verified and bool(r.source_url) for r in reqs)/len(reqs) if reqs else 0}
