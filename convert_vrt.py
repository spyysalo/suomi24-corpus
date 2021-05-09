#!/usr/bin/env python3

# Convert the VRT format used in the Suomi24 corpus distribution
# (http://urn.fi/urn:nbn:fi:lb-2017021506) to text and other formats.

import sys
import json
import logging
import xml.etree.ElementTree as ET

from hashlib import md5
from collections import namedtuple
from argparse import ArgumentParser


Word = namedtuple('Word', 'word ref lemma lemmacomp pos msd dephead deprel spaces initid lex')


def argparser():
    ap = ArgumentParser()
    ap.add_argument('--jsonl', default=False, action='store_true') 
    ap.add_argument('--tsv', default=False, action='store_true')
    ap.add_argument('file', nargs='+')
    return ap


def is_comment_line(line):
    return line.startswith('<!-- ')


def is_text_start_line(line):
    return line.startswith('<text ')


def is_text_end_line(line):
    return line.startswith('</text>')


def parse_text_line(line):
    line = line.rstrip()
    return ET.fromstring(f'{line}</text>')


def is_paragraph_start_line(line):
    return line.startswith('<paragraph ')


def is_paragraph_end_line(line):
    return line.startswith('</paragraph>')


def parse_paragraph_line(line):
    line = line.rstrip()
    return ET.fromstring(f'{line}</paragraph>')
    

def is_sentence_start_line(line):
    return line.startswith('<sentence ')


def is_sentence_end_line(line):
    return line.startswith('</sentence>')


def parse_sentence_line(line):
    line = line.rstrip()
    return ET.fromstring(f'{line}</sentence>')


def make_id(element):
    return md5(ET.tostring(element)).hexdigest()


def parse_attr_value(string):
    attr_value = {}
    for av in string.split('|'):
        if av and av != '_':
            attr, value = av.split('=', 1)
            attr_value[attr] = value
    return attr_value


def unescape_space(string):
    orig, unescaped = string, []
    while string:
        if string.startswith('\\s'):
            unescaped.append(' ')
            string = string[len('\\s'):]
        elif string.startswith('\\n'):
            unescaped.append('\n')
            string = string[len('\\n'):]
        else:
            logging.warning(f'failed to unescape space: "{orig}"')
            break
    return ''.join(unescaped)


def unescape_text(string):
    string = string.replace('&lt;', '<')
    string = string.replace('&gt;', '>')
    string = string.replace('&amp;', '&')
    return string


def vrt_to_text(fn, options):
    id_, textelem, paraelem, sentelem, strings = None, None, None, None, None
    with open(fn) as f:
        for ln, l in enumerate(f, start=1):
            if is_comment_line(l):
                continue
            elif is_text_start_line(l):
                assert textelem is None
                textelem = parse_text_line(l)
                id_ = make_id(textelem)
                strings = []
            elif is_text_end_line(l):
                assert textelem is not None
                string = ''.join(strings)
                if options.jsonl:
                    data = {
                        'id': id_,
                        'text': string,
                        'meta': { 'sourcemeta': textelem.attrib },
                    }
                    print(json.dumps(data, sort_keys=True, ensure_ascii=False))
                elif not options.tsv:
                    print('-' * 20, id_, '-' * 20)
                    print(string)
                else:
                    encoded = json.dumps(string, ensure_ascii=False)
                    print(f'{id_}\t{encoded}')
                id_, textelem, strings = None, None, None
            elif is_paragraph_start_line(l):
                assert paraelem is None
                paraelem = parse_paragraph_line(l)
            elif is_paragraph_end_line(l):
                assert paraelem is not None
                paraelem = None
            elif is_sentence_start_line(l):
                assert sentelem is None
                sentelem = parse_sentence_line(l)
            elif is_sentence_end_line(l):
                assert sentelem is not None
                sentelem = None
            else:
                fields = l.rstrip('\n').split('\t')
                word = Word(*fields)
                spaces = parse_attr_value(word.spaces)
                if 'SpacesBefore' in spaces:
                    strings.append(unescape_space(spaces['SpacesBefore']))
                    del spaces['SpacesBefore']
                strings.append(unescape_text(word.word))
                if 'SpacesInToken' in spaces:
                    del spaces['SpacesInToken']    # redundant
                if not spaces:
                    strings.append(' ')    # single space by default
                elif 'SpacesAfter' in spaces:
                    strings.append(unescape_space(spaces.get('SpacesAfter')))
                else:
                    assert spaces.get('SpaceAfter') == 'No', spaces


def main(argv):
    args = argparser().parse_args(argv[1:])
    for fn in args.file:
        vrt_to_text(fn, args)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
