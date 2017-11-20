#!/usr/bin/env python3
# Jordan huang<good5dog5@gmail.com>

import os
import sys
import subprocess

import re

from crawler.crawler import crawl_course, crawl_dept
from crawler.course import get_cou_codes, course_from_syllabus
try:
    from crawler.decaptcha import Entrance, DecaptchaFailure
except ImportError:
    Entrance = None

import requests
from config import course_code

def get_auth_pair(url):
    if Entrance is not None:
        try:
            return Entrance(url).get_ticket()
        except DecaptchaFailure:
            print('Automated decaptcha failed.')
    else:
        print('crawler.decaptcha not available (requires tesseract >= 3.03).')
    print('Please provide valid ACIXSTORE and auth_num from')
    print(url)
    ACIXSTORE = input('ACIXSTORE: ')
    auth_num = input('auth_num: ')
    return ACIXSTORE, auth_num


class Command():
    args = ''
    help = 'Help crawl the course data from NTHU.'

    def handle(self, *args, **kwargs):
        if len(args) == 0:
            import time
            start_time = time.time()
            cou_codes = get_cou_codes()
            for ys in ['105|20']:
                ACIXSTORE, auth_num = get_auth_pair(
                    'https://www.ccxp.nthu.edu.tw/ccxp/INQUIRE'
                    '/JH/6/6.2/6.2.9/JH629001.php'
                )
                print('Crawling course for ' + ys)
                crawl_course(ACIXSTORE, auth_num, cou_codes, ys)

                ACIXSTORE, auth_num = get_auth_pair(
                    'https://www.ccxp.nthu.edu.tw/ccxp/INQUIRE'
                    '/JH/6/6.2/6.2.3/JH623001.php'
                )
                print('Crawling dept for ' + ys)
                crawl_dept(ACIXSTORE, auth_num, cou_codes, ys)
                print('===============================\n')
            elapsed_time = time.time() - start_time
            print('Total %.3f second used.' % elapsed_time)
        if len(args) == 1:
            if args[0] == 'clear':
                Course.objects.all().delete()
                Department.objects.all().delete()

if __name__ == '__main__':
    # aci, auth = get_auth_pair()
    # print(crawler.course.get_syllabus(ACIXSTORE, "10510EE  152000"))
    # a = Command()
    # a.handle()

    
    res = requests.get(sys.argv[1])
    # print(type(res.encoding))
    res.encoding = "cp950"

    # print(res.text)
    course_dict = course_from_syllabus(res.text)

    Semester = "1051"
    No          = course_dict['no']
    Name        = course_dict['name_zh']
    Syllabus    = course_dict['syllabus']
    Department  = course_code[re.sub("[0-9]", "", No.strip())]

    fileName = "-".join(s for s in [Semester, Department, No, Name])+".txt"

    f = open(fileName, "w")
    f.write(Syllabus)
    print("create {0}".format(fileName))



