#!/usr/bin/env python3
# Jordan huang<good5dog5@gmail.com>


import os
import sys
import subprocess

from urllib.request import urlopen

from itertools import zip_longest
import requests
import lxml.html
import re


def xpath0(element, xpath):
    result = element.xpath(xpath)
    assert len(result) == 1, result
    return result[0]

def extract_multirow_text(element):
    return re.sub(
        r'\n{4,}',
        '\n' * 3,
        '\n'.join(
            s.strip() for s in element.itertext()
        )
    )

def coursedata_from_syllabus(filename):

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

    html = open(filename, "r").read()
    document = lxml.html.fromstring(html)

    def extract_text(element, joiner=''):
        return joiner.join(element.itertext()).strip()

    def xpath_text(xpath, joiner=''):
        return extract_text(xpath0(document, xpath), joiner=joiner)

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
        'has_attachment': bool(
            document.xpath('/html/body/div/table[4]/tr[2]/td/div/font[1]/a')),
    }

if __name__ == '__main__':

    info = coursedata_from_syllabus("./syllabus.html")
    print(info.items())
    print(info.get("syllabus", "None"))
    
