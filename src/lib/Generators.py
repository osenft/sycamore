from datetime import datetime
from datetime import timedelta
import logging
import phonenumbers

STUDENT_DOMAIN = '@student.gssb.org'
TEACHER_DOMAIN = '@gssb.org'

def __formatFirstName(name: str) -> str:
    return (
        name
            .strip()
            .replace(' ', '')
            .replace('\'', '')
            )

def __formatLastName(name: str) -> str:
    name = (
        name
            .strip()
            .replace('\'', '')
            .replace('ä', 'ae')
            .replace('ö', 'oe')
            .replace('ü', 'ue')
            .replace('ß', 'ss')
            )

    if name[:4] in ('van ', 'Van ', 'von ', 'Von '):
        return name.replace(' ', '')
    elif name.startswith('Freiin von '):
        return name.replace('Freiin von ', 'Von').replace(' ','-')
    elif ' zu ' in name:
        return name.replace(' ', '')
    elif ' Zu ' in name:
        return name.replace(' ', '')
    elif name.startswith('de '):
        return name.replace(' ', '')
    elif name.startswith('De '):
        return name.replace(' ', '')
    elif ' Nguyen' in name:
        return name.replace(' ', '')
    elif ' nguyen' in name:
        return name.replace(' ', '')
    else:
        return name.replace(' ', '-')

def __createEmailAddress(first_name: str, last_name: str, domain: str) -> str:
    return (__formatFirstName(first_name) + '.'
            + __formatLastName(last_name)
            + domain)

def createStudentEmailAddress(first_name: str, last_name: str, include_domain: bool = True) -> str:
    return __createEmailAddress(first_name, last_name, STUDENT_DOMAIN if include_domain else '')

def createTeacherEmailAddress(first_name: str, last_name: str, email: str, include_domain: bool = True) -> str:
    if email.strip().endswith('@gssb.org'):
        if include_domain:
            return email.strip()
        else:
            return email.strip().replace('@gssb.org', '')

    return __createEmailAddress(first_name, last_name, TEACHER_DOMAIN if include_domain else '')

def createStudentName(first_name: str, last_name: str) -> str:
    return last_name + ', ' + first_name

def createTeacherName(first_name: str, last_name: str) -> str:
    return last_name + ', ' + first_name

def createCityStateZip(city: str, state: str, zipcode: str) -> str:
    return city + ', ' + state + ' ' + zipcode

def createClassName(class_name: str, teacher_first: str, teacher_last: str) -> str:
    result = class_name
    if ("DSD I" in class_name):
        result = result.replace(' Jahr', 'J')
    if ("/" in class_name):
        result = result.replace('/', '.')
    return result

GRADE_MAP = {
    'Preschool': 'Prekindergarten',
    'Kindergarten': 'Kindergarten',
    '1st': '1',
    '2nd': '2',
    '3rd': '3',
    '4th': '4',
    '5th': '5',
    '6th': '6',
    '7th': '7',
    '8th': '8',
    '9th - DSD 1': '9',
    '10th - DSD 2 y1': '10',
    '11th - DSD 2 y2': '11',
    '10th (no DSD 2)': '12',
}

def createGrade(sycamore_grade: str) -> str:

    if sycamore_grade is None:
        logging.warn("Translating None grade to ''.")
        return ''

    if sycamore_grade in GRADE_MAP:
        return GRADE_MAP[sycamore_grade]

    logging.warn("Could not translate grade '" + sycamore_grade + "'.")
    return sycamore_grade

def createSectionName(sycamore_class_name: str, sycamore_section: str) -> str:
    if not sycamore_section:
        return str(sycamore_class_name)
    return str(sycamore_class_name) + '-' + str(sycamore_section)

def createTermName(sycamore_term_name: str):
    if sycamore_term_name == 'First':
        return 'S1'
    if sycamore_term_name == 'Second':
        return 'S2'
    if sycamore_term_name == 'Full Year':
        return 'Year'

    logging.warn("Could not translate term '" + sycamore_term_name + "'.")
    return sycamore_term_name

def createTermStart(sycamore_term_name: str, s1_start: datetime.date, s2_start: datetime.date, _year_end: datetime.date) -> datetime.date:
    if sycamore_term_name == 'First':
        return s1_start
    if sycamore_term_name == 'Second':
        return s2_start
    if sycamore_term_name == 'Full Year':
        return s1_start

    logging.warn("Could not translate term '" + sycamore_term_name + "'.")
    return s1_start

def createTermEnd(sycamore_term_name: str, s1_start: datetime.date, s2_start: datetime.date, year_end: datetime.date) -> datetime.date:
    if sycamore_term_name == 'First':
        return s2_start - timedelta(days=7)
    if sycamore_term_name == 'Second':
        return None
    if sycamore_term_name == 'Full Year':
        return None

    logging.warn("Could not translate term '" + sycamore_term_name + "'.")
    return None

