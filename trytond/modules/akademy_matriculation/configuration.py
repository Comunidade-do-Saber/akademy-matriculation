# This file is part of SAGE Education.   The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields, Unique, Check
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.exceptions import UserError
from datetime import date


class MatriculationReference(ModelSQL, ModelView):
    "Matriculation Reference"
    __name__ = 'akademy_configuration.matriculation.reference'

    name = fields.Char('Name', required=True,
        help="Name of the application reference.\nEx: Private, Scholarship holder")
    applications = fields.One2Many('akademy_matriculation.applications', 
        'reference', 'Application method')

    @classmethod
    def __setup__(cls):
        super(MatriculationReference, cls).__setup__()
        table = cls.__table__()
        cls._sql_constraints = [
            ('name', Unique(table, table.name),
            u'We were unable to register the new candidate reference; please check if the name entered already exists.')
        ]


class Phase(ModelSQL, ModelView):
    'Phase'
    __name__ = 'akademy_configuration.phase'

    code = fields.Char('Code', size=20,
        help="Phase code.")
    name = fields.Char('Name', required=True, 
        help="Admission phase name.")
    start = fields.Date('Start', required=True,          
        help="Start date of the academic year.")
    end = fields.Date('End', required=True, 
        help="End date of the academic year.")
    lective_year = fields.Many2One('akademy_configuration.lective.year', 
        'Lective year', required=True, ondelete="RESTRICT")
    application_criteria = fields.One2Many('akademy_configuration.application.criteria', 
        'phase', 'Application criteria')

    @classmethod
    def __setup__(cls):
        super(Phase, cls).__setup__()
        table = cls.__table__()
        cls._sql_constraints = [
            ('name', Unique(table, table.name, table.code),
            u'We were unable to register the new admission phase; please check if the name or code entered already exists.'),
            ('start_date', Check(table, table.start < table.end),
            u'We were unable to register the new school year; please check if the start date is earlier than the end date.')
        ]
    
    @classmethod
    def default_start(cls):
        return date.today() 


class LectiveYear(metaclass=PoolMeta):
    'Lective Year'
    __name__ ='akademy_configuration.lective.year'

    phase = fields.One2Many('akademy_configuration.phase', 
        'lective_year', 'Admission phase')
    application_criteria = fields.One2Many('akademy_configuration.application.criteria', 
        'lective_year', 'Admission criteria')


class AcademicLevel(metaclass=PoolMeta):
    'Academic Level'
    __name__ ='akademy_configuration.academic.level'
    
    application_criteria = fields.One2Many('akademy_configuration.application.criteria', 
        'academic_level', 'Admission criteria')  


class Area(metaclass=PoolMeta):
    'Area'
    __name__ ='akademy_configuration.area'
    
    application_criteria = fields.One2Many('akademy_configuration.application.criteria', 
        'area', 'Admission criteria')     


class Course(metaclass=PoolMeta):
    'Course'
    __name__ ='akademy_configuration.course'
        
    application_criteria = fields.One2Many('akademy_configuration.application.criteria', 
        'course', 'Admission criteria')


class CourseClasse(metaclass=PoolMeta):
    'Course Classe'
    __name__ ='akademy_configuration.course.classe'
          
    application_criteria = fields.One2Many('akademy_configuration.application.criteria', 
        'course_classe', 'Admission criteria')


class ApplicationCriteria(ModelSQL, ModelView):
    'Application Criteria'
    __name__ = 'akademy_configuration.application.criteria'

    code = fields.Char('Code', size=20,
        help="Admission criteria code.")
    name = fields.Char('Name', required=True,
        help="Admission criteria name.")
    description = fields.Text('Description')
    age = fields.Integer('Age', required=True, 
        help=u'Enter the maximum age for admission.')
    average = fields.Numeric('Average', digits=(2,1), 
        required=True, help="Enter the minimum average for admission.")
    student_limit = fields.Integer('Student limit', required=True, 
        help="Enter the limit of students to be admitted.")
    lective_year = fields.Many2One('akademy_configuration.lective.year', 
        'Lective year', required=True, ondelete="RESTRICT")
    academic_level = fields.Many2One('akademy_configuration.academic.level', 
        'Academic level', required=True, ondelete="RESTRICT")
    area = fields.Many2One('akademy_configuration.area', 'Area', 
        domain=[('academic_level', '=', Eval('academic_level', -1))],
        depends=['academic_level'], required=True, ondelete="RESTRICT")    
    course = fields.Many2One('akademy_configuration.course', 'Course', 
        domain=[('area', '=', Eval('area', -1))],
        depends=['area'], required=True, ondelete="RESTRICT")
    course_classe = fields.Many2One(
        'akademy_configuration.course.classe', 'Year level', 
        required=True, domain=[('course', '=', Eval('course', -1))],
        depends=['course'], ondelete="RESTRICT", help="Year level name.")
    phase = fields.Many2One('akademy_configuration.phase', 
        'Phase', required=True, ondelete="RESTRICT")
    application_result = fields.One2Many('akademy_matriculation.applications.result', 
        'application_criteria', 'Result of applications')

    @classmethod
    def __setup__(cls):
        super(ApplicationCriteria, cls).__setup__()
        table = cls.__table__()
        cls._sql_constraints = [
            ('name', Unique(table, table.name, table.course, table.lective_year, table.phase),
            u'We were unable to register the new admission criteria; please check if admission criteria already exist for this admission phase.'),
            ('min_average', Check(table, table.average >= 10),
            u'We were unable to register the new admission criteria; please check if the average is below 10 points.'),
            ('max_average', Check(table, table.average <= 20),
            u'We were unable to register the new admission criteria; please check if the average is above 20 points.'),
            ('student', Check(table, table.student_limit > 0),
            u'We were unable to register the new admission criteria; please check the limit of available positions.'),
        ]

    @classmethod
    def delete(cls, application_criterias):
        for application_criteria in application_criterias:        
            if len(application_criteria.application_result) < 1:
                super(ApplicationCriteria, cls).delete(application_criteria)
            else:
                raise UserError("It was not possible to eliminate the admission criterion because there is already an application associated with it.")
        
    @classmethod
    def default_student_limit(cls):
        return 0
