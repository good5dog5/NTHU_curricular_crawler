import configparser
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),".."))

def get_config(section, option, filename='nthu_course.cfg'):
    '''Return a config in that section'''
    try:
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(ROOT_DIR+ '/config/' + filename)
        return config.get(section, option)

    except Exception as ex:
        # no config found
        return None


def get_config_section(section, filename='nthu_course.cfg'):
    '''Return all config in that section'''
    try:
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(ROOT_DIR+ '/config/' + filename)
        return dict(config.items(section))
    except Exception as ex:
        # no config found
        print(ex)
        return {}

if __name__== '__main__':

    crawler_config      = get_config_section('crawler')
