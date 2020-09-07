#!/usr/bin/python3

#
# Copyright (c) 2020 Saurabh Joshi, Department of CSE, IIT Hyderabad
#
#


from typing import List, Tuple, Dict
from enum import Enum
from collections import OrderedDict

from pysat.solvers import Glucose3
from pysat.formula import WCNF, CNF, IDPool, CNFPlus
from pysat.card import CardEnc, EncType
from pysat.examples.lsu import LSU
import sys



'''
Usage : python3 ta_allocation.py talist.csv courses.csv

ta_allocation.py : Name of this file
talist.csv       : List of roll numbers available for TA ship, one roll number per line
courses.csv      : List of all courses in the following format


CourseID, StartSegment, EndSegment, NumTAsRequired,ConstraintString

Constraint String format is

ES16|CS17:>=:2:h (a hard constraint (because of 'h') to select at least 2 students from a group of students whose role numbers contain either ES16 or CS17



'''


#global
#separate multile constraint using this string
con_string_separator="&&"
#separator string within a constraint
con_separator=":"
#separator string from multiple group of students
group_separator="|"
#weight of all the soft constraints
soft_weight=1
is_numta_constraint_hard=True

class tCardType(Enum):
    """ Enumeration class for type of cardinality constraint """
    LESSTHEN=1
    GREATERTHEN=2
    LESSOREQUALS=3
    GREATEROREQUALS=4
    EQUALS=5


class tConstraint:
    """ A class that represents a constraint

    Fields
    ------

    course_name : Name of the course
    con_str     : A string unique to a constraint, needed for pretty printing of the solution
                  This string will be printed if it is a soft constraint and it got satisfied
    tas         : List of strings that represent TAs
    type        : type of the cardinality constraint
    bound       : bound of the cardinality constraint
    ishard      : A flag to tell if the constraint is a hard constraint or a soft constraint
    """
    def __init__(self):
        self.course_name=""
        self.con_str=""
        self.tas=[]
        self.type=tCardType.LESSOREQUALS 
        self.bound=0
        self.ishard=True
    def __repr__(self):
        return "Constraint: " + self.course_name + ":" + str(self.type) + " " + str(self.bound) + " " + ("HARD" if self.ishard else "SOFT") +  (' '.join([str(elem) for elem in self.tas]))


class tCourse:
    """ A class that represents a course

    Fields
    ------
    name                : Name of the course
    start_segment       : start segment
    end_segment         : end_segment
    num_tas_required    : Number of TAs needed for the course
    """
    def __init__(self):
        self.name=""
        self.start_segment=1
        self.end_segment=6
        self.num_tas_required=0
        self.tas_available=[]
    def __repr__(self):
        return "Course: "+self.name+" from " + str(self.start_segment) + " to "+str(self.end_segment)

tCourses = Dict[str,tCourse]

def are_conflicting_courses(c1: tCourse, c2: tCourse)->bool:
    """ Determine if two given courses conflict with each other"""
    if(c1.name>=c2.name): # use lexigraphic order to avoid symmetry
        return False
    if(c1.end_segment < c2.start_segment or c2.end_segment < c1.start_segment):
        return False
    return True

def compute_conflict_courses(courses: tCourses) -> Dict[str,List[str]]:
    """ For every course compute the list of conflicting courses """
    conflictCourses=dict()
    for c in courses.values():
        conCourses = list(map((lambda x: x.name),list(filter((lambda cc: are_conflicting_courses(c,cc)),courses.values()))))
        conflictCourses[c.name]=conCourses
    return conflictCourses


## Given a group pattern for students, get the list of students
def get_students(tas: List[str], gr:str)->List[str]:
    """ From the list of all TAs, find TAs matching the constraint string

    For example, gr could be "cs17|es18" this represents all the students
    whole roll numbers start from cs17 or es18

    This function returns the list of TAs from tas which match gr
    """
    group_list = gr.split(group_separator)
    st = []
    for g in group_list:
        st.extend(list(filter(lambda s: g in s,tas)))
    return st


def is_hard_constraint(ctype : str) -> bool:
    if ctype == "h":
        return True
    elif ctype == "s":
        return False
    else:
        assert(False), "Found: "+ctype+" Expected 'h' or 's'"


def preprocess_constraints(constraints: List[tConstraint], courses: tCourses) -> List[tConstraint]:
    """ Given a hard constraint of type :<=0:h remove all the TAs part of group pattern
        of this constraints from the tas_available for this course. This is needed
        to forbid some TAs for a course. e.g., second year students should not TA 
        for second year courses
    """
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


def get_course_constraints(course: str,tas: List[str], con_str: str)->List[tConstraint]:
    """ Parse constraint string in the list of constraints for a course
    con_str would looklike "cs17|es18:>=:2:s" indicating that at least 2 students
    have to be given from cs17 or es18 and it is a soft constraint
    """
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
            c1.con_str=c1.course_name+"->"+constring+"<="
            constraints.append(c1)
        else :
            c.type = cardtype
            c.bound=int(b)

        c.con_str=c.course_name+"->"+constring
        constraints.append(c)
    return constraints



