"""Reviewed subset of UNC 2026-27 MATH course catalog, NOT exhaustive.

Each quoted prerequisite excerpt is taken from the official catalog. The
catalog includes exceptions, placement, permissions, and substitution rules;
unknown conditions are not silently waived. This dataset intentionally limits
itself to a defensible subset and must not certify a whole degree.
"""
from .prerequisite_graph import Alternative as A, CourseRule as R
SOURCE='https://catalog.unc.edu/courses/math/'
def r(code,credits,clauses,excerpt,notes=''):
    return R(code,credits,tuple(tuple(A(*x) if isinstance(x,tuple) else A(x) for x in clause) for clause in clauses),SOURCE,excerpt,notes=notes)
RULES={
'MATH 232':r('MATH 232',4,[[('MATH 231','C-'),'PLACEMENT:MATH232']], 'Prerequisite, A grade of C- or better in MATH 231 or placement by the department.'),
'MATH 233':r('MATH 233',4,[['MATH 232']], 'Prerequisite, MATH 232.'),
'MATH 235':r('MATH 235',4,[['MATH 231'],['MATH 232']], 'Prerequisites, MATH 231 and MATH 232.'),
'MATH 347':r('MATH 347',3,[['MATH 232','MATH 231+MATH 210','MATH 231+MATH 381','COMP 283','STOR 315']], 'Prerequisites, MATH 232 or MATH 231 and MATH 210 or MATH 231 and MATH 381 or COMP 283 or STOR 315.', 'Composite alternatives are unresolved; MATH 347 rule is blocked pending exact grouping review.'),
'MATH 381':r('MATH 381',3,[['MATH 232',('MATH 231','B'),'MATH 210']], 'Prerequisite, MATH 232 or a B or better in MATH 231 or MATH 210.'),
'MATH 383':r('MATH 383',3,[['MATH 233','MATH 235']], 'Prerequisite, MATH 233 or MATH 235.'),
'MATH 521':r('MATH 521',3,[['MATH 233','MATH 235'],['MATH 381',('STOR 215','A-')]], 'Prerequisites, MATH 233 or MATH 235, and MATH 381; A grade of A- or better in STOR 215 may substitute for MATH 381.'),
'MATH 523':r('MATH 523',3,[['MATH 383']], 'Prerequisite, MATH 383.'),
'MATH 524':r('MATH 524',3,[['MATH 383']], 'Prerequisite, MATH 383.'),
'MATH 528':r('MATH 528',3,[['MATH 383']], 'Prerequisite, MATH 383.'),
'MATH 533':r('MATH 533',3,[['MATH 381',('STOR 215','A-')]], 'Prerequisite, MATH 381; A grade of A- or better in STOR 215 may substitute for MATH 381.'),
'MATH 534':r('MATH 534',3,[['MATH 381',('STOR 215','A-')]], 'Prerequisite, MATH 381; A grade of A- or better in STOR 215 may substitute for MATH 381.'),
'MATH 548':r('MATH 548',3,[['MATH 381']], 'Prerequisite, MATH 381.'),
'MATH 549':r('MATH 549',3,[['MATH 347'],['MATH 381']], 'Prerequisites, MATH 347 and MATH 381.'),
'MATH 550':r('MATH 550',3,[['MATH 233','MATH 235'],['MATH 381']], 'Prerequisites, MATH 233 or MATH 235, and MATH 381.'),
'MATH 555':r('MATH 555',3,[['MATH 383']], 'Prerequisite, MATH 383.'),
'MATH 577':r('MATH 577',3,[['MATH 381',('STOR 215','A-')],['MATH 383']], 'Prerequisites, MATH 381 and MATH 383; A grade of A- or better in STOR 215 may substitute for MATH 381.'),
}
# The MATH 347 wording contains multi-course alternatives; remove until encoded as
# proper nested Boolean logic, rather than falsely allowing a partial combination.
RULES.pop('MATH 347')
