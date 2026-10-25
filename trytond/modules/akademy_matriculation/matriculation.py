# This file is part of SAGE Education.   The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import Check, ModelSQL, ModelView, Unique, fields, sort
from trytond.wizard import Button, StateTransition, StateView, Wizard
from trytond.pyson import Bool, Eval, Not
from trytond.exceptions import UserError
from trytond.pool import Pool
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from ..akademy_classe.classe import ClasseStudentDiscipline

_APPLICATION_RESULT = (
    ('analyzing', 'Analyzing'),
    ('admitted', 'Admitted'),
    ('not_allowed', 'Not allowed'),
    ('waiting_list', 'Waiting list')
)


class Candidates(ModelSQL, ModelView):
    'Candidates'
    __name__ = 'akademy_matriculation.candidates'      

    code = fields.Char('Code', size=20,
        help="Candidate code.")
    date_start = fields.Date('Start date',
        help="Training start date.")
    date_end = fields.Date('End date',
        help="Training end date.") 
    average = fields.Numeric('Average', digits=(2,1), required=True, 
        help=u'Average acquired in the certificate.')
    party = fields.Many2One('party.party', 'Party', 
        required=True, domain=[('is_person', '=', True)],
        ondelete="RESTRICT", help="Candidate name.")   
    institution = fields.Many2One('company.company', 'Institution', 
        required=True, ondelete="RESTRICT",
        help="Name of the training institution.")       
    area = fields.Many2One('akademy_configuration.area', 'Area', 
        domain=[('academic_level', '=', Eval('academic_level', -1))], 
        depends=['academic_level'], required=True, ondelete="RESTRICT")
    course = fields.Many2One('akademy_configuration.course', 'Course', 
        domain=[('area', '=', Eval('area', -1))], 
        depends=['area'], required=True, ondelete="RESTRICT")
    academic_level = fields.Many2One('akademy_configuration.academic.level', 
        'Academic level', required=True, ondelete="RESTRICT") 
    applications = fields.One2Many('akademy_matriculation.applications', 
        'candidate', 'Applications')

    @classmethod
    def __setup__(cls):
        super(Candidates, cls).__setup__()
        table = cls.__table__()
        cls._sql_constraints = [
            ('key', Unique(table, table.party, table.academic_level),
            u'It was not possible to register the new candidate, please check if there is already a candidate at this academic level.'),
            ('duration', Check(table, table.date_start < table.date_end),
            u'It was not possible to register the new candidate, please check the date of registration and completion of academic training.'),
            ('min_average', Check(table, table.average >= 10),
            u'It was not possible to register the new candidate, please check if the certificate average is less than 10.'),
            ('max_average', Check(table, table.average <= 20),
            u'It was not possible to register the new candidate, please check if the certificate average is greater than 20.')
        ]
        cls._order = [('party', 'ASC')]
            
    def get_rec_name(self, name):
        return self.party.rec_name

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('party.rec_name',) + tuple(clause[1:])]
  