def read_course_constraints(fname: str,tas: List[str], courses: tCourses, constraints: List[tConstraint]):
    """ Parse CSV file to get all the course related info and constraints
    Format of the CSV is

    coursename,start_segment,end_segment,num_tas_required,constraints_string

    Example:

    cs2433,1,3,5,cs17:<=:0:h&&cs16:>=:2:s

    Indicating that cs2433 starts from segment 1 and goes on till segment 3
    It MUST NOT be assigned a TA from cs17 and at least 2 TAs should be given from cs16

    :<=:0 is needed to avoid assigning TAs from the same batch/class
    """
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
        numta_constraint.con_str=str(numta_constraint.course_name)+":ALL:>=:"+str(numta_constraint.bound)+":"+("h" if numta_constraint.ishard else "s")
        constraints.append(numta_constraint)
        constraints.extend(cons)
#    return Tuple(courses,constraints)
        

def read_ta_list(fname: str)->List[str]:
    """ Read total list of TAs from a file with one TA roll number per line"""
    tfile = open(fname,"r")
    tas = []
    for l in tfile:
        s=l.strip()
        if (len(s)==0):
            continue
        tas.append(s.lower())
    return tas


def gen_constraint_conflict_courses(idpool: IDPool, id2varmap, courses: tCourses)->WCNF:
    """ Generate a constraint that two conflicting courses can not share TAs"""
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


def validate_constraint(constraint: tConstraint)->bool:
    if(constraint.type==tCardType.GREATEROREQUALS):
        if (constraint.bound<=0):
            print("Bound for "+constraint.con_str+" is "+str(constraint.bound),file=sys.stderr)
            print("\n Bound too low",file=sys.stderr)
            sys.exit("\nIllegal bound\n")
        if (constraint.bound>len(constraint.tas)):
            print("\nBound for "+constraint.con_tr+" is "+str(constraint.bound),file=sys.stderr)
            print("\nBound is more than TAs available for this constraint",file=sys.stderr)
            print("\nList of available TAs: ")
            print(constraint.tas)
            sys.exit("\n Lower Bound of the constraint too high")
        return True
    if(constraint.type==tCardType.LESSOREQUALS):
        if(constraint.bound<0):
            print("\nBound for constraint is"+str(constraint.bound),file=sys.stderr)
            print("\n Bound too low",file=sys.stderr)
            sys.exit("\nIllegal Bound")
        if(constraint.bound>len(constraint.tas)):
            print("\nBound for constraint is"+str(constraint.bound),file=sys.stderr)
            print("\nUpper bound is way more than TAs available for this constraint",file=sys.stderr)
            print("\nBound too high",file=sys.stderr)
        return True
            





def get_constraint(idpool:IDPool, id2varmap, constraint: tConstraint)->CNFPlus:
    """ Generate formula for a given cardinality constraint"""
    validate_constraint(constraint)
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
        elif (constraint.bound>len(lits)):
            msg="Num TAs available for constraint:"+constraint.con_str+"is more than the bound in the constraint. \
            Changing the bound to "+str(len(lits))+".\n"
            print(msg,file=sys.stderr)
            constraint.bound=len(lits)

        cnf=CardEnc.atleast(lits,vpool=idpool,bound=constraint.bound)
    elif constraint.type == tCardType.LESSOREQUALS :
                cnf = CardEnc.atmost(lits,vpool=idpool,bound=constraint.bound)
    return cnf


def gen_constraints(idpool: IDPool, id2varmap, courses:tCourses, constraints: List[tConstraint])->WCNF:
    """ Generate complete formula for all the constraints including conflicting course constraints"""
    wcnf=gen_constraint_conflict_courses(idpool,id2varmap,courses)
    for con in constraints:
        cnf=get_constraint(idpool,id2varmap,con)
        """ if the constraint is not hard, add an auxiliary variable and keep only this 
            auxiliary variable as soft. This is to allow displaying to the user which high
            level constraint specified by the user was satisfied
        """
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
    



#print(sys.argv)
talist=read_ta_list(sys.argv[1])
#print(talist)        
courses_dict=dict()
constraint_list: List[tConstraint]=[]
read_course_constraints(sys.argv[2],talist,courses_dict,constraint_list)
#print(courses_dict)
constraint_list=preprocess_constraints(constraint_list,courses_dict)
#print(constraint_list)
#print(compute_conflict_courses(courses_dict))
vpool=IDPool()
id2varmap=dict()
wcnf1=gen_constraints(vpool,id2varmap,courses_dict,constraint_list)
#for c in wcnf1.soft:
#    for l in c:
#        print(vpool.obj(l))
lsu=LSU(wcnf1)
res = lsu.solve()
if not res:
    print("Hard constraints could not be satisfied")
else:
#    print(lsu.cost)
    model=list(lsu.model)
    pos_lits=list(filter((lambda x: x>0),model))
    unsatisfied_constraints=[]
    ta_allocation=dict()
    tas_allocated=[]
    for id in id2varmap.values():
        if id in pos_lits:
            (course_name,ta)=vpool.obj(id)
            tas_allocated.append(ta)
            if course_name not in ta_allocation.keys():
                talist=[]
                ta_allocation[course_name]=talist
            
            if ":" not in ta:
                ta_allocation[course_name].append(ta)
        else:
            (course_name,ta)=vpool.obj(id)
            if ":" in ta:
                unsatisfied_constraints.append(ta)


    
    for course_name in ta_allocation.keys():
        print(course_name," : ",ta_allocation[course_name])

    if len(unsatisfied_constraints)>0:
        print("\n Following soft constraints could not be satisfied: \n")
        print(unsatisfied_constraints)
    tas_not_allocated=[t for t in talist if t not in tas_allocated]
    if len(tas_not_allocated)>0:
        print("\nTAs who are not assigned any TA duty: ")
        print(tas_not_allocated)
            




    
