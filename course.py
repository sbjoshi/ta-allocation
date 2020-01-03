from typing import List, Tuple, Dict
from enum import Enum
from collections import OrderedDict

from pysat.solvers import Glucose3
from pysat.formula import WCNF, CNF, IDPool
from pysat.pb import *



'''
Input file format, Comma Separated Values

CourseName, StartSegment, EndSegment, NumTAsRequired,ConstraintString

Constraint String format is

ES16|CS17:>=:2:h (a hard constraint (because of 'h') to select at least 2 students from a group of students whose role numbers start with either ES16 or CS17



'''


#global
con_string_separator="::"
con_separator=":"
group_separator="|"

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
        group_list = gr.split(group_separator)
        st = []
        for g in group_list:
            st.extend(list(filter(lambda s: s.startswith(g),tas)))
        return st



def is_hard_constraint(ctype : str) -> bool:
    if ctype == "h":
        return True
    elif ctype == "s":
        return False
    else:
        assert(false), "Found: "++ctype++" Expected 'h' or 's'"



def preprocess_constraints(constraints: List[tConstraint], courses: tCourses) -> List[tConstraint]:
    fconstraints=[]
    for con in constraints:
        if con.bound == 0 and con.type == tCardType.LESSOREQUALS and con.ishard==True:
            reduced_list = filter(lambda j: j not in con.tas, courses[con.course_name].tas_available)
            courses[con.course_name]=reduced_list
        else:
            fconstraints.append(con)
    return fconstraints

   
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
        c.ishard=is_hard_constraint(hardness)
        constraints.append(c)


def read_course_constraints(fname: str,tas: List[str], courses: tCourses, constraints: List[tConstraint]):
#    courses=[]
#    constraints=[]
    cfile = open(fname,"r")
    for l in cfile:
        fields=l.split(",")
        course=tCourse()
        course.name=fields[0]
        course.start_segment = int(fields[1])
        course.end_segment=int(fields[2])
        course.num_tas_required=int(fields[3])
        course.tas_available=tas.copy()
        courses.append(course)
        cons = get_course_constraints(course.name,tas,fields[4])
        constraints.extend(cons)
#    return Tuple(courses,constraints)
        

    
def read_ta_list(fname: str)->List[str]:
    tfile = open(fname,"r")
    tas = []
    for l in tfile:
        tas.append(l)
    return tas

def gen_constraint_conflict_courses(idpool: IDPool, id2varmap, courses: tCourses, wcnf: WCNF):
    conflict_courses=compute_conflict_courses(courses)
    for course in conflict_courses:
        for ccourse in conflict_courses[course]:
            for t in courses[course].tas_available:
                if t in courses[ccourse].tas_available:
                    t1=Tuple(course,t)
                    t2=Tuple(ccourse,t)
                    id1=idpool.id(t1)
                    id2=idpool.id(t2)
                    if t1 not in id2varmap.keys():
                        id2varmap[t1]=id1
                    if t2 not in id2varmap.keys():
                        id2varmap[t2]=id2
                    wcnf.append([-id1,-id2])

def gen_constraints(idpool: IDPool, id2varmap, courses:tCourses, wcnf: WCNF, constraints: List[tConstraint]):
    for con in constraints:
        t1=Tuple(con.course_name,con.con_str)
        







    