class Applications(ModelSQL, ModelView):
    'Applications'
    __name__ = 'akademy_matriculation.applications' 
            
    state = fields.Boolean('Evaluated')
    description = fields.Text('Description')
    reference = fields.Many2One('akademy_configuration.matriculation.reference', 
        'Modality', required=True, help="Choose the application method.")
    age = fields.Function(
        fields.Integer(
            'Age'
        ), 'on_change_with_age')
    candidate = fields.Many2One('akademy_matriculation.candidates', 
        'Candidate', required=True, ondelete="RESTRICT")
    phase = fields.Many2One('akademy_configuration.phase', 'Phase', 
        required=True, ondelete="RESTRICT", help="Application registration phase.")
    lective_year = fields.Many2One('akademy_configuration.lective.year', 
        'Lective year', required=True, ondelete="RESTRICT",
        help="Academic year in which you intend to register.")
    academic_level = fields.Many2One('akademy_configuration.academic.level', 
        'Academic level', required=True, ondelete="RESTRICT",
        help="Academic level you intend to enroll.")
    area = fields.Many2One('akademy_configuration.area', 'Area', 
        domain=[('academic_level', '=', Eval('academic_level', -1))],
        depends=['academic_level'], required=True, ondelete="RESTRICT")    
    course = fields.Many2One('akademy_configuration.course', 'Course', 
        domain=[('area','=',Eval('area', -1))],
        depends=['area'], required=True, ondelete="RESTRICT")
    course_classe = fields.Many2One('akademy_configuration.course.classe', 'Year level',
        domain=[('course', '=', Eval('course', 1))],
        depends=['course'], required=True, ondelete="RESTRICT")
    company = fields.Many2One(
        'company.company', 'Institution', #required=True, 
        ondelete="RESTRICT", help="Name of the institution.") 
    result = fields.One2Many('akademy_matriculation.applications.result', 
        'application', 'Result', 
        states={'invisible': Not(Bool(Eval('state')))}, depends=['state'])

    @classmethod
    def __setup__(cls):
        super(Applications, cls).__setup__()
        table = cls.__table__()
        cls._sql_constraints = [
            ('key', Unique(table, table.candidate, table.course, table.phase, table.lective_year),
            u'It was not possible to register the candidate, because the candidate is already registered for this course, phase and academic year.')
        ]       
        cls._order = [('candidate.party', 'ASC')] 
    
    def get_rec_name(self, name):
        return self.candidate.rec_name

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('candidate.rec_name',) + tuple(clause[1:])]

    @fields.depends('candidate')
    def on_change_with_age(self, name=None):
        if self.candidate.party:
            if self.candidate.party.date_birth:
                now = datetime.now()
                delta = relativedelta(now, self.candidate.party.date_birth)
                years_months_days = delta.years
                
                return years_months_days
        
        return None
            
    @classmethod
    def application_admission_avaliation(cls, ApplicationCriteria, application, ApplicationResult, lective_year):           
        
        if (len(ApplicationCriteria) >= 1):
            for application_criteria in ApplicationCriteria:
                if ((application_criteria.academic_level == application.academic_level)
                and (application_criteria.lective_year == application.lective_year) 
                and (application_criteria.area == application.area) 
                and (application_criteria.course == application.course)
                and (application_criteria.phase >= application.phase)):
                                        
                    if ((application_criteria.average <= application.candidate.average)
                    and (application_criteria.age >= application.age)
                    and (application_criteria.phase >= application.phase)):
                        result_avaliation = 'admitted'
                        Applications.application_admission(
                            ApplicationResult, application, application_criteria, result_avaliation, lective_year) 
                    else:                   
                        result_avaliation = 'not_allowed'
                        Applications.application_admission(
                            ApplicationResult, application, application_criteria, result_avaliation, lective_year)
        else:
            raise UserError("Unable to evaluate the application; please check if"+
                            " registration meet at least one admission criterion for the course "+
                            application.course.name+".")
    
    @classmethod
    def application_admission(cls, ApplicationResult, application, criteria, result_avaliation, lective_year):                 
        total_application_admission = ApplicationResult.search([
            ('application_criteria', '=', criteria), ('result', '=', 'admitted')
            ]) 
        
        if criteria.student_limit > len(total_application_admission):  
            candidate_has_evaluation = ApplicationResult.search([
                ('phase', '=', criteria.phase), ('application', '=', application),
                ('application_criteria', '=', criteria), ('lective_year', '=', lective_year)
                ])   
            
            if len(candidate_has_evaluation) > 0:
                pass
            else:
                Result = ApplicationResult(
                    result = result_avaliation,
                    phase = criteria.phase,
                    application = application,
                    application_criteria = criteria,
                    lective_year = lective_year
                )
                Result.save() 
                
                Applications.application_change_state(application)
        else:
            raise UserError("Already reached the maximum number of available places.") 

    @classmethod
    def application_change_state(cls, application):        
        application.state = True
        application.save()   
                                        	
    
