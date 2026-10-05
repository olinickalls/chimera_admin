# Helper functions with no particular home
import string

safechars = string.ascii_letters + string.digits + " -_=.[](){}"


def get_safe_filename(in_txt):
    '''
    Remove filesystem unsafe characters
    to allow safe file/dir name creation.
    '''
    filter_generator = filter(lambda c: c in safechars, in_txt)
    safe_str = ''.join([str(elem) for elem in filter_generator])
    return safe_str


def matches_pdf_filter(session, pdf_status):
    if pdf_status == 'yes':
        return bool(session.get('pdf'))
    if pdf_status == 'no':
        return not bool(session.get('pdf'))
    return True
