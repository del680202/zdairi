#!/usr/bin/env python
# encoding: utf-8


import commands
import getopt
import json
import os
import re
import requests
import sys
import time
from datetime import datetime, timedelta


HTTP_HEADER={'Connection':'close'}


#Api call will return ret(True, False) and result(status_code, JSON)
notebook_left = '# '
paragraph_title_left = '#' * 60 + ' ' * 3
paragraph_title_right = ' ' * 3 + '#' * 60

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


def restart_interpreter(api_url, ids):
    for id in ids:
        r = requests.put("%s/api/interpreter/setting/restart/%s" % (api_url, id))
        ret, status_code, json_context = build_api_result(r)
        if ret:
            print "Restart interpreter: %s" % id
        else:
           raise Exception('status_code:%s' % status_code)


def list_interpreter(api_url):
    '''
        Output:
        [(id, name), (id, name)...]
    '''
    result = []
    r = requests.get("%s/api/interpreter/setting" % api_url)
    ret, status_code, json_context = build_api_result(r)
    if ret:
       for interpreter_setting in json_context['body']:
           result.append((interpreter_setting['id'], interpreter_setting['name']))
    else:
       raise Exception('status_code:%s' % status_code)
    return result


def build_available_interpreter_id(api_url, interpreter_id):
    for id, name in list_interpreter(api_url):
        if interpreter_id == name:
            interpreter_id = id
            break 
    return interpreter_id


def build_all_interpretes_ids(api_url):
    return [id for id,name in list_interpreter(api_url)]


def build_api_result(response):
    if response.status_code == 200 or response.status_code == 201:
        return True, response.status_code, response.json()
    else:
        return False, response.status_code, response.json()

def parse_notebook_to_json(context):
    vaild_char_pattern = r'.'
    m = re.search(r'^# (%s+?)\n' % vaild_char_pattern, context)
    if m is None: raise Exception("Cannot parse notebook name")
    notebook_name = m.group(1).strip()
    titles =  re.findall(r'%s(%s+?)%s\n' % (paragraph_title_left, vaild_char_pattern, paragraph_title_right), context)
    paragraphs = []
    for title in titles:
        if title in [k for k, v in paragraphs]:
            raise Exception("Duplicated paragraph name: %s" % title)
        m = re.search(r'%s%s%s\n(.*?)($|\n%s)' % (
                      paragraph_title_left,
                      title,
                      paragraph_title_right,
                      paragraph_title_left),
                      context,
                      re.DOTALL)
        scenario = None
        if m is not None:
            scenario = m.group(1)
            scenario = scenario if len(scenario.strip()) > 0 else None
        if scenario is None:
            raise Exception("Scenario of %s cannot be parsed, please check it." % title)
        paragraphs.append([title, scenario.strip()])

    notebook = {}
    notebook['name'] = notebook_name
    notebook['paragraphs'] = [{'title': v[0], 'text': v[1]} for v in paragraphs]
    return json.dumps(notebook, indent=4)

def convert_format(notebook_file, context):
    filename, file_extension = os.path.splitext(notebook_file)
    if file_extension == ".json":
        return context
    elif file_extension == ".nb":
        return parse_notebook_to_json(context)
    else:
        raise Exception("Unknown filename extension: %s" % file_extension)

def check_duplicated_name_notebook(api_url, context):
    notebooks = list_notebook(api_url)
    json_context = json.loads(context)
    for notebook in notebooks:
        if notebook['name'].lower() == json_context['name'].lower():
            raise Exception("Notebook name duplicated: %s" % json_context['name'])

def build_paragrapgs_string(paragraphs):
    context = ""
    no_title_index = 1
    for paragraph in paragraphs:
        title = paragraph.get('title', None)
        if title is None:
            title = 'undefine_%s' % no_title_index
            no_title_index = no_title_index + 1
        if 'text' in paragraph:
            context = "%s\n%s%s%s\n%s" % (context, paragraph_title_left, title, paragraph_title_right, paragraph['text'])
    return context

def save_notebook(api_url, notebook_id, save_path):
    json_context = get_notebook(api_url, notebook_id)
    notebook = json_context['body']
    notebook_context = "%s%s\n%s" % (
                       notebook_left,
                       notebook['name'],
                       build_paragrapgs_string(notebook['paragraphs'])
                       )

    with open(save_path, 'w') as f:
        f.write(notebook_context)

def create_notebook(api_url, notebook_file):
    with open(notebook_file, 'r') as f:
        context = f.read()
        context = convert_format(notebook_file, context)
        check_duplicated_name_notebook(api_url, context)
        r = requests.post("%s/api/notebook" % api_url, data = context)
        ret, status_code, json_context = build_api_result(r)
        if ret:
           print "Create notebook: %s" % json_context['body']
        else:
           raise Exception('status_code:%s' % status_code)