class ApplicationsResult(ModelSQL, ModelView):
    'Applications Result'
    __name__ = 'akademy_matriculation.applications.result'
        
    result = fields.Selection(selection=_APPLICATION_RESULT, string=u'Result')  
    phase = fields.Many2One('akademy_configuration.phase', 'Phase', required=True)
    application = fields.Many2One('akademy_matriculation.applications', 
        'Application', required=True, ondelete="RESTRICT")
    application_criteria = fields.Many2One('akademy_configuration.application.criteria', 
        'Application criteria', required=True, ondelete="RESTRICT")
    lective_year = fields.Many2One('akademy_configuration.lective.year', 
        'Lective year', required=True, ondelete="RESTRICT")
     
    @classmethod
    def __setup__(cls):
        super(ApplicationsResult, cls).__setup__()
        table = cls.__table__()
        cls._sql_constraints = [
            ('key', Unique(table, table.application, table.application_criteria),
            u'The application has already been evaluated.')
        ]     
        cls._order = [('application.candidate.party', 'ASC')] 
    
    def get_rec_name(self, name):
        return self.application.rec_name

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('application.rec_name',) + tuple(clause[1:])]             


class StudentTransfer(ModelSQL, ModelView):
    'Student - Transfer'
    __name__ = 'akademy_matriculation.student.transfer'

    description = fields.Text('Description')
    internal = fields.Boolean(
        'Internal',
        states={ 
            'invisible': Bool(Eval('external')), 
            'required': Not(Bool(Eval('external')))
        }, depends=['external'],
        help="Leaving the institution.")
    external = fields.Boolean(
        'External',
        states={
            'invisible': Bool(Eval('internal')), 
            'required': Not(Bool(Eval('internal')))
        }, depends=['internal'],
        help="Coming from another institution.")
    lective_year = fields.Many2One(
		'akademy_configuration.lective.year', 'Lective year', 
        states={ 
            'invisible': Bool(Eval('internal')), 
            'required': Not(Bool(Eval('internal')))
        }, depends=['internal'], ondelete="RESTRICT",
        help="Name of the school year.")
    academic_level = fields.Many2One(
		'akademy_configuration.academic.level', 'Academic level', 
        states={ 
            'invisible': Bool(Eval('internal')), 
            'required': Not(Bool(Eval('internal')))
        }, depends=['internal'], ondelete="RESTRICT",
        help="Name of academic level.")
    area = fields.Many2One(
		'akademy_configuration.area', 'Area', 
        states={ 
            'invisible': Bool(Eval('internal')), 
            'required': Not(Bool(Eval('internal')))
        }, ondelete="RESTRICT",
		domain=[('academic_level', '=', Eval('academic_level', -1))], 
		depends=['academic_level', 'internal'], help="Area name.")
    course = fields.Many2One(
		'akademy_configuration.course', 'Course', 
        states={ 
            'invisible': Bool(Eval('internal')), 
            'required': Not(Bool(Eval('internal')))
        }, ondelete="RESTRICT",
		domain=[('area', '=', Eval('area', -1))],
		depends=['area', 'internal'], help="Course name.")
    course_classe = fields.Many2One(
		'akademy_configuration.course.classe', 'Year level', 
        states={ 
            'invisible': Bool(Eval('internal')), 
            'required': Not(Bool(Eval('internal')))
        }, ondelete="RESTRICT",
        domain=[('course', '=', Eval('course', -1))],
		depends=['course', 'internal'], help="Year level name.")
    student = fields.Many2One('company.student', 
        'Student', required=True, ondelete="RESTRICT")
    student_transfer_discipline = fields.One2Many(
		'akademy_matriculation.student.transfer.discipline', 
        'student_transfer', 'Discipline')
    
    @classmethod
    def __setup__(cls):
        super(StudentTransfer, cls).__setup__()
        table = cls.__table__()
        cls._sql_constraints = [
            ('key',
            Unique(table, table.lective_year, table.academic_level, table.course, table.course_classe, table.student),
            u'It was not possible to register the transfer, please check if the student already has a transfer with these details.')
        ]

    def get_rec_name(self, name):
        t1 = '%s' % \
            (self.student.rec_name)
        return t1   
    

