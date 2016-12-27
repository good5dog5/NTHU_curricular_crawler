#!/usr/bin/env python3
# Jordan huang<good5dog5@gmail.com>

import re
import os
import sys
import subprocess
from bs4 import BeautifulSoup

soup = BeautifulSoup(open("./index_table.html"),"lxml")

def chinese_word_only(text):

    # trim digits,letters and newline
    pattern = "[A-Za-z0-9\[\`\~\!\@\#\$\^\&\*\(\)\=\|\{\}\'\:\;\'\,\[\]\.\<\>\/\?\~\！\@\#\\\&\*\%\n]" 
    return re.sub(pattern,"", text)

if __name__ == '__main__':
    results = soup.findAll("td", {"width" : "20%"})
    for a in results:
        print(chinese_word_only(a.text))
