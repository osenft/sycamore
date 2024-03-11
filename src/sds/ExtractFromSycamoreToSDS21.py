import argparse
from datetime import datetime
import os
import pandas
# import re
import logging
import sys

# append the path of the parent directory
sys.path.append("..")
sys.path.append(".")

from lib import Generators
from lib import SycamoreRest
from lib import SycamoreCache

DATE_FORMAT = '%Y-%m-%d'

class CleverCreator:

    def __init__(self, args):
        self.school_id = args.school_id
        self.cache_dir = args.cache_dir
        self.output_dir = args.output_dir

        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)
        elif not os.path.isdir(self.output_dir):
            raise InvalidOutputDir('output_dir="{}" is not a directory'.format(self.output_dir))

        print('Initializing cache')
        rest = SycamoreRest.Extract(school_id=self.school_id, token=args.security_token)
        self.sycamore = SycamoreCache.Cache(rest=rest, cache_dir=self.cache_dir, reload=args.reload_data)

    def generate(self):
        print('Generating output')
        schools = self.generateOrgs()
        schools.to_csv(
            os.path.join(self.output_dir, 'orgs.csv'),
            index=False)

        students = self.generateUsers()
        students.to_csv(
            os.path.join(self.output_dir, 'users.csv'),
            index=False,
            date_format=DATE_FORMAT)

        roles = self.generateRoles()
        roles.to_csv(
            os.path.join(self.output_dir, 'roles.csv'),
            index=False,
            date_format=DATE_FORMAT)

        classes = self.generateClasses()
        classes.to_csv(
            os.path.join(self.output_dir, 'classes.csv'),
            index=False,
            date_format=DATE_FORMAT)

        enrollments = self.generateEnrollments()
        enrollments.to_csv(
            os.path.join(self.output_dir, 'enrollments.csv'),
            index=False)

        academicSessions = self.generateAcademicSessions()
        academicSessions.to_csv(
            os.path.join(self.output_dir, 'academicSessions.csv'),
            index=False,
            date_format=DATE_FORMAT)

        courses = self.generateCourses()
        courses.to_csv(
            os.path.join(self.output_dir, 'courses.csv'),
            index=False,
            date_format=DATE_FORMAT)

        relationships = self.generateRelationships()
        relationships.to_csv(
            os.path.join(self.output_dir, 'relationships.csv'),
            index=False)

    def _strToDate(self, dateStr: str) -> datetime.date:
        return datetime.strptime(dateStr, '%Y-%m-%d') if dateStr else None

    def _isValidFamilyContact(self, sycFamilyContact) -> bool:
        #if sycFamilyContact['PrimaryParent'] != 1:
        #    return False

        if not sycFamilyContact['Email']:
            return False

        if not sycFamilyContact['FirstName']:
            return False

        if not sycFamilyContact['LastName']:
            return False

        return True

    def _appendFamilyContactUser(self, contactId, sycFamilyContact, phoneField=None):
        if phoneField and not sycFamilyContact[phoneField]:
            return None

        sdsUser = {}
        sdsUser['sourcedId'] = contactId
        sdsUser['username'] = sycFamilyContact['Email']
        sdsUser['familyName'] = sycFamilyContact['LastName'].strip()
        sdsUser['givenName'] = sycFamilyContact['FirstName'].strip()
        sdsUser['email'] = sycFamilyContact['Email']
        if phoneField:
            sdsUser['phone'] = Generators.createE164PhoneNumber(sycFamilyContact[phoneField], sycamore_contact_id=contactId)

        return sdsUser

    def generateUsers(self):
        sdsUsers = pandas.DataFrame(columns=[
            'sourcedId',
            'username',
            'familyName',
            'givenName',
            'activeDirectoryMatchId',
            'email',
            'phone',
            'sms',
            'userNumber',
            ])

        # Add family contacts
        for index, sycFamilyContact in self.sycamore.get('family_contacts').iterrows():
            # Email, First Name and Last Name are required in SDS, so skip contacts without it
            if (not self._isValidFamilyContact(sycFamilyContact)):
                continue

            # Try cell phone first, then work phone, then home phone and finally no phone number
            sdsUser = self._appendFamilyContactUser(index, sycFamilyContact, 'CellPhone')
            if not sdsUser:
                sdsUser = self._appendFamilyContactUser(index, sycFamilyContact, 'WorkPhone')
            if not sdsUser:
                sdsUser = self._appendFamilyContactUser(index, sycFamilyContact, 'HomePhone')
            if not sdsUser:
                sdsUser = self._appendFamilyContactUser(index, sycFamilyContact)

            if not sdsUser:
                print('Could not generate user for family contact {}'.format(index))
            sdsUsers.loc[str(index)] = pandas.Series(data=sdsUser)

        # Add students
        for index, _sycStudent in self.sycamore.get('students').iterrows():
            sycStudentDetails = self.sycamore.get('student_details').loc[index]

            if sycStudentDetails['Grade'] is None:
                print('Skipping student "{}" with empty grade'.format(index))
                continue

            emailAddress = Generators.createStudentEmailAddress(
                sycStudentDetails['FirstName'], sycStudentDetails['LastName'],
                include_domain=True)

            sdsUser = {}
            sdsUser['sourcedId'] = index
            sdsUser['username'] = emailAddress
            sdsUser['familyName'] = sycStudentDetails['LastName']
            sdsUser['givenName'] = sycStudentDetails['FirstName']
            sdsUser['activeDirectoryMatchId'] = emailAddress
            sdsUser['email'] = emailAddress
            sdsUser['phone'] = None
            sdsUser['sms'] = None
            sdsUser['userNumber'] = index

            sdsUsers.loc[index] = pandas.Series(data=sdsUser)


        # Add teachers
        for index, sycEmployee in self.sycamore.get('employees').iterrows():
            if sycEmployee['Position'] != 'Teacher' and sycEmployee['Position'] != 'Substitute':
                continue
            if sycEmployee['Active'] != 1:
                continue
            if sycEmployee['Current'] != 1:
                continue

            sdsUser = {}
            sdsUser['sourcedId'] = index
            emailAddress = Generators.createTeacherEmailAddress(
                sycEmployee['FirstName'], sycEmployee['LastName'], sycEmployee['Email1'],
                include_domain=True)
            sdsUser['username'] = emailAddress
            sdsUser['familyName'] = sycEmployee['LastName']
            sdsUser['givenName'] = sycEmployee['FirstName']
            sdsUser['activeDirectoryMatchId'] = emailAddress
            sdsUser['email'] = emailAddress
            sdsUser['phone'] = None
            sdsUser['sms'] = None
            sdsUser['userNumber'] = index

            sdsUsers.loc[index] = pandas.Series(data=sdsUser)

        return sdsUsers.drop_duplicates()

    def generateRoles(self):
        sdsRoles = pandas.DataFrame(columns=[
            'userSourcedId',
            'orgSourcedId',
            'role',
            'sessionSourcedIds',
            'grade',
            'isPrimary',
            'roleStartDate',
            'roleEndDate',
            ])

        # Add students
        for index, _sycStudent in self.sycamore.get('students').iterrows():
            sycStudentDetails = self.sycamore.get('student_details').loc[index]

            if sycStudentDetails['Grade'] is None:
                print('Skipping student "{}" with empty grade'.format(index))
                continue

            emailAddress = Generators.createStudentEmailAddress(
                sycStudentDetails['FirstName'], sycStudentDetails['LastName'],
                include_domain=True)

            sdsRole = {}
            sdsRole['userSourcedId'] = index
            sdsRole['orgSourcedId'] = self.school_id
            sdsRole['role'] = 'student'

            sdsRoles.loc[index] = pandas.Series(data=sdsRole)


        # Add teachers
        for index, sycEmployee in self.sycamore.get('employees').iterrows():
            if sycEmployee['Position'] != 'Teacher' and sycEmployee['Position'] != 'Substitute':
                continue
            if sycEmployee['Active'] != 1:
                continue
            if sycEmployee['Current'] != 1:
                continue

            sdsRole = {}
            sdsRole['userSourcedId'] = index
            sdsRole['orgSourcedId'] = self.school_id
            sdsRole['role'] = Generators.createUserRole(sycamore_employee_position=sycEmployee['Position'],
                                                        sycamore_employee_id=index)

            sdsRoles.loc[index] = pandas.Series(data=sdsRole)

        return sdsRoles.drop_duplicates()

    def _getCurrentYear(self):
        for index, year in self.sycamore.get('years').iterrows():
            if year['Current'] == '1':
                return self.sycamore.get('years_details').loc[index]
        return None

    def generateClasses(self):
        currentYear = self._getCurrentYear()

        sdsClasses = pandas.DataFrame(columns=[
            'sourcedId',
            'orgSourcedId',
            'title',
            'sessionSourcedIds',
            'courseSourcedId',
            'code',
            ])

        for index, sycClass in self.sycamore.get('classes').iterrows():
            sdsClass = {}
            sdsClass['sourcedId'] = index
            sdsClass['orgSourcedId'] = self.school_id
            sdsClass['title'] = Generators.createSectionName(
                sycClass['Name'], sycClass['Section'])
            sdsClass['sessionSourcedIds'] = currentYear['Name']
            sdsClass['courseSourcedId'] = index
            sdsClass['code'] = index

            sdsClasses.loc[index] = pandas.Series(data=sdsClass)

        return sdsClasses


    def generateEnrollments(self):
        sdsEnrollments = pandas.DataFrame(columns=[
            'classSourcedId',
            'userSourcedId',
            'role',
            ])

        for index, _sycStudent in self.sycamore.get('students').iterrows():
            try:
                sycStudentClassesList = self.sycamore.get('student_classes')
                sycStudentClasses = sycStudentClassesList.loc[sycStudentClassesList['students_id'] == index]
            except KeyError:
                print('Skipping student "{} {}" with no classes'.format(_sycStudent["FirstName"], _sycStudent["LastName"]))
                continue

            if sycStudentClasses is None:
                print('Skipping student "{} {}" with empty classes'.format(_sycStudent["FirstName"], _sycStudent["LastName"]))
                continue

            for studentClassIndex, sycStudentClass in sycStudentClasses.iterrows():
                studentStudentClassIndex = '{}_{}'.format(index, studentClassIndex)
                sdsEnrollment = {}
                sdsEnrollment['classSourcedId'] = studentClassIndex
                sdsEnrollment['userSourcedId'] = index
                sdsEnrollment['role'] = 'student'

                sdsEnrollments.loc[studentStudentClassIndex] = pandas.Series(data=sdsEnrollment)

        return sdsEnrollments

    def generateAcademicSessions(self):
        currentYear = self._getCurrentYear()

        sdsAcademicSessions = pandas.DataFrame(columns=[
            'sourcedId',
            'title',
            'type',
            'schoolYear',
            'startDate',
            'endDate',
            ])

        startDate = self._strToDate(currentYear['Q1.StartDate'])

        sdsAcademicSession = {}
        sdsAcademicSession['sourcedId'] = currentYear['Name']
        sdsAcademicSession['title'] = currentYear['Name']
        sdsAcademicSession['type'] = 'schoolYear'
        sdsAcademicSession['schoolYear'] = startDate.year
        sdsAcademicSession['startDate'] = startDate
        sdsAcademicSession['endDate'] = self._strToDate(currentYear['EndDate'])

        sdsAcademicSessions.loc[currentYear['Name']] = pandas.Series(data=sdsAcademicSession)

        return sdsAcademicSessions


    def generateCourses(self):
        currentYear = self._getCurrentYear()

        sdsCourses = pandas.DataFrame(columns=[
            'sourcedId',
            'orgSourcedId',
            'title',
            'code',
            'schoolYearSourcedId',
            'subject',
            'grade',
            ])

        for index, sycClass in self.sycamore.get('classes').iterrows():
            sdsCourse = {}
            sdsCourse['sourcedId'] = index
            sdsCourse['orgSourcedId'] = self.school_id
            sdsCourse['title'] = sycClass['Name']
            sdsCourse['code'] = index
            sdsCourse['schoolYearSourcedId'] = currentYear['Name']
            sdsCourse['subject'] = '24039' # "World language"
            sdsCourse['grade'] = None

            sdsCourses.loc[index] = pandas.Series(data=sdsCourse)

        return sdsCourses


    def generateRelationships(self):
        sdsRelationships = pandas.DataFrame(columns=[
            'userSourcedId', # the student
            'relationshipUserSourcedId',
            'relationshipRole',
            ])

        sycFamilyContacts = self.sycamore.get('family_contacts')
        sycFamilyStudents = self.sycamore.get('family_students')

        for familyIndex, sycFamily in self.sycamore.get('families').iterrows():
            for contactIndex, sycFamilyContact in sycFamilyContacts.loc[sycFamilyContacts['families_id'] == familyIndex].iterrows():
                # Email is the lookup key, so skip contacts without it
                if not self._isValidFamilyContact(sycFamilyContact):
                    continue

                for studentIndex in sycFamilyStudents.loc[sycFamilyStudents['families_id'] == familyIndex].index.values:
                    sdsRelationship = {}
                    sdsRelationship['userSourcedId'] = studentIndex
                    sdsRelationship['relationshipUserSourcedId'] = contactIndex
                    sdsRelationship['relationshipRole'] = Generators.createRelationshipRole(
                        sycamore_relationship=sycFamilyContact['Relation'],
                        sycamore_contact_id=contactIndex)

                    sdsRelationships.loc[str(studentIndex)+"_"+str(contactIndex)] = (
                        pandas.Series(data=sdsRelationship))

        return sdsRelationships.drop_duplicates()

    def _getSchool(self) -> pandas.core.series.Series:
        sycSchools = self.sycamore.get('school')
        if len(sycSchools.index) != 1:
            raise KeyError('Should have 1 school, but found {}'.format(len(sycSchools.index)))
        return sycSchools.iloc[0]

    def generateOrgs(self):
        sdsOrgs = pandas.DataFrame(columns=[
            'sourcedId',
            'name',
            'type',
            'parentSourcedId',
            ])

        sycSchool = self._getSchool()

        sdsOrg = {}
        sdsOrg['sourcedId'] = self.school_id
        sdsOrg['name'] = sycSchool['Name']
        sdsOrg['School_number'] = self.school_id
        sdsOrg['type'] = 'school'
        sdsOrg['parentSourcedId'] = None

        sdsOrgs.loc[self.school_id] = pandas.Series(data=sdsOrg)

        return sdsOrgs


def parse_arguments():
    parser = argparse.ArgumentParser(description='Extract Family and School Data')
    parser.add_argument('--school', dest='school_id', action='store',
                        type=int, required=True, help='Sycamore school ID')
    parser.add_argument('--token', dest='security_token', action='store',
                        required=True, help='Sycamore security token')
    parser.add_argument('--cache', dest='cache_dir', action='store',
                        required=True, help='Cache directory')
    parser.add_argument('--reload', dest='reload_data', action='store_true',
                        help='Whether to reload data')
    parser.add_argument('--out', dest='output_dir', action='store',
                        required=True, help='Output directory')
    parser.set_defaults(reload_data=False)
    return parser.parse_args()

if __name__ == "__main__" :
    logging.basicConfig(level=logging.INFO)
    args = parse_arguments()
    creator = CleverCreator(args)
    creator.generate()
    print('Done')