class StudentTransferDiscipline(ModelSQL, ModelView):
    'Student Tranfer Discipline'
    __name__ = 'akademy_matriculation.student.transfer.discipline'

    course = fields.Function(
		fields.Integer(
			'Course',
		), 'on_change_with_course')
    average = fields.Numeric('Average', digits=(2,1), required=True) 
    student_transfer = fields.Many2One('akademy_matriculation.student.transfer', 
        'Student', required=True, ondelete="RESTRICT")
    discipline = fields.Many2One('akademy_configuration.discipline', 
        'Discipline', required=True, ondelete="RESTRICT")   
    course_classe = fields.Many2One('akademy_configuration.course.classe', 'Year level', 
        required=True, domain=[('course.id', '=', Eval('course', -1))],
        depends=['course'], ondelete="RESTRICT", help="Year level name.")
    
    @classmethod
    def __setup__(cls):
        super(StudentTransferDiscipline, cls).__setup__()
        table = cls.__table__()
        cls._sql_constraints = [
            ('uniq_classes',
            Unique(table, table.student_transfer, table.discipline, table.course_classe),
            u'It was not possible to associate this subject with the student, please check if they already have this subject associated.')            
        ]

    def get_rec_name(self, name):
        t1 = '%s' % \
            (self.discipline.rec_name)
        return t1

    @fields.depends('student_transfer')
    def on_change_with_course(self, name=None):  
        if self.student_transfer:
            #if self.student_transfer.external:
            return self.student_transfer.student.course.id
        else:
            return None


class MatriculationCreateWzardStart(ModelView):
    'Matriculation CreateStart'
    __name__ = 'akademy_matriculation.wizmatriculation.create.start'

    is_candidate = fields.Boolean(
        'Candidate', 
        states={
            'invisible':  Bool(Eval('is_transferred')) | Bool(Eval('is_student'))
        }, depends=['is_transferred'], 
        help="Registration for candidate.")
    is_transferred = fields.Boolean(
        'Transferred', 
        states={
            'invisible':  Bool(Eval('is_candidate')) | Bool(Eval('is_student'))
        }, depends=['is_candidate'], 
        help="Registration for transferred students.")
    applications = fields.Many2One(
        'akademy_matriculation.applications.result', 'Application',
        states={
            'invisible': Not(Bool(Eval('is_candidate'))), 
            'required': Bool(Eval('is_candidate'))
        }, domain=[('result', '=', 'admitted')], 
        help="Dear user, the candidate will be registered.")
    transferred = fields.Many2One(
        'akademy_matriculation.student.transfer', 'Transferred',
        states={
            'invisible': Not(Bool(Eval('is_transferred'))), 
            'required': Bool(Eval('is_transferred'))
        }, domain=[('external', '=', True)],
        help="Dear user, the transfer student will be enrolled.")
           
        
