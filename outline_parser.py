#!/usr/bin/env python3
# Jordan huang<good5dog5@gmail.com>

import os
import sys
import subprocess
from urllib.request import urlopen
from bs4 import BeautifulSoup

# url = sys.argv[1] if len(sys.argv) > 1 else False
soup = BeautifulSoup(open("./syllabus.html"),"lxml")

if __name__ == '__main__':
    print(soup)

