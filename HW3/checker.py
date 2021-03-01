import re
from datetime import datetime


def email_checker(source_email):
    found_email = re.search('[\w\.-]+@[\w\.-]+(\.[\w]+)+', source_email)
    email = found_email.group(0) if found_email else None
    return email


def date_checker(date_string):
    now = datetime.now()
    current_year = now.year

    if date_string is not None:
        try:
            date_sign = re.match(r'\d{2}.\d{2}.\d{4}', date_string).group(0)

            parsed_date = re.findall(r'\d+', date_sign)

            date_parts_checked_set = set()
            day, month, year = map(int, parsed_date)

            if 0 < day < 31:
                date_parts_checked_set.add(True)
            else:
                date_parts_checked_set.add(False)

            if 0 < month < 13:
                date_parts_checked_set.add(True)
            else:
                date_parts_checked_set.add(False)

            if (current_year - year) < 70:
                date_parts_checked_set.add(True)
            else:
                date_parts_checked_set.add(False)
            if True in list(date_parts_checked_set) and len(date_parts_checked_set) == 1:
                return True
            else:
                return False

        except (AttributeError, TypeError):
            return False
    else:
        return None