class MatriculationCreateWzard(Wizard):
    'Matriculation CreateWzard'
    __name__ = 'akademy_matriculation.wizmatriculation.create'

    start_state = 'start'
    start = StateView(
        'akademy_matriculation.wizmatriculation.create.start', 
        "akademy_matriculation.act_matriculation_wizard_from", [
            Button(string=u'Cancel', state='end', icon='tryton-cancel'),
            Button(string=u'Enroll', state='matriculation', icon='tryton-save')
        ]
    )
    matriculation = StateTransition()

    def transition_matriculation(self):       
        if (self.start.is_candidate == True):
            MatriculationCreateWzard.student_candidate(self.start.applications.application)
        if (self.start.is_transferred == True):
            MatriculationCreateWzard.student_transferred(self.start.transferred)
                    
        return 'end'
    
    @classmethod
    def student_candidate(cls, application):
        NewStudent = Pool().get('company.student')        
        #MatriculationState = Pool().get('akademy_configuration.matriculation.state')
        
        if len(application.candidate.party.student) > 0:
            MatriculationCreateWzard.candidate_matriculation(
                application, application.candidate.party.student[0], 'candidate')          
        else:
            student_matriculatio = NewStudent.search([
                ('party','=',application.candidate.party),
                ('academic_level','=',application.academic_level),
                ('area','=',application.area),
                ('course','=',application.course)
                ])
            
            if len(student_matriculatio) <= 0:   
                state = 'enrolled'             
                Matriculation = NewStudent(
                    state = state, #matriculation_state[0],
                    course = application.course,
                    area = application.area,
                    academic_level = application.academic_level,
                    start_date = date.today(),
                    party = application.candidate.party,
                )
                Matriculation.save()

                MatriculationCreateWzard.candidate_matriculation(
                    application, Matriculation, 'candidate')        
        
    @classmethod
    def candidate_matriculation(cls, application, matriculation, mt_type):
        ClasseStudent = Pool().get('akademy_classe.classe.student')
        Classes = Pool().get('akademy_classe.classes')
        
        if len(application.area.studyplan) <= 0:
            raise UserError("Unfortunately, it is not possible to enroll the student, as the area does not yet have study plans.")

        get_classes = Classes.search([
            ('lective_year', '=', application.lective_year),
            ('classe', '=', application.course_classe.classe),
            ('studyplan.course', '=', application.course),
            ])

        if len(get_classes) > 0:           
            if (get_classes[0].max_student != len(get_classes[0].classe_student)):  
                matriculation_state = 'enrolled'
                MatriculationStudent = MatriculationCreateWzard.create_student_matriculation(
                    application, ClasseStudent, matriculation_state, mt_type, 
                    matriculation, get_classes[0], get_classes[0].classe, 0
                )
                
                if len(application.area.studyplan[0].studyplan_discipline) > 0:
                    MatriculationCreateWzard.discipline_matriculation(
                        MatriculationStudent, get_classes[0].studyplan.studyplan_discipline) 

                else:
                    raise UserError("Unfortunately, it is not possible to enroll the student because the limit of available places has already been exceeded.")
            else:
                raise UserError("It is not possible to enroll the student or candidate because the class is already full.")
        else:
            raise UserError("It was not possible to enroll the student or candidate because a class has not yet been created.")      
    
    @classmethod
    def create_student_matriculation(cls, classe_student, ClasseStudent, matriculation_state, matriculation_type, student, classes, classe, update):   
        if matriculation_state:
            student_matriculation = ClasseStudent.save_student_matriculation(
                matriculation_state, matriculation_type, student, classes)
            MatriculationCreateWzard.update_student_company_state(student, classe, matriculation_state)        

        if update:                
            MatriculationCreateWzard.update_student_state(classe_student)

        return student_matriculation

    @classmethod
    def update_student_company_state(cls, company_student, classe, matriculation_state): 
        company_student.state = matriculation_state
        company_student.classe = classe
        company_student.save()

    @classmethod
    def update_student_state(cls, classe_student):
        #MatriculationState = Pool().get('akademy_configuration.matriculation.state')
        classe_student.state = "approved" #MatriculationState.search([('name', '=', "Aprovado(a)")])
        classe_student.save()

    @classmethod
    def discipline_matriculation(cls, student, studyplan_discipline):
        StudentClasseDiscipline = Pool().get('akademy_classe.classe.student.discipline')        
        
        if len(studyplan_discipline) > 0:
            for discipline in studyplan_discipline:
                student_matriculation = StudentClasseDiscipline.search([
                    ('classe_student', '=', student), 
                    ('studyplan_discipline', '=', discipline)
                    ])                
                if len(student_matriculation) <= 0: 
                    discipline_modality = 'in_person' 
                    mt_state = 'enrolled' 

                    ClasseStudentDiscipline.save_student_discipline(
                        student, discipline, mt_state, discipline_modality)                    
        else:
            raise UserError("It is not possible to assign subjects to the student, as he did not fail any of the subjects taken in the class.  "+
                student[0].classes.name+" during the school year of "+student[0].classes.lective_year.name+
                " and is already enrolled in those subjects.")
    
    @classmethod
    def student_transferred(cls, student):  
        Studyplan = Pool().get('akademy_configuration.studyplan')        
        get_studyplan = Studyplan.search([
            ('area', '=', student.area),
            ('course', '=', student.course)
            ])
                
        #EQUIVALENCY PROCESS
        for studyplan in get_studyplan:
            discipline_required = []
            student_discipline_possitive = []
            get_student_transferred_discipline = []
            discipline_positive = []

            for studyplan_discipline in studyplan.studyplan_discipline:   
                if len(student.student_transfer_discipline) > 0: 
                    for student_transfer_discipline in student.student_transfer_discipline:
                            if (student_transfer_discipline.discipline ==  studyplan_discipline.discipline):
                                if (studyplan_discipline.average > student_transfer_discipline.average):                                
                                    get_student_transferred_discipline.append(studyplan_discipline)                                    
                                else:                                   
                                    student_discipline_possitive.append(student_transfer_discipline)                                    
                                    discipline_positive.append(studyplan_discipline)                                    
                else:
                    get_student_transferred_discipline.append(studyplan_discipline)

                if studyplan_discipline.state.required == True:
                    discipline_required.append(studyplan_discipline)
                    
            if len(discipline_required) == len(student_discipline_possitive):                            
                pass
            else:
                # Check if the student is enrolled
                if len(student.student.classe_student) < 1:
                    MatriculationCreateWzard.student_transfer_classe(
                        studyplan, get_student_transferred_discipline, 
                        discipline_positive, student_discipline_possitive, 
                        student)

    @classmethod
    def student_transfer_classe(cls, studyplan, get_student_transferred_discipline, discipline_positive, student_discipline_possitive, student):
        Classes = Pool().get('akademy_classe.classes')
        ClasseStudent = Pool().get('akademy_classe.classe.student')
        Student = Pool().get('company.student')
        MatriculationType = Pool().get('akademy_configuration.matriculation.type')

        for studyplan_discipline in studyplan.studyplan_discipline:
            if studyplan_discipline not in discipline_positive and studyplan_discipline not in get_student_transferred_discipline:                        
                get_student_transferred_discipline.append(studyplan_discipline)
        
        if len(student_discipline_possitive) == 0:
            classe_matriculation = studyplan_discipline.studyplan.classe.classe
        else:
            classe_matriculation = student_discipline_possitive[0].course_classe.classe
        
        get_classes = Classes.search([
            ('lective_year', '=', student.lective_year),
            ('classe', '=', classe_matriculation),
            ('studyplan', '=', studyplan)
            ])
 
        if len(student.student.classe_student) > 0:
            raise UserError("Unfortunately, it is not possible to enroll the student because the student is already enrolled.")                    
        else:
            if len(get_classes) > 0:                        
                get_class_student = ClasseStudent.search(
                    [
                        ('student', '=', student.student),
                        ('classes', '=', get_classes[0])
                    ]
                ) 
                
                if len(get_class_student) > 0:
                    raise UserError("The student "+student.student.party.name+" already exists in the institution, please verify his enrollment in the "+get_class_student[0].classes.name+".")                        
                else:
                    if (get_classes[0].max_student != len(get_classes[0].classe_student)):
                        matriculation_state = 'enrolled'
                        matriculation_type = 'transfer'

                        MatriculationCreateWzard.create_student_matriculation(
                            student, ClasseStudent, matriculation_state, 
                            matriculation_type, student.student, get_classes[0], 
                            get_classes[0].classe, 0)                                                        
                        student_matriculation = Student.search([
                            ('party','=',student.student.party),
                            ('academic_level','=',student.student.academic_level),
                            ('area','=',student.student.area),
                            ('course','=',student.student.course)
                            ])
                        
                        if len(student_matriculation) > 0:
                            student_matriculation[0].state = matriculation_state
                            student_matriculation[0].save()
                                                    
                        MatriculationCreateWzard.student_transferred_discipline(
                            student.student.classe_student, 
                            get_student_transferred_discipline, get_classes[0].studyplan)
                    else:
                        raise UserError("Unfortunately, it is not possible to enroll the student because the limit of available places has already been exceeded.")
            else:
                raise UserError("Unfortunately, it is not possible to enroll the student because no available class was found.")           
    
    @classmethod
    def student_transferred_discipline(cls, student, discipline_negative, studyplan):        
        if len(studyplan.studyplan_discipline) > 0:
            if len(discipline_negative) > 0:
                MatriculationCreateWzard.association_discipline(student, discipline_negative)
            else:
                raise UserError("Unfortunately, it's not possible to assign subjects to a student because there are no failing grades.")        
        else:
            raise UserError("Unfortunately, it is not possible to assign courses to the student because a study plan compatible with their academic background was not found.")

    @classmethod
    def association_discipline(cls, student, studyplan_discipline):
        StudentClasseDiscipline = Pool().get('akademy_classe.classe.student.discipline')                 
        if len(studyplan_discipline) > 0:
            for discipline in studyplan_discipline:                
                student_matriculation = StudentClasseDiscipline.search([
                    ('classe_student', '=', student[0]), 
                    ('studyplan_discipline', '=', discipline)
                    ])                
                if len(student_matriculation) <= 0:  
                    matriculation_state = 'enrolled'
                    discipline_modality = 'all'                    
           
                    ClasseStudentDiscipline.save_student_discipline(
                        student[0], discipline, matriculation_state, discipline_modality)
                    
        else:
            raise UserError("It is not possible to assign subjects to the student, as he did not fail any subject in the class. "+
                student[0].classes.name+" during the school year of "+student[0].classes.lective_year.name+
                " and is already enrolled in those subjects.")
 