def list_notebook(api_url):
    r = requests.get("%s/api/notebook" % api_url)
    ret, status_code, json_context = build_api_result(r)
    if ret:
       return json_context['body']
    else:
       raise Exception('status_code:%s' % status_code)

def get_job_status_list(api_url, notebook_id):
    r = requests.get("%s/api/notebook/job/%s" % (api_url, notebook_id))
    return build_api_result(r)

def get_notebook(api_url, notebook_id):
    r = requests.get("%s/api/notebook/%s" % (api_url, notebook_id))
    ret, status_code, json_context = build_api_result(r)
    if not ret:
        raise Exception('status_code:%s' % status_code)
    return json_context

def delete_notebook(api_url, notebook_id):
    r = requests.delete("%s/api/notebook/%s" % (api_url, notebook_id))
    ret, status_code, json_context = build_api_result(r)
    if not ret:
        raise Exception('status_code:%s' % status_code)
    return json_context

def print_notebook(api_url, notebook_id):
    json_context = get_notebook(api_url, notebook_id)
    print json.dumps(json_context['body'], indent=4, sort_keys=True)


def fetch_paragraph_status(api_url, notebook_id, paragraph_id):
    r = requests.get("%s/api/notebook/%s/paragraph/%s" % (api_url, notebook_id, paragraph_id), headers=HTTP_HEADER)
    return build_api_result(r)


def run_paragraph_job(api_url, notebook_id, paragraph_id, parameters):
    r = requests.post("%s/api/notebook/job/%s/%s" % (api_url, notebook_id, paragraph_id),
                      json = parameters, headers=HTTP_HEADER)
    ret, status_code, json_context = fetch_paragraph_status(api_url, notebook_id, paragraph_id)
    while ret and json_context['body']['status'] in ['RUNNING', 'PENDING']:
        if not ret:
            raise Exception('status=%s' % status_code)
        time.sleep(1)
        ret, status_code, json_context = fetch_paragraph_status(api_url, notebook_id, paragraph_id)
    print 'status=%s, notebook=%s, paragraph=%s' % (json_context['body']['status'], notebook_id, paragraph_id)
    if json_context['body']['status'] != 'FINISHED':
        raise Exception(json_context['body']['result']['msg'])


def run_notebook_in_order(api_url, notebook_id, parameters):
    ret, status_code, json_context = get_job_status_list(api_url, notebook_id)
    for job in json_context['body']:
        run_paragraph_job(api_url, notebook_id, job['id'], parameters)


def process_create_command(argv, command, commands):
    notebook_file = None
    api_url = None
    try:
        opts, args = getopt.getopt(argv[2:], "h", ["help", "url=", "notebook="])
    except getopt.error, msg:
        raise Usage(msg)
    # option processing
    for option, value in opts:
        if option in ("-h", "--help"):
            raise Usage(help_message)
        if option in ("--url"):
            api_url = value
        if option in ("--notebook"):
            notebook_file = value

    if api_url is None or notebook_file is None:
        raise Usage('Illegal Argument')
    commands[command][0](api_url, notebook_file)

def process_save_command(argv, command, commands):
    notebook_id = None
    api_url = None
    save_path = None
    try:
        opts, args = getopt.getopt(argv[2:], "h", ["help", "url=", "notebook=", "savepath="])
    except getopt.error, msg:
        raise Usage(msg)
    # option processing
    for option, value in opts:
        if option in ("-h", "--help"):
            raise Usage(help_message)
        if option in ("--url"):
            api_url = value
        if option in ("--notebook"):
            notebook_id = value
        if option in ("--savepath"):
            save_path = value

    if api_url is None or notebook_id is None or save_path is None:
        raise Usage('Illegal Argument')
    notebook_id = build_available_notebook_id(api_url, notebook_id)
    commands[command][0](api_url, notebook_id, save_path)

def build_available_notebook_id(api_url, notebook_id):
    '''
    if given notebook_id is name of notebook, convert it.
    '''
    notebooks = list_notebook(api_url)
    if notebook_id in [v['id'] for v in notebooks]:
        return notebook_id
    elif notebook_id.lower() in [v['name'].lower() for v in notebooks]:
        candidates = [v for v in notebooks if v['name'].lower() == notebook_id.lower()]
        if len(candidates) != 1:
            raise Exception('Notebook name %s duplicated, please check it.' % notebook_id)
        else:
            return candidates[0]['id']
    else:
        raise Exception('Unavailable notebook id:%s' % notebook_id)

