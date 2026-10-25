# This file is part of SAGE Education.   The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.pool import Pool
from trytond.report import Report
from datetime import date


class ApplicationCriteriaReport(Report):
    __name__ = 'akademy_report.application.criteria.report'

    @classmethod
    def get_context(cls, records, header, data):
        LectiveYear = Pool().get('akademy_configuration.lective.year')
		
        context = super().get_context(records, header, data)
        lective_year = LectiveYear.browse(data['ids'])
        application_criteria = lective_year[0].application_criteria

        context['criteria'] = application_criteria
        context['create_date'] = date.today()
        return context


class CandidatesReport(Report):
	__name__ = 'akademy_report.candidates.report'

	@classmethod
	def get_context(cls, records, header, data):		
		Candidates = Pool().get('akademy_matriculation.candidates')

		context = super().get_context(records, header, data)
		candidate = Candidates.browse(data['ids'])

		context['candidates'] = candidate
		context['create_date'] = date.today()
		return context


class ApplicationResultReport(Report):
	__name__ = 'akademy_report.application.result.report'

	@classmethod
	def get_context(cls, records, header, data):
		LectiveYear = Pool().get('akademy_configuration.lective.year')
		
		context = super().get_context(records, header, data)
		lective_year = LectiveYear.browse(data['ids'])
		application_criterias = lective_year[0].application_criteria
		result = application_criterias
		
		context['result'] = result
		context['create_date'] = date.today()
		return context


class StudentTransferReport(Report):
	__name__ = 'akademy_report.student.transfer.report'

	@classmethod
	def get_context(cls, records, header, data):
		StudentTransfer = Pool().get('akademy_matriculation.student.transfer')

		context = super().get_context(records, header, data)
		student = StudentTransfer.browse(data['ids'])
		
		context['student'] = student
		context['create_date'] = date.today()
		return context


class StudentTransferInternalReport(Report):
	__name__ = 'akademy_report.student.transfer.internal.report'

	@classmethod
	def get_context(cls, records, header, data):
		StudentTransfer = Pool().get('akademy_matriculation.student.transfer')

		context = super().get_context(records, header, data)
		student = StudentTransfer.browse(data['ids'])
		
		context['student'] = student
		context['create_date'] = date.today()
		return context


class EquivalenceDisciplineReport(Report):
	__name__ = 'akademy_report.equivalence.discipline.report'

	@classmethod
	def get_context(cls, records, header, data):
		StudentTransfer = Pool().get('akademy_matriculation.student.transfer')        
		Studyplan = Pool().get('akademy_configuration.studyplan')

		context = super().get_context(records, header, data)
		students = StudentTransfer.browse(data['ids'])

		get_student_equivalence = []
		get_student_discipline = []
		get_studyplan_discipline = []
		discipline_exit = []		

		for student in students:
			if student.internal == True:
				pass
			else:
				get_studyplan = Studyplan.search([
					('area', '=', student.area),
					('course', '=', student.course)
				])  
				
				for studyplan in get_studyplan:
					for studyplan in get_studyplan:
							for studyplan_discipline in studyplan.studyplan_discipline:
								if studyplan_discipline not in discipline_exit:
									discipline_exit.append(studyplan_discipline)
									get_studyplan_discipline.append([
										studyplan_discipline.discipline.name, 
										studyplan.classe.classe.name, 0])								
				
				if len(student.student_transfer_discipline) > 0:
					for student_transfer_discipline in student.student_transfer_discipline:											
						if student_transfer_discipline not in discipline_exit:
							discipline_exit.append(student_transfer_discipline)
							get_student_discipline.append([
								student_transfer_discipline.discipline.name, 
								student_transfer_discipline.course_classe.classe.name, 
								student_transfer_discipline.average])
			
				get_student_equivalence.append(student)
		
		if student.internal == True:
			context['students'] = [student]
			context['discipline'] = []
			context['create_date'] = date.today()
			return context
						
		else:
			student_external = EquivalenceDisciplineReport.student_external_equivalence(
				get_student_equivalence, get_student_discipline, get_studyplan_discipline)
			
			context['students'] = student_external[0]
			context['discipline'] = student_external[1]
			context['create_date'] = date.today()
			return context
	
	@classmethod
	def student_external_equivalence(cls, get_student_equivalence, get_student_discipline, get_studyplan_discipline):
		student_has_discipline = []
		student = []
		discipline = []

		for student_equivalence in get_student_equivalence:				
			student_discipline_exit = []
			student.append(student_equivalence)

			for studyplan_discipline in get_studyplan_discipline:
				st_discipline_state = False
				if studyplan_discipline not in student_discipline_exit:
					student_discipline_exit.append(studyplan_discipline)
					st_discipline_exit = []
					for student_discipline in get_student_discipline:
						if student_discipline not in st_discipline_exit:
							st_discipline_exit.append(student_discipline)
							if (student_discipline[0] == studyplan_discipline[0]) and (student_discipline[1] == studyplan_discipline[1]):									
								student_has_discipline.append(student_discipline)
								discipline.append(student_discipline)
								st_discipline_state = True

					if st_discipline_state == False:
						discipline.append(studyplan_discipline)

			for student_discipline in get_student_discipline:
						if student_discipline not in student_has_discipline:
							discipline.append(student_discipline)
		
		return [student, discipline]
