from typing import List, Tuple, Dict
from enum import Enum
from collections import OrderedDict

from pysat.solvers import Glucose3
from pysat.formula import WCNF, CNF

class tCardType(Enum):
    LESSTHEN=1
    GREATERTHEN=2
    LESSOREQUALS=3
    GREATEROREQUALS=4
    EQUALS=5


class tConstraint:
    def __init__(self):
        self.course_name=""
        self.con_str=""
        self.tas=[]
        self.type=tCardType.LESSOREQUALS 
        self.bound=0
        self.ishard=True
    def __repr__(self):
        return "Course: "++self.course_name++" "++self.con_str


class tCourse:
    def __init__(self):
        self.name=""
        self.start_segment=1
        self.end_segment=6
        self.num_tas_required=0
        self.tas_available=[]

tCourses = Dict[str,tCourse]



def compute_conflict_courses(courses: tCourses) -> Dict[str,List[str]]:
    conflictCourses=[]
    for c in courses.values():
        conCourses=[]
        for cc in courses.values():
            if c == cc or c.start_segment > cc.start_segment:
                continue
            #Now c.start_segment >= cc.start_segment

            if cs.start_segment <= c.end_segment:
                conCourses.append(cs.name)

        conflictCourses[c.name]=conCourses
    return conflictCourses

def get_students(tas: List[str], gr:str)->List[str]:
        return list(filter(lambda s: s.startswith(gr),tas))

#global
con_string_separator="::"
con_separator=":"
   
def get_constraint_type(ct : str)->tCardType:
    if ct == "<":
        return tConTpe.LESSTHEN
    elif ct == "<=":
        return tCardType.LESSOREQUALS
    elif ct==">":
        return tCardType.GREATERTHEN
    elif ct==">=":
        return tCardType.GREATEROREQUALS
    elif ct=="=":
        return tCardType.EQUALS
    else:
        assert(false), "Found: "++ct++", which is not a valid relational operator"

def get_course_constraints(course: str,tas: List[str], con_str: str)->List[tConstraint]:
    constraints=[]
    constrings=con_str.split(con_string_separator)
    for constring in constraints:
        (stud_str,ctype,b,hardness)=tuple(constring.split(con_separator))
        c = tConstraint()
        c.course_name=course
        c.tas=get_students(tas,stud_str)
        c.type=get_constraint_type(ctype)
        c.bound=b
        c.con_str=constring
        c.ishard=hardness
        constraints.append(c)



    

solver_var_counter=0
assignment_var_bound=0
tVarManager = Dict[Tuple(str,str),int]



def populate_varmanager(courses: tCourses):
    for c in courses.values():
        for s in courses.tas_available:
            varmanager[Tuple(c.name,s)]=++solver_var_counter
    assignment_var_bound=solver_var_counter
    return varmanager
        
