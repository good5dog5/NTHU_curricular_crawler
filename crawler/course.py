#!/usr/bin/env python3
# Jordan huang<good5dog5@gmail.com>


import os
import sys
import subprocess
import requests
import lxml.html
import re
from itertools import zip_longest

from utils.config import get_config_section
from config import course_dict

crawler_config      = get_config_section('crawler')
encoding            = crawler_config['encoding']  # big5 superset

form_url            = crawler_config['form_url']
form_action_url     = crawler_config['form_action_url']
syllabus_url        = crawler_config['syllabus_url']
attachment_url      = crawler_config['attachment_url']
dept_url            = crawler_config['dept_url']


def xpath0(element, xpath):
    result = element.xpath(xpath)
    assert len(result) == 1, result
    return result[0]


def extract_text(element, joiner=''):
    return joiner.join(element.itertext()).replace(" ", "")


def extract_int(element, allow_empty=False):
    text_list = element.xpath('.//text()')
    assert len(text_list) == 1, text_list
    if allow_empty and not text_list[0].strip():
        return None
    return int(text_list[0])


def extract_multirow_text(element):
    return re.sub(
        r'\n{4,}',
        '\n' * 3,
        '\n'.join(
            s.strip() for s in element.itertext()
        )
    )


class EmptyResponse(Exception):
    pass
def with_retry(request_function):
    def function(url, max_retries=32, **kwargs):
        '''
        get a valid response in <max_retries> retries
        change encoding before return
        raises EmptyResponse if not valid
        '''
        for r in range(max_retries):
            response = request_function(url, **kwargs)
            if response.content:
                response.encoding = encoding
                return response
        raise EmptyResponse(url)
    function.__name__ = request_function.__name__
    return function



def get_slfr(text):
    sl, s, fr = text.partition(u'新生保留')
    if not sl:
        return None, 0
    sl = int(sl)
    if fr:
        assert fr[-1] == u'人', fr
        fr = int(fr[:-1])
    else:
        fr = 0
    return sl, fr


get = with_retry(requests.get)
post = with_retry(requests.post)

def curriculum_to_trs(html):
    document = lxml.html.fromstring(html)
    course_trs = document.xpath("//tr[contains(@class, 'class3')]")
    assert len(course_trs) % 2 == 0, len(course_trs)
    return course_trs[::2]


def course_from_tr(main_tr):
    '''
    main_tr -> dict: course data

    data info: ([x] means implemented but disabled)
    no                  text            course number
    name_zh             text            Chinese course name
    name_en             text / None     English course name
    ge_hint             text / None     GE line text
    credit [x]          int             credit
    time [x]            text            time
    rc [x]              text            room & capacity
    teacher             text            teacher name, may contain English
    size_limit          int / None      quota size limit
    fr                  int             quota reserved for freshmen
    note                text            note
    enrollment          int             quota enrollment
    object              text            object
    has_prerequisite    bool            has prerequisite
    '''
    tds = main_tr.xpath('td')
    part = {
        'no': extract_text(tds[0]),
        'credit': extract_int(tds[2]),
        'time': extract_text(tds[3]),
        'room/capacity': extract_text(tds[4]),
        'teacher': extract_text(tds[5]),
        'note': extract_text(tds[7]),
        'enrollment': extract_int(tds[8]),
        'object': extract_text(tds[9]),
    }
    part['size_limit'], part['fr'] = get_slfr(extract_text(tds[6]))
    for key, text in zip_longest(
        ('name_zh', 'name_en', 'ge_hint'),
        tds[1].itertext(),
    ):
        if text is not None:
            text = text.strip()
        part[key] = text
    prerequisite = extract_text(tds[10])
    if prerequisite == u'擋修' or u'先修科目' in prerequisite:
        part['has_prerequisite'] = True
    else:
        assert not prerequisite, 'unknown prerequisite %r' % prerequisite
        part['has_prerequisite'] = False
    return part


def course_from_syllabus(html):
    '''
    syllabus html -> dict: course data

    data info:
    no              text            course number
    name_zh         text            Chinese course name
    name_en         text            English course name
    credit          int             credit
    time            text            time
    room            text            room
    syllabus        text            syllabus, no html
    has_attachment  bool            has attachment

    note: to get the attachment, simply visit:
    https://www.ccxp.nthu.edu.tw/ccxp/INQUIRE/JH/output/6_6.1_6.1.12/<no>.pdf
    where <no> is the course number
    '''
    document = lxml.html.fromstring(html,parser = lxml.etree.HTMLParser())

    def xpath_text(xpath, joiner=''):
        return extract_text(xpath0(document, xpath), joiner=joiner)

    def xpath_int(xpath):
        return extract_int(xpath0(document, xpath))

    def patch_teacher(text):
        '''
        Save only Chinese names for teachers.

        See issue #86.
        '''
        return re.sub(r'\([^)]*\)', '', text)

    return {
        'no': xpath_text('/html/body/div/table[1]/tr[2]/td[2]'),
        'name_zh': xpath_text('/html/body/div/table[1]/tr[3]/td[2]'),
        'name_en': xpath_text('/html/body/div/table[1]/tr[4]/td[2]'),
        'credit': xpath_text('/html/body/div/table[1]/tr[2]/td[4]'),
        'teacher': patch_teacher(xpath_text(
            '/html/body/div/table[1]/tr[5]/td[2]', joiner=', ')),
        'time': xpath_text('/html/body/div/table[1]/tr[6]/td[2]'),
        'room': xpath_text('/html/body/div/table[1]/tr[6]/td[4]', joiner=', '),
        'syllabus': extract_multirow_text(
            xpath0(document, '/html/body/div/table[5]/tr[2]/td')),
        'has_attachment': bool( document.xpath('/html/body/div/table[5]/tr[2]/td/div/font[1]/a')),
        'attachment_url': document.xpath('/html/body/div/table[5]/tr[2]/td/div/font[1]/a/@href')
    }


def get_syllabus(c_key, acixstore):
    return get(syllabus_url, params={'c_key': c_key, 'ACIXSTORE': acixstore})


def get_cou_codes(url):
    html = get(form_url).text
    document = lxml.html.fromstring(html)
    return document.xpath('//select[@name="cou_code"]/option/@value')

def gen_cou_codes_dict(url):
    html = get(form_url).text
    document = lxml.html.fromstring(html)
    # print( document.xpath('//select[@name="cou_code"]/option/@value'))
    print( [x.text for x in document.xpath('//select[@name="cou_code"]/option')])

if __name__ == '__main__':

    course_dict = coursedata_from_syllabus(sys.argv[1])

    Semester = "1051"
    No          = course_dict['no']
    Name        = course_dict['name_zh']
    Syllabus    = course_dict['syllabus']
    Department  = course_code[re.sub("[0-9]", "", No.strip())]

    fileName = "-".join(s for s in [Semester, Department, No, Name])+".txt"

    f = open(fileName, "w")
    f.write(Syllabus)
    