class AssociationDisciplineCreateWzardStart(ModelView):
    'AssociationDiscipline CreateStart'
    __name__ = 'akademy_matriculation.wizassociatiodiscipline.create.start'

    classes = fields.Many2One(
        'akademy_classe.classes', 'Class', required=True,
        help="An association will be made between the students in this class and the subjects in the study plan."
    )


class AssociationDisciplineCreateWzard(Wizard):
    'AssociationDiscipline CreateWzard'
    __name__ = 'akademy_matriculation.wizassociatiodiscipline.create'

    start_state = 'start'
    start = StateView(
        'akademy_matriculation.wizassociatiodiscipline.create.start', 
        "akademy_matriculation.act_associationdiscipline_wizard_from", [
            Button(string=u'Cancel', state='end', icon='tryton-cancel'),
            Button(string=u'Associate', state='association', icon='tryton-save')
        ]
    )
    association = StateTransition()

    def transition_association(self):
        StudentDiscipline = Pool().get('akademy_classe.classe.student.discipline')        
        state_student = ['waiting', 'suspended', 'cancelled', 'transferred', 'failed']
        list_matriculation = 0

        for classe_student in self.start.classes.classe_student:
            if classe_student.state not in state_student:
                for studyplan_discipline in self.start.classes.studyplan.studyplan_discipline:
                    matriculaton_discipline = StudentDiscipline.search(
                        [('classe_student', '=', classe_student), ('studyplan_discipline', '=', studyplan_discipline)]
                    )
                    
                    if (len(matriculaton_discipline) < 1):
                        list_matriculation = 1
                        discipline_modality = 'all'

                        matriculaton = StudentDiscipline(
                            classe_student = classe_student,
                            studyplan_discipline = studyplan_discipline,
                            state = classe_student.state,
                            modality = discipline_modality
                        )
                        matriculaton.save()

        if list_matriculation == 0:
            raise UserError("We were unable to associate subjects with the students in this class. Please check if the class has any students or if all subjects have already been associated.")		
          
        return 'end'  


