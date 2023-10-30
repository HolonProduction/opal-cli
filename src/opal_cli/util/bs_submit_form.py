from bs4 import Tag
import requests
import urllib


class NotAForm(Exception):
    pass


def submit(self: Tag, session: requests.Session, url: str, **argv):
    if self.name != "form":
        raise NotAForm()

    submitter_found = False
    data = {}
    for inp in self.select("input"):
        if inp.get("type") == "submit":
            submitter_found = True
        if inp.has_attr("name"):
            data[inp.get("name")] = inp.get("value", "")
    
    if not submitter_found:
        for button in self.select("button"):
            if button.get("type") == "submit" or button.has_attr("submit"):
                submitter_found = True
                if button.has_attr("name"):
                    data[button.get("name")] = button.get("value", "")
                break
    
    if not submitter_found and self.has_attr("id"):
        submitter = self.find_parent("html").select_one(f"button[form={self.get('id')}]")
        if submitter and submitter.has_attr("name"):
            data[submitter.get("name")] = submitter.get("value", "")
    
    data = {**data, **argv}

    destination = urllib.parse.urljoin(url, self.get("action"))

    requester = session if session else requests

    if self.get("action") == "get":
        return requester.get(destination, params=data)
    elif self.get("method") == "post" or self.get("method") == "":
        return requester.post(destination, data=data)
    else:
        print(f"Unsupported form method {self.get('method')}.")
        return None


Tag.submit = submit
