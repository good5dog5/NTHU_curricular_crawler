#!/usr/bin/env python3
# Jordan huang<good5dog5@gmail.com>

import re
import os
from os.path import join as join
import sys
import subprocess

from urllib.request import urlopen
import requests
from requests_futures.sessions import FuturesSession

from lxml import html, etree
from crawler.crawler import crawl_course, crawl_dept
from crawler.course import gen_cou_codes_dict, course_from_syllabus

try:
    from crawler.decaptcha import Entrance, DecaptchaFailure
except ImportError:
    Entrance = None

import config as cfg
import csv 
import logging

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
                return response
        raise EmptyResponse(url)
    function.__name__ = request_function.__name__
    return function

get = with_retry(requests.get)
post = with_retry(requests.post)

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


def chinese_word_only(text):

    # trim digits,letters and newline
    pattern = "[A-Za-z0-9\[\`\~\!\@\#\$\^\&\*\(\)\=\|\{\}\'\:\;\'\,\[\]\.\<\>\/\?\~\！\@\#\\\&\*\%\n\ ]" 
    return re.sub(pattern,"", text)


def get_course_no_list(treeObj):
    results = treeObj.findall(".//table/tr[@class='class3']/td[1]/div[@align='center']")
    return results

def gen_file_name(ys, cou_dict):

    dept = cfg.cou_codes[re.sub("[0-9]", "", cou_dict['no'].strip())]
    return "-".join(s for s in [ys, dept, cou_dict['no'], cou_dict['name_zh']]).replace("/", "-")

def syllabus_from_curriculum(acixstore, cou_no):
    data = { 'ACIXSTORE': acixstore, 'c_key': cou_no }
    req = get(cfg.course_url['syllabus'], params=data)
    req.encoding = "cp950"
    return req

def cou_code_2_curriculum(session, acixstore, cou_code, auth_num, ys):

    return  session.post(
        cfg.course_url['curriculum'],
        data = {
            'ACIXSTORE' : acixstore,
            'YS' : ys,
            'cond': 'b',
            'dept' : cou_code,
            'auth_num': auth_num })

def download_syllabus_file(path, req, cou_dict, filename):
    
    fName = ""

    if cou_dict['has_attachment']:

        fName = "".join([filename, ".pdf"])
        full_path = join(path, fName)
        pdf_url = "https://www.ccxp.nthu.edu.tw/" + cou_dict['attachment_url'][0]
        res = get(pdf_url)

        with open(full_path,"wb") as pdf:
            pdf.write(res.content)

        print ("Create {0}".format(fName))

    else: 
        fName = "".join([filename, ".txt"])
        full_path = join(path, fName)

        with open(full_path, "w") as txt:
            txt.write(cou_dict["syllabus"])

        print ("Create {0}".format(fName))
        
    return fName

def keywordAnalyser(fname):

    with open(fname, 'r') as f:
        content = f.read().replace('\n', '')
        wordfreq = [len(re.findall(keyword, content)) for keyword in keyword_list]
        print(wordfreq)

    return OrderedDict(zip(keyword_list, wordfreq))

if __name__ == '__main__':

    acixstore, auth_num = get_auth_pair(cfg.course_url['curriculum_entry'])

    with FuturesSession(max_workers=1) as session:

        for year_semester in sorted(cfg.year_semester_dict.keys()):

            folder = join("./syllabus_download", cfg.year_semester_dict[year_semester])
            if not os.path.exists(folder):
                os.makedirs(folder)

            log = open( join(folder, "log"), "w")
            log_csv = open( join(folder, "log.csv"), "w")

            for cou_code in cfg.cou_codes.keys():

                curriculum = cou_code_2_curriculum(session, acixstore, cou_code, auth_num, year_semester) 
                curriculum_req = curriculum.result()
                curriculum_req.encoding = "cp950"
                curriculum_text = html.fromstring(curriculum_req.text, parser=etree.HTMLParser())

                course_no_list   = get_course_no_list(curriculum_text)
                for no in course_no_list:

                    if no.text in cfg.id_2_pass_list:
                        print("{0} been passed".format(no.text))
                        continue

                    syllabus_req = syllabus_from_curriculum(acixstore, no.text)
                    cou_dict = course_from_syllabus(syllabus_req.text)
                    syllabus_file_name = gen_file_name(cfg.year_semester_dict[year_semester], cou_dict)
                    # print(cfg.cou_codes[re.sub("[0-9]", "", cou_dict['no'].strip())], file=log)

                    fName = download_syllabus_file(folder, syllabus_req, cou_dict, syllabus_file_name )
                    print("{0:>10} {1:>30} {2:>50}".format(cfg.cou_codes[cou_code], cou_dict['name_zh'], fName), file=log)

                    w = csv.writer(log_csv, delimiter=',')

                    keyword_freq_list = keywordAnalyser(join(str(folder),fName))
                    data = [cfg.cou_codes[cou_code], cou_dict['name_zh'], '', fName] + keyword_freq_list
                    w.writerow(data)


            log.close()
            log_csv.close()

    