def build_available_paragraph_id(api_url, notebook_id, paragraph_id):
    '''
    if given paragraph_id is title of paragraph, convert it.
    '''
    json_context = get_notebook(api_url, notebook_id)
    paragraphs = json_context['body']['paragraphs']
    if paragraph_id in [v['id'] for v in paragraphs]:
        return paragraph_id
    elif paragraph_id.lower() in [v['title'].lower() for v in paragraphs if 'title' in v]:
        candidates = [v for v in paragraphs if 'title' in v and v['title'].lower() == paragraph_id.lower()]
        if len(candidates) != 1:
            raise Exception('Paragraph title %s duplicated, please check it.' % paragraph_id)
        else:
            return candidates[0]['id']
    else:
        raise Exception('Unavailable paragraph id:%s' % paragraph_id)
    sys.exit(0)

def process_notebook_command(argv, command, commands):
    notebook_id = None
    paragraph_id = None
    api_url = None
    try:
        opts, args = getopt.getopt(argv[2:], "h", ["help", "url=", "notebook=", "paragraph="])
    except getopt.error, msg:
        raise Usage(msg)
    # option processing
    for option, value in opts:
        if option in ("-h", "--help"):
            raise Usage(help_message)
        if option in ("--url"):
            api_url = value
        if option in ("--notebook"):
            notebook_id = value
        if option in ("--paragraph"):
            paragraph_id = value

    if api_url is None or notebook_id is None:
        raise Usage('Illegal Argument')

    notebook_id = build_available_notebook_id(api_url, notebook_id)
    if paragraph_id is None:
        commands[command][0](api_url, notebook_id)
    else:
        paragraph_id = build_available_paragraph_id(api_url, notebook_id, paragraph_id)
        commands[command][1](api_url, notebook_id, paragraph_id)


def process_run_command(argv, command, commands):
    notebook_id = None
    paragraph_id = None
    api_url = None
    parameters = {}
    try:
        opts, args = getopt.getopt(argv[2:], "h", ["help", "url=", "notebook=", "paragraph=", "parameters="])
    except getopt.error, msg:
        raise Usage(msg)
    # option processing
    for option, value in opts:
        if option in ("-h", "--help"):
            raise Usage(help_message)
        if option in ("--url"):
            api_url = value
        if option in ("--notebook"):
            notebook_id = value
        if option in ("--paragraph"):
            paragraph_id = value
        if option in ("--parameters"):
            parameters = json.loads(value)

    if api_url is None or notebook_id is None:
        raise Usage('Illegal Argument')

    notebook_id = build_available_notebook_id(api_url, notebook_id)
    if paragraph_id is None:
        commands[command][0](api_url, notebook_id, parameters=parameters)
    else:
        paragraph_id = build_available_paragraph_id(api_url, notebook_id, paragraph_id)
        commands[command][1](api_url, notebook_id, paragraph_id, parameters=parameters)


def process_restart_command(argv, command, commands):
    api_url = None
    interpreter_id = None
    try:
        opts, args = getopt.getopt(argv[2:], "h", ["help", "url=", "interpreter="])
    except getopt.error, msg:
        raise Usage(msg)
    # option processing
    for option, value in opts:
        if option in ("-h", "--help"):
            raise Usage(help_message)
        if option in ("--url"):
            api_url = value
        if option in ("--interpreter"):
            interpreter_id = value

    if api_url is None:
        raise Usage('Illegal Argument')

    interpreter_ids = []
    if interpreter_id is None:
        interpreter_ids = build_all_interpretes_ids(api_url)
    else:
        interpreter_id = build_available_interpreter_id(api_url, interpreter_id)
        if interpreter_id is not None:
            interpreter_ids.append(interpreter_id)
    restart_interpreter(api_url, interpreter_ids)


#command name :  (notebook handler, paragraph handler)
notebook_commands = {'print': (print_notebook, None),
                     'delete': (delete_notebook, None)}
run_commands      = {'run': (run_notebook_in_order, run_paragraph_job)}
create_commands   = {'create': (create_notebook, None)}
save_commands     = {'save': (save_notebook, None)}
restart_commands  = {'restart_interpreter': restart_interpreter}


def main(argv=None):

    if argv is None:
        argv = sys.argv
    try:
        command = argv[1] if len(argv) > 2 else ""
        if command in notebook_commands:
            process_notebook_command(argv, command, notebook_commands)
        elif command in create_commands:
            process_create_command(argv, command, create_commands)
        elif command in run_commands:
            process_run_command(argv, command, run_commands)
        elif command in save_commands:
            process_save_command(argv, command, save_commands)
        elif command in restart_commands:
            process_restart_command(argv, command, restart_commands)
        else:
            raise Usage('Unknown command: %s' % command)

    except Usage, err:
        print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
        print >> sys.stderr, "\t for help use --help"
        return 2


if __name__ == "__main__":
    sys.exit(main())
