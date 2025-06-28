from email_validator import validate_email, EmailNotValidError
import re

# email validation -----------
password_condition = r"^(?=.*[a-z])(?=.*\d)(?=.*[@$!%*#?&+])[A-Za-z\d@$!#%*?&+]{4,20}$"
pat = re.compile(password_condition)


def email_checker(email):
    try:
        check = validate_email(email)
        email = check['email']
        return True
    except EmailNotValidError as e:
        print(e)
        return False


# password validation -----------

def password_checker(password):
    passw = re.search(pat, password)
    if passw:
        return True
    else:
        return False