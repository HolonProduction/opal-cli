import re


def get_ajax_url(id: str, markup: str) -> str:
    """ Extract the ajax url for a certain targeted element. May not work reliable as the ajax url for a target may be loaded through another ajax url """

    #ajax_regex = re.compile(R'{\s*"u"\s*:\s*"(?P<url>[^"]*)"(\s*,\s*"[^"]+"\s*:\s*"[^,]*"\s*)*\s*,\s*"c"\s*:\s*"' + id)
    #ajax_regex = re.compile(R'{\s*"u"\s*:\s*"(?P<url>[^"]*)"(\s*,\s*"[^"]+"\s*:\s*"[^,]*"\s*)*\s*,\s*"c"\s*:\s*"')
    m = re.search(R'{\s*"u"\s*:\s*"(?P<url>[^"]*)"(\s*,\s*"[^"]+"\s*:\s*"[^,]*"\s*)*\s*,\s*"c"\s*:\s*"' + id,  markup)
    if not m:
        raise "Ajax target not found"
    return m.group("url")


AJAX_BASE_URL_REGEX = re.compile(R'Wicket\.Ajax\.baseUrl="(?P<url>[^)]+)";')
def get_ajax_base_url(markup: str) -> str:
    """ Extracts the ajax base url for the Wicket-Ajax-BaseURL header. """

    m = AJAX_BASE_URL_REGEX.search(markup)
    if not m:
        return "."
    return m.group("url")
