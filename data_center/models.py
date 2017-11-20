# -*- coding: utf-8 -*-

from datetime import datetime

attachment_url_format = (
    'https://www.ccxp.nthu.edu.tw/ccxp/INQUIRE/JH/'
    'output/6_6.1_6.1.12/%s.pdf')


class Course():
    """Course database schema"""
    no = None
    code = None
    eng_title = None
    chi_title = None
    note = None
    objective = None
    time = None
    time_token = None
    teacher = None
    room = None
    credit = None
    limit = None
    prerequisite = None
    ys = None
    ge = None
    hit = None
    syllabus = None
    has_attachment = None

    def __str__(self):
        return self.no

    @property
    def attachment_url(self):
        return attachment_url_format % urlquote(self.no)


class Department():
    dept_name = None
    required_course = None
    ys = None

    def __str__(self):
        return self.dept_name


class Announcement():
    TAG_CHOICE = (
        ('Info', '公告'),
        ('Bug', '已知問題'),
        ('Fix', '問題修復'),
    )

    content = None
    time = None
    tag = None

    def __str__(self):
        return '%s|%s' % (self.time, self.tag)