class ApplicationAvaliationCreateWzardStart(ModelView):
    "ApplicationAvaliation CreateStart"
    __name__ = 'akademy_matriculation.wizapplication_avaliation.create.start'

    applications_criteria = fields.Many2One(
        'akademy_configuration.application.criteria', 'Admission criteria',       
        required=True, help="Choose your admission criteria.")


class ApplicationAvaliationCreateWzard(Wizard):
    "ApplicationAvaliation Create"
    __name__ = 'akademy_matriculation.wizapplication_avaliation.create'

    start_state = 'start'
    start = StateView(
        'akademy_matriculation.wizapplication_avaliation.create.start',
        "akademy_matriculation.act_application_avaliation_wizard_from", [
            Button(string=u'Cancel', state='end', icon='tryton-cancel'),
            Button(string=u'Evaluate', state='application_avaliation', icon='tryton-save')
        ]
    )
    application_avaliation = StateTransition()

    def transition_application_avaliation(self):
        Criteria = Pool().get('akademy_configuration.application.criteria')
        ApplicationResult = Pool().get('akademy_matriculation.applications.result') 
        Applications = Pool().get('akademy_matriculation.applications') 
        
        candidate_application = Applications.search([
            ('phase', '=', self.start.applications_criteria.phase),
            ('lective_year', '=', self.start.applications_criteria.lective_year),
            ('academic_level', '=', self.start.applications_criteria.academic_level),
            ('area', '=', self.start.applications_criteria.area),
            ('course', '=', self.start.applications_criteria.course)
            ])
        
        if self.start.applications_criteria.phase.start <= date.today() <= self.start.applications_criteria.phase.end:
            if len(candidate_application) >= 1:
                
                order = [('age', 'ASC'), ('candidate.average', 'ASC')]
                application_sort = sort(candidate_application, order)
                
                for element in application_sort:                
                    phase_admission = element.phase
                    ApplicationCriteria = Criteria.search([('course', '=', element.course), ('phase', '=', phase_admission)])                  
                    
                    if len(ApplicationCriteria) > 0:
                        Result = ApplicationResult.search([
                            ('result', '=', 'admitted'), 
                            ('application_criteria', '=', ApplicationCriteria[0]),
                            ('lective_year', '=', element.lective_year)
                            ]) 
                    
                        limit = len(Result)
                        if len(ApplicationCriteria) >= 1:
                            if ApplicationCriteria[0].student_limit >= limit: 
                                if len(element.result) <= 1:
                                    Applications.application_admission_avaliation(
                                        ApplicationCriteria, element, 
                                        ApplicationResult, element.lective_year)
                                else:
                                    raise UserError("It was not possible to evaluate the candidate's application. "+element.candidate.party.name+
                                                    ", please check if there is already a reviewed application for this.")
                            else:
                                raise UserError("It was not possible to evaluate the application because it has already exceeded the limit established by the institution.")
                        else:
                            raise UserError("We were unable to evaluate your application. Please check if you meet at least one eligibility criterion in this phase "+
                                            element.phase.name+", for the course of "+element.course.name+".\nOr if the candidate "+element.candidate.party.name+
                                            ", You are already enrolled in this course and this academic year.")
                    else:
                        raise UserError("The application could not be evaluated because no admission criteria could be found,"+
                                        " for the phase "+self.start.applications_criteria.phase.name)
        else:
            raise UserError("It was not possible to evaluate the application because it is no longer within the application evaluation period of this phase. "+
                            self.start.applications_criteria.phase.name)    
        return 'end'        
