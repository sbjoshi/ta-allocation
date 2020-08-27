from typing import List, Tuple, Dict
from enum import Enum
from collections import OrderedDict

from pysat.solvers import Glucose3
from pysat.formula import WCNF, CNF, IDPool, CNFPlus
from pysat.card import CardEnc, EncType
from pysat.examples.lsu import LSU
import sys



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
soft_weight=1
is_numta_constraint_hard=False

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
        return "Constraint: " + self.course_name + " " + str(self.type) + " " + str(self.bound) + " " + ("HARD" if self.ishard else "SOFT") +  (' '.join([str(elem) for elem in self.tas]))


class tCourse:
    def __init__(self):
        self.name=""
        self.start_segment=1
        self.end_segment=6
        self.num_tas_required=0
        self.tas_available=[]
    def __repr__(self):
        return "Course: "+self.name+" from " + str(self.start_segment) + " to "+str(self.end_segment)

tCourses = Dict[str,tCourse]

# are two given courses conflicting with each other
# test overlap of start/end segments
def are_conflicting_courses(c1: tCourse, c2: tCourse)->bool:
    if(c1.name>=c2.name): # use lexigraphic order to avoid symmetry
        return False
    if(c1.end_segment < c2.start_segment or c2.end_segment < c1.start_segment):
        return False
    return True

#Compute a dictionary coursename -> list of coursse names where there is a conflict
# from key to values
def compute_conflict_courses(courses: tCourses) -> Dict[str,List[str]]:
    conflictCourses=dict()
    for c in courses.values():
        conCourses = list(map((lambda x: x.name),list(filter((lambda cc: are_conflicting_courses(c,cc)),courses.values()))))
        conflictCourses[c.name]=conCourses
    return conflictCourses


## Given a group pattern for students, get the list of students
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
        assert(False), "Found: "+ctype+" Expected 'h' or 's'"


## Given a hard constraint of type :<=0:h remove all the TAs part of group pattern
## of this constraints from the tas_available for this course. This is needed
## to forbid some TAs for a course. e.g., second year students should not TA 
## for second year courses
def preprocess_constraints(constraints: List[tConstraint], courses: tCourses) -> List[tConstraint]:
    fconstraints=[]
    for con in constraints:
        if con.bound == 0 and con.type == tCardType.LESSOREQUALS and con.ishard==True:
            newcon = con
            reduced_list = filter(lambda j: j not in con.tas, courses[con.course_name].tas_available)
            newcon.tas = reduced_list
        else:
            fconstraints.append(con)
    return fconstraints

   
def get_constraint_type(ct : str)->tCardType:
    if ct == "<":
        return tCardType.LESSTHEN
    elif ct == "<=":
        return tCardType.LESSOREQUALS
    elif ct==">":
        return tCardType.GREATERTHEN
    elif ct==">=":
        return tCardType.GREATEROREQUALS
    elif ct=="=":
        return tCardType.EQUALS
    else:
        assert(False), "Found: "+ct+", which is not a valid relational operator"


## Parse constraint string in the list of constraints for a course
def get_course_constraints(course: str,tas: List[str], con_str: str)->List[tConstraint]:
    constraints=[]
    constrings=con_str.split(con_string_separator)
    for constring in constrings:
        (stud_str,ctype,b,hardness)=tuple(constring.split(con_separator))
        c = tConstraint()
        c.course_name=course
        c.tas=get_students(tas,stud_str)
        c.ishard=is_hard_constraint(hardness)
        cardtype = get_constraint_type(ctype)
        if cardtype == tCardType.LESSTHEN:
            b = int(b)-1
            c.type = tCardType.LESSOREQUALS
        elif cardtype == tCardType.GREATERTHEN:
            b = int(b)+1
            c.type=tCardType.GREATEROREQUALS
        elif cardtype == tCardType.EQUALS:
            c.type=tCardType.GREATEROREQUALS
            c.bound=int(b)
            c1 = tConstraint()
            c1.course_name=course
            c1.tas=c.tas.copy()
            c1.type=tCardType.LESSOREQUALS
            c1.ishard=c.ishard
            c1.bound=int(b)
            c1.con_str=constring+"<="
            constraints.append(c1)
        else :
            c.type = cardtype
            c.bound=int(b)

        c.con_str=constring
        constraints.append(c)
    return constraints



