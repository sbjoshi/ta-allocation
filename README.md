# TA allocation using MaxSAT solver  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Usage : ``python3 ta_allocation.py talist.csv courses.csv``

``ta_allocation.py`` : Name of this file

``talist.csv``       : List of roll numbers available for TA ship, one roll number per line

``courses.csv``      : List of all courses in the following format

``CourseID, StartSegment, EndSegment, NumTAsRequired,ConstraintString``

Constraint String format is
``ES16|CS17:>=:2:s&&CS16:<=:0:h`` (a soft constraint (because of ``'s'``) to select at least 2 students from a group of students whose roll numbers
start with either ``ES16`` or ``CS17`` and a hard constraint to not allocate any TA whose roll number contains ``CS16``.

# Dependencies

* PySAT: [https://pysathq.github.io/](https://pysathq.github.io/)

# Contributor

* [Saurabh Joshi](https://sbjoshi.github.io)
