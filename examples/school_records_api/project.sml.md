#Project
name: School Records Api Students
description: Build a school records API with students, courses, enrollment records, teacher roles, PostgreSQL, JWT auth, and CRUD.

#Stack
backend: FastAPI
database: PostgreSQL
auth: JWT

#Capability school
status: requested

#Capability generic_crud
status: requested

#Capability procurement
status: requested

#Role Admin
permissions:
  - read
  - write

#Role Manager
permissions:
  - read
  - write

#Role Viewer
permissions:
  - read

#DataModel Student
fields:
  id: uuid primary
  name: string required max=120
  student_number: string unique required max=60

#DataModel StudentCreate
fields:
  name: string required max=120
  student_number: string unique required max=60

#DataModel Course
fields:
  id: uuid primary
  title: string required max=160
  code: string unique required max=40

#DataModel CourseCreate
fields:
  title: string required max=160
  code: string unique required max=40

#Route ListStudents
method: GET
path: /students
auth: required
body: none
returns: Student[]

#Route CreateStudent
method: POST
path: /students
auth: required
body: StudentCreate
returns: Student

#Route GetStudent
method: GET
path: /students/{id}
auth: required
body: none
returns: Student

#Route UpdateStudent
method: PATCH
path: /students/{id}
auth: required
body: StudentCreate
returns: Student

#Route DeleteStudent
method: DELETE
path: /students/{id}
auth: required
body: none
returns: Student

#Route ListCourses
method: GET
path: /courses
auth: required
body: none
returns: Course[]

#Route CreateCourse
method: POST
path: /courses
auth: required
body: CourseCreate
returns: Course

#Route GetCourse
method: GET
path: /courses/{id}
auth: required
body: none
returns: Course

#Route UpdateCourse
method: PATCH
path: /courses/{id}
auth: required
body: CourseCreate
returns: Course

#Route DeleteCourse
method: DELETE
path: /courses/{id}
auth: required
body: none
returns: Course

#Policy ErrorHandling
broad_catch: forbidden

#Constraint Architecture
architecture: layered