NAME_TO_PERIOD_MAP = {
    'Beginner\'s Class': 'Adlt',
    'Conversation Class German': 'Adlt',
}

def createPeriod(sycamore_class_name: str) -> str:
    if sycamore_class_name in NAME_TO_PERIOD_MAP:
        return NAME_TO_PERIOD_MAP[sycamore_class_name]
    return 'GP'

def createTeacherId(sycamore_primary_staff_id: str) -> str:
    if not sycamore_primary_staff_id or sycamore_primary_staff_id == '0':
        return ''
    return sycamore_primary_staff_id

def createRole(sycamore_relationship: str):
    if not isinstance(sycamore_relationship, str):
        # Default value
        return 'Parent'

    sycamore_relationship = sycamore_relationship.strip()

    if sycamore_relationship == 'Mother':
        return 'Parent'
    if sycamore_relationship == 'Father':
        return 'Parent'
    if sycamore_relationship == 'Parents':
        return 'Parent'
    if sycamore_relationship == 'Grandmother':
        return 'Relative'
    if sycamore_relationship == '':
        return 'Parent'
    if sycamore_relationship == 'Aunt':
        return 'Relative'
    if sycamore_relationship == 'Close Friend':
        return 'Other'
    if sycamore_relationship == 'Colleague':
        return 'Other'
    if sycamore_relationship == 'Grandfather':
        return 'Relative'
    if sycamore_relationship == 'Grandparents':
        return 'Relative'
    if sycamore_relationship == 'Nanny':
        return 'Aide'
    if sycamore_relationship == 'Not Defined':
        return 'Other'
    if sycamore_relationship == 'Relative':
        return 'Relative'
    if sycamore_relationship == 'Sibling':
        return 'Relative'
    if sycamore_relationship == 'Uncle':
        return 'Relative'

    print('Unsupported relationship "%s"' % (sycamore_relationship))
    return 'Parent'

def createUserRole(sycamore_employee_position: str, sycamore_employee_id: str):
    if not isinstance(sycamore_employee_position, str):
        # Default value
        return 'teacher'

    sycamore_employee_position = sycamore_employee_position.strip()

    if sycamore_employee_position == 'Teacher':
        return 'teacher'
    if sycamore_employee_position == 'Substitute':
        return 'substitute'

    print('Unsupported employee position "%s" for employeee "%s"' %
        (sycamore_employee_position, sycamore_employee_id))
    return 'other'

def createRelationshipRole(sycamore_relationship: str, sycamore_contact_id: str):
    if not isinstance(sycamore_relationship, str):
        # Default value
        return 'parent'

    sycamore_relationship = sycamore_relationship.strip()

    if sycamore_relationship == 'Mother':
        return 'parent'
    if sycamore_relationship == 'Father':
        return 'parent'
    if sycamore_relationship == 'Stepmother':
        return 'parent'
    if sycamore_relationship == 'Stepfather':
        return 'parent'
    if sycamore_relationship == 'Parents':
        return 'parent'
    if sycamore_relationship == 'Grandmother':
        return 'relative'
    if sycamore_relationship == '':
        return 'parent'
    if sycamore_relationship == 'Aunt':
        return 'relative'
    if sycamore_relationship == 'Close Friend':
        return 'other'
    if sycamore_relationship == 'Colleague':
        return 'other'
    if sycamore_relationship == 'Grandfather':
        return 'relative'
    if sycamore_relationship == 'Grandparents':
        return 'relative'
    if sycamore_relationship == 'Nanny':
        return 'aide'
    if sycamore_relationship == 'Not Defined':
        return 'other'
    if sycamore_relationship == 'Relative':
        return 'relative'
    if sycamore_relationship == 'Sibling':
        return 'relative'
    if sycamore_relationship == 'Uncle':
        return 'relative'
    if sycamore_relationship == 'Partner':
        return 'guardian'
    if sycamore_relationship == 'DayCare Provider':
        return 'aide'
    if sycamore_relationship == 'Helper':
        return 'aide'
    if sycamore_relationship == 'Student':
        return 'other'

    print('Unknown relationship "%s" for contact "%s"' %
        (sycamore_relationship, sycamore_contact_id))
    return 'other'

def createPhoneNumber(phone: str) -> str:
    return (
        phone.replace("-", "")
          .replace("(","")
          .replace(")","")
          .replace(" ","")
          .strip())

def createE164PhoneNumber(phone: str, sycamore_contact_id: str) -> str:
    try:
        parsed_phone = phonenumbers.parse(phone, region="US")
    except phonenumbers.phonenumberutil.NumberParseException:
        parsed_phone = None

    if not parsed_phone or not phonenumbers.is_valid_number(parsed_phone):
        print('Invalid phone number format "%s" for contact "%s"' % (phone, sycamore_contact_id))
        return None

    return phonenumbers.format_number(parsed_phone, num_format=phonenumbers.PhoneNumberFormat.E164)
