#!/usr/bin/env python3

import logging
import re
import subprocess
import tempfile
import io
try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

import lxml.html
import requests
# Python Image Library
from PIL import Image  

try:
    from utils.config import get_config_section
except ImportError:
    captcha_url_base = (
        'https://www.ccxp.nthu.edu.tw/ccxp/INQUIRE/JH/'
        'mod/auth_img/auth_img.php')
else:
    decaptcha_config = get_config_section('decaptcha')
    captcha_url_base = decaptcha_config['captcha_url_base']

logger = logging.getLogger(__name__)


class DecaptchaFailure(Exception):
    pass


def tesseract(path):
    return subprocess.check_output([
        'tesseract',
        path, '-',
        '-psm', '8',
        '-c', 'tessedit_char_whitelist=0123456789', 'nobatch'
    ]).strip()


def tesseract_versions():
    return subprocess.check_output(
        ['tesseract', '--version'],
        stderr=subprocess.STDOUT
    )


def preprocess(b):
    color = Image.open(io.BytesIO(b))
    gray = color.convert('L')
    bw = gray.point(lambda c: (c > 150) * 255, '1')
    fp = io.BytesIO()
    bw.save(fp, 'png')
    return fp.getvalue()


def decaptcha_url(url, params=None):
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmpimg:
        tmpimg.write(preprocess(requests.get(url, params=params).content))
        tmpimg.flush()
        return tesseract(tmpimg.name).replace(b' ', b'')


class Entrance(object):
    def __init__(
        self,
        form_url,
        form_action_url=None,
        page_encoding='cp950',
        captcha_length_hint=3
    ):
        self.form_url = form_url
        self.form_action_url = form_action_url
        if form_action_url is None:
            self.form_action_url = None
        else:
            self.form_action_url = urljoin(form_url, form_action_url)
        self.page_encoding = page_encoding
        self.captcha_length_hint = captcha_length_hint

    @property
    def form_action_url(self):
        try:
            return self._form_action_url
        except AttributeError:
            self._form_action_url = self.guess_form_action_url()
            logger.info(
                'form_action_url not provided, assuming %r',
                self._form_action_url)
            return self._form_action_url

    @form_action_url.setter
    def form_action_url(self, val):
        if val is not None:
            self._form_action_url = val

    def get_key_from_new_form(self, xpath_hint):
        response = requests.get(self.form_url)
        response.encoding = self.page_encoding
        document = lxml.html.fromstring(response.text)
        return document.xpath(xpath_hint)[0].value

    def get_acixstore(self):
        return self.get_key_from_new_form('//input[@name="ACIXSTORE"]')

    def guess_form_action_url(self):
        response = requests.get(self.form_url)
        response.encoding = self.page_encoding
        document = lxml.html.fromstring(response.text, base_url=self.form_url)
        element = document.xpath('//input[@type="submit"]')[0]
        while element is not None:
            element = element.getparent()
            if element.tag == 'form':
                return element.action
        raise DecaptchaFailure('Cannot guess form action url')

    def validate_by_post(self, result):
        acixstore, captcha = result
        response = requests.post(
            self.form_action_url,
            data={
                'ACIXSTORE': acixstore,
                'auth_num': captcha,
            }
        )
        response.encoding = self.page_encoding
        if b'interrupted' in response.content:
            logger.info('%r: %r session is interrupted', *result)
            return False
        elif b'Wrong check code' in response.content:
            logger.info('%r: %r is simply incorrect', *result)
            return False
        else:
            # assume the code is correct if nothing indicates it's not
            logger.info('%r: %r is correct', *result)
            logger.debug('RESPONSE: %r', response.text)
            return True

    def pre_validate(self, captcha, log_hint):
        if not captcha.isdigit():
            logger.info('%r: %r is not a number', log_hint, captcha)
            return False
        if (
            self.captcha_length_hint is not None and
            not len(captcha) == self.captcha_length_hint
        ):
            logger.info(
                '%r: %r does not have length == %i',
                log_hint,
                captcha,
                self.captcha_length_hint
            )
            return False
        return True

    def validate(self, result):
        acixstore, captcha = result
        return (
            self.pre_validate(captcha, acixstore) and
            self.validate_by_post(result)
        )

    def _get_ticket(self):
        acixstore = self.get_acixstore()
        captcha = decaptcha_url(
            captcha_url_base,
            params={'ACIXSTORE': acixstore}
        )
        return acixstore, captcha

    def get_ticket(self, retries=32):
        '''
        returns (acixstore, captcha) pair
        raises DecaptchaFailure if cannot guess captcha in limited retries
        '''
        logger.info('trying acixstore-captcha pair for %r', self.form_url)
        for try_ in range(retries):
            result = self._get_ticket()
            if self.validate(result):
                return result
        raise DecaptchaFailure('Cannot decaptcha for, retries=%i' % retries)



def benchmark(ent, count):
    correct_count = 0
    for try_ in range(count):
        result = ent._get_ticket()
        correct_count += ent.validate(result)
    print(
        '{} of {} correct, ({:.2%})'.format(
            correct_count,
            count,
            float(correct_count) / count
        )
    )


# tesseract availability test
try:
    versions = tesseract_versions()
except (subprocess.CalledProcessError, OSError):
    raise ImportError('%r requires tesseract binary' % __name__)
else:
    major, minor = list(map(
        int,
        versions.splitlines()[0].split()[-1].split(b'.')
    ))[:2]
    # $ tesseract --version
    # tesseract 3.04.00
    #  leptonica-1.72
    #   libgif 5.1.1 : libjpeg 8d (libjpeg-turbo 1.4.1)...
    if (major, minor) < (3, 3):
        raise ImportError('%r requires tesseract >= 3.03' % __name__)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Get a ticket of an acixstore-captcha pair to CCXP'
    )

    parser.add_argument(
        '--form-url',
        help='target form url',
        default='https://www.ccxp.nthu.edu.tw/ccxp/INQUIRE/JH/6/6.2/6.2.9/JH629001.php',  # noqa
    )
    parser.add_argument(
        '--form-action-url',
        help='where to post to validate captcha (auto detect if not provided)',
        default=None
    )
    parser.add_argument(
        '--retries',
        help='max_retries',
        default=32,
        type=int
    )
    parser.add_argument(
        '--quiet',
        help='do not log',
        action='store_true'
    )
    parser.add_argument(
        '--benchmark',
        type=int,
        default=None,
        help='test correct rate',
        metavar='COUNT'
    )

    args = parser.parse_args()

    if not args.quiet:
        logger.setLevel(logging.INFO)
        logger.addHandler(logging.StreamHandler())

    ent = Entrance(
        args.form_url,
        args.form_action_url
    )
    if args.benchmark:
        benchmark(ent, args.benchmark)
    else:
        print(ent.get_ticket(args.retries))