## Given a CSV initialize courses with name, start_sgment, end_segment, num_tas_required and constraints
def read_course_constraints(fname: str,tas: List[str], courses: tCourses, constraints: List[tConstraint]):
#    courses=[]
#    constraints=[]
    cfile = open(fname,"r")
    for l in cfile:
        if (len(l.strip())==0):
            return
        fields=l.strip().lower().split(",")
        course=tCourse()
        course.name=fields[0]
        course.start_segment = int(fields[1])
        course.end_segment=int(fields[2])
        course.num_tas_required=int(fields[3])
        course.tas_available=tas.copy()
        courses[course.name]=course
        cons = [] if len(fields[4])==0 else get_course_constraints(course.name,tas,fields[4])
        numta_constraint = tConstraint()
        numta_constraint.course_name=fields[0]
        numta_constraint.bound=course.num_tas_required
        numta_constraint.ishard=is_numta_constraint_hard
        numta_constraint.tas=course.tas_available.copy()
        numta_constraint.type=tCardType.GREATEROREQUALS
        numta_constraint.con_str="ALL:>=:"+str(numta_constraint.bound)+":"+("h" if numta_constraint.ishard else "s")
        constraints.append(numta_constraint)
        constraints.extend(cons)
#    return Tuple(courses,constraints)
        

## Read the list of total TAs available    
def read_ta_list(fname: str)->List[str]:
    tfile = open(fname,"r")
    tas = []
    for l in tfile:
        s=l.strip()
        if (len(s)==0):
            continue
        tas.append(s.lower())
    return tas


## Conflicting courses can not share TAs
def gen_constraint_conflict_courses(idpool: IDPool, id2varmap, courses: tCourses)->WCNF:
    wcnf=WCNF()
    conflict_courses=compute_conflict_courses(courses)
    for course in conflict_courses.keys():
        for ccourse in conflict_courses[course]:
            for t in courses[course].tas_available:
                if t in courses[ccourse].tas_available:
                    t1=tuple((course,t))
                    t2=tuple((ccourse,t))
                    id1=idpool.id(t1)
                    id2=idpool.id(t2)
                    if t1 not in id2varmap.keys():
                        id2varmap[t1]=id1
                    if t2 not in id2varmap.keys():
                        id2varmap[t2]=id2
                    wcnf.append([-id1,-id2])
    return wcnf


def get_constraint(idpool:IDPool, id2varmap, constraint: tConstraint)->CNFPlus:
    lits=[]
    for ta in constraint.tas:
        t1=tuple((constraint.course_name,ta))
        if t1 not in id2varmap.keys():
            id1=idpool.id(t1)
            id2varmap[t1]=id1
        else:
            id1=id2varmap[t1]
        lits.append(id1)

    if constraint.type == tCardType.GREATEROREQUALS :
        if (constraint.bound==1):
            cnf=CNFPlus()
            cnf.append(lits)
        else:
            cnf=CardEnc.atleast(lits,bound=constraint.bound)
    elif constraint.type == tCardType.LESSOREQUALS :
        cnf = CardEnc.atmost(lits,bound=constraint.bound)
    return cnf



# Course should get the num_tas_required (soft constraint)        
'''
def get_requirement_constraint(idpool:IDPool,id2varmap,course:tCourse)->CNFPlus:
    lits=[]
    for ta in course.tas_available:
        t1=Tuple(course.name,ta)
        if t1 not in id2varmap:
            id2varmap[t1]=idpool.id(t1)
        id1=id2varmap(t1)
        lits.append(id1)
    cnf=CardEnc.atleast(lits,encoding=EncType.pairwise,bound=course.num_tas_required)
    return cnf
'''


def gen_constraints(idpool: IDPool, id2varmap, courses:tCourses, constraints: List[tConstraint])->WCNF:
    wcnf=gen_constraint_conflict_courses(idpool,id2varmap,courses)
    for con in constraints:
        cnf=get_constraint(idpool,id2varmap,con)
        if not con.ishard:
            t1=tuple((con.course_name,con.con_str))
            if t1 not in id2varmap:
                id2varmap[t1]=idpool.id(t1)
            id1=idpool.id(t1)
            clauses=cnf.clauses.copy()
            for c in clauses:
                c.append(-id1)
                wcnf.append(c)
            c=[]
            c.append(id1)
            wcnf.append(c,soft_weight)
        else:
            clauses=cnf.clauses.copy()
            for c in clauses:
                wcnf.append(c)
    return wcnf
    



print(sys.argv)
talist=read_ta_list(sys.argv[1])
print(talist)        
courses_dict=dict()
constraint_list: List[tConstraint]=[]
read_course_constraints(sys.argv[2],talist,courses_dict,constraint_list)
print(courses_dict)
constraint_list=preprocess_constraints(constraint_list,courses_dict)
print(constraint_list)
#print(compute_conflict_courses(courses_dict))
vpool=IDPool()
id2varmap=dict()
wcnf1=gen_constraints(vpool,id2varmap,courses_dict,constraint_list)
lsu=LSU(wcnf1)
res = lsu.solve()
if not res:
    print("Hard constraints could not be satisfied")
else:
    print(lsu.cost)
    model=list(lsu.model)
    pos_lits=list(filter((lambda x: x>0),model))
    for id in id2varmap.values():
        if id in pos_lits:
            print(vpool.obj(id))




    
