#!/usr/bin/env python
# encoding: utf-8

import json
import getopt
import os
import re
import requests
import time
from usage import Usage


NOTEBOOK_LEFT = '# '
PARAGRAPH_TITLE_LEFT = '#' * 60 + ' ' * 3
PARAGRAPH_TITLE_RIGHT = ' ' * 3 + '#' * 60


class CommandInvoker(object):
    """
    Singleton Pattern:
    - Inheritance object
    - Override __new__
    """
    
    __instance = None

    def __new__(cls, *args, **keys):
        if cls.__instance is None:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def __init__(self):
        self.__commands = {}

    def mapping(self, command_type, command_name):
        def receive(cls):
            if command_type not in self.__commands:
                self.__commands[command_type] = {}
            c = cls()
            c.set_command_name(command_name)
            self.__commands[command_type][command_name] = c
        return receive

    def execute(self, command_type, command_name, config, argv):
        self.__commands[command_type][command_name].execute(config, argv)

    def list_command_types(self):
        return self.__commands.keys()

    def list_commands(self, command_type):
        return self.__commands[command_type].keys()


invoker = CommandInvoker()


class BaseCommand(object):
    def __init__(self):
        self.api_url = None
        self.http_header = {'Connection': 'close'}
        self.cookies = {}
        self.help_message = ""
        self.longopts = []
        self.vars = {}
        self.command_name = "unknown"

    def set_command_name(self, command_name):
        self.command_name = command_name

    def prepare(self, argv):
        try:
            longopts = ["help"] + ["%s=" % v for v in self.longopts]
            opts, args = getopt.getopt(argv, "h", longopts=longopts)
        except getopt.error, msg:
            raise Usage(self.help_message)

        longopts = ["--%s" % v for v in self.longopts]
        # option processing
        for option, value in opts:
            if option in ("-h", "--help"):
                raise Usage(self.help_message)
            if option in longopts:
                #Convert --option_name to option_name
                self.vars[option[2:]] = value

    def execute(self, config, argv):
        self.init_http_request(config)
        self.prepare(argv)
        self.do_execute()

    def requests_get(self, url):
        return requests.get(url, headers=self.http_header, cookies=self.cookies)

    def requests_post(self, url, data={}):
        return requests.post(url, headers=self.http_header, cookies=self.cookies, data=data)

    def requests_delete(self, url):
        return requests.delete(url, headers=self.http_header, cookies=self.cookies)

    def requests_put(self, url):
        return requests.put(url, headers=self.http_header, cookies=self.cookies)

    def init_http_request(self, config):
        self.api_url = config['zeppelin_url']
        if config.get('zeppelin_auth', False):
            data = {
                'userName': config.get('zeppelin_user', ''),
                'password': config.get('zeppelin_password', '')
            }
            r = requests.post("%s/api/login" % self.api_url, data=data)
            ret, status_code, json_context = self.build_api_result(r)
            if ret:
                self.cookies = r.cookies
            else:
                raise Exception('status_code:%s, auth failed.' % status_code)

    def do_execute(self):
        print "Unsupported command"

    def build_api_result(self, response):
        if response.status_code == 200 or response.status_code == 201:
            return True, response.status_code, response.json()
        else:
            return False, response.status_code, ""


class NotebookCommand(BaseCommand):

    def __init__(self):
        BaseCommand.__init__(self)
        self.longopts = self.longopts + ["notebook"]
        self.help_message = """zdari notebook %s --notebook ${notebook_id|$notebook_name}"""
        self.notebook_id = None

    def prepare(self, argv):
        self.help_message = self.help_message % self.command_name
        BaseCommand.prepare(self, argv)
        notebook_id = self.vars.get('notebook', None)
        if notebook_id is None:
            raise Usage(self.help_message)
        self.notebook_id = self.build_available_notebook_id(notebook_id)

    def build_available_notebook_id(self, notebook_id):
        """
        if given notebook_id is name of notebook, convert it.
        """
        notebooks = self.list_notebook()
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

    def build_available_paragraph_id(self, notebook_id, paragraph_id):
        """
        if given paragraph_id is title of paragraph, convert it.
        """
        json_context = self.get_notebook(notebook_id)
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

    def fetch_paragraph_status(self, notebook_id, paragraph_id):
        r = self.requests_get("%s/api/notebook/%s/paragraph/%s" % (self.api_url, notebook_id, paragraph_id))
        return self.build_api_result(r)

    def list_notebook(self):
        r = self.requests_get("%s/api/notebook" % self.api_url)
        ret, status_code, json_context = self.build_api_result(r)
        if ret:
            return json_context['body']
        else:
            raise Exception('status_code:%s' % status_code)

    def get_notebook(self, notebook_id):
        r = self.requests_get("%s/api/notebook/%s" % (self.api_url, notebook_id))
        ret, status_code, json_context = self.build_api_result(r)
        if not ret:
            raise Exception('status_code:%s' % status_code)
        return json_context

    def get_job_status_list(self, notebook_id):
        r = self.requests_get("%s/api/notebook/job/%s" % (self.api_url, notebook_id))
        return self.build_api_result(r)


@invoker.mapping("notebook", "print")
class PrintNotebookCommand(NotebookCommand):
    def __init__(self):
        NotebookCommand.__init__(self)

    def do_execute(self):
        json_context = self.get_notebook(self.notebook_id)
        print json.dumps(json_context['body'], indent=4, sort_keys=True)


@invoker.mapping("notebook", "run")
class RunNotebookCommand(NotebookCommand):
    def __init__(self):
        NotebookCommand.__init__(self)
        self.longopts = self.longopts + ["paragraph", "parameters"]
        self.help_message = "%s [--paragraph ${paragraph_id|$paragraph_name}] [--parameters ${json}]" % self.help_message
        self.parameters = {}
        self.paragraph_id = None

    def prepare(self, argv):
        NotebookCommand.prepare(self, argv)
        self.paragraph_id = self.vars.get('paragraph', None)
        self.parameters = self.vars.get('parameters', {})
        if self.notebook_id is None:
            raise Usage(self.help_message)

    def do_execute(self):
        if self.paragraph_id is None:
            ret, status_code, json_context = self.get_job_status_list(self.notebook_id)
            for job in json_context['body']:
                self.run_paragraph_job(self.notebook_id,
                                       job['id'],
                                       self.parameters)
        else:
            self.run_paragraph_job(self.notebook_id,
                                   self.build_available_paragraph_id(self.notebook_id, self.paragraph_id),
                                   self.parameters)

    def run_paragraph_job(self, notebook_id, paragraph_id, parameters):
        r = self.requests_post("%s/api/notebook/job/%s/%s" % (self.api_url, notebook_id, paragraph_id), data=parameters)
        ret, status_code, json_context = self.fetch_paragraph_status(notebook_id, paragraph_id)
        while ret and json_context['body']['status'] in ['RUNNING', 'PENDING']:
            if not ret:
                raise Exception('status=%s' % status_code)
            time.sleep(1)
            ret, status_code, json_context = self.fetch_paragraph_status(notebook_id, paragraph_id)
        print 'status=%s, notebook=%s, paragraph=%s' % (json_context['body']['status'], notebook_id, paragraph_id)
        if json_context['body']['status'] != 'FINISHED':
            raise Exception(json_context['body']['result']['msg'])


@invoker.mapping("notebook", "delete")
class DeleteNotebookCommand(NotebookCommand):
    def do_execute(self):
        r = self.requests_delete("%s/api/notebook/%s" % (self.api_url, self.notebook_id))
        ret, status_code, json_context = self.build_api_result(r)
        if not ret:
            raise Exception('status_code:%s' % status_code)


@invoker.mapping("notebook", "create")
class CreateNotebookCommand(NotebookCommand):
    def __init__(self):
        BaseCommand.__init__(self)
        self.longopts = self.longopts + ["filepath"]
        self.help_message = """zdari notebook %s --filepath ${filepath}"""
        self.filepath = ""

    def prepare(self, argv):
        self.help_message = self.help_message % self.command_name
        BaseCommand.prepare(self, argv)
        self.filepath = self.vars.get('filepath', None)
        if self.filepath is None:
            raise Usage(self.help_message)

    def do_execute(self):
        with open(self.filepath, 'r') as f:
            context = f.read()
            context = self.convert_format(self.filepath, context)
            self.check_duplicated_name_notebook(context)
            r = self.requests_post("%s/api/notebook" % self.api_url, data=context)
            ret, status_code, json_context = self.build_api_result(r)
            if ret:
                print "Create notebook: %s" % json_context['body']
            else:
                raise Exception('status_code:%s' % status_code)

    def convert_format(self, notebook_file, context):
        filename, file_extension = os.path.splitext(notebook_file)
        if file_extension == ".json":
            return context
        elif file_extension == ".nb":
            return self.parse_notebook_to_json(context)
        else:
            raise Exception("Unknown filename extension: %s, only support .json or .nb" % file_extension)

    def check_duplicated_name_notebook(self, context):
        notebooks =self.list_notebook()
        json_context = json.loads(context)
        for notebook in notebooks:
            if notebook['name'].lower() == json_context['name'].lower():
                raise Exception("Notebook name duplicated: %s" % json_context['name'])

    def parse_notebook_to_json(self, context):
        vaild_char_pattern = r'.'
        m = re.search(r'^# (%s+?)\n' % vaild_char_pattern, context)
        if m is None: raise Exception("Cannot parse notebook name")
        notebook_name = m.group(1).strip()
        titles = re.findall(r'%s(%s+?)%s\n' % (PARAGRAPH_TITLE_LEFT, vaild_char_pattern, PARAGRAPH_TITLE_RIGHT),
                            context)
        paragraphs = []
        for title in titles:
            if title in [k for k, v in paragraphs]:
                raise Exception("Duplicated paragraph name: %s" % title)
            m = re.search(r'%s%s%s\n(.*?)($|\n%s)' % (
                PARAGRAPH_TITLE_LEFT,
                title,
                PARAGRAPH_TITLE_RIGHT,
                PARAGRAPH_TITLE_LEFT),
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


@invoker.mapping("notebook", "save")
class SaveNotebookCommand(NotebookCommand):
    def __init__(self):
        NotebookCommand.__init__(self)
        self.longopts = self.longopts + ["filepath"]
        self.help_message = "%s --filepath $filepath" % self.help_message

    def prepare(self, argv):
        NotebookCommand.prepare(self, argv)
        self.filepath = self.vars.get('filepath', None)
        if self.filepath is None:
            raise Usage(self.help_message)

    def build_paragrapgs_string(self, paragraphs):
        context = ""
        no_title_index = 1
        for paragraph in paragraphs:
            title = paragraph.get('title', None)
            if title is None:
                title = 'undefine_%s' % no_title_index
                no_title_index = no_title_index + 1
            if 'text' in paragraph:
                context = "%s\n%s%s%s\n%s" % (
                context, PARAGRAPH_TITLE_LEFT, title, PARAGRAPH_TITLE_RIGHT, paragraph['text'])
        return context

    def do_execute(self):
        json_context = self.get_notebook(self.notebook_id)
        notebook = json_context['body']
        notebook_context = "%s%s\n%s" % (
            NOTEBOOK_LEFT,
            notebook['name'],
            self.build_paragrapgs_string(notebook['paragraphs'])
        )
        with open(self.filepath, 'w') as f:
            f.write(unicode(notebook_context).encode('utf_8'))


@invoker.mapping("notebook", "list")
class ListNotebookCommand(NotebookCommand):
    def __init__(self):
        NotebookCommand.__init__(self)
        self.longopts = self.longopts + ["list"]

    def prepare(self, argv):
        try:
            NotebookCommand.prepare(self, argv)
        except:
            pass

    def do_execute(self):
        if self.notebook_id is None:
            for notebook in self.list_notebook():
                print "id:[%s], name:[%s]" % (notebook['id'], notebook['name'])
        else:
            ret, status_code, json_context = self.get_job_status_list(self.notebook_id)
            if ret:
                for job in json_context['body']:
                    print "id:[%s], status:[%s]" % (job['id'], job['status'])
            else:
                raise Exception('status_code:%s' % status_code)


class InterpreterCommand(BaseCommand):

    def __init__(self):
        BaseCommand.__init__(self)
        self.longopts = self.longopts + ["interpreter"]
        self.help_message = """zdari interpreter %s --interpreter ${interpreter_id|$interpreter_name}"""
        self.interpreter_id = "Unknown"

    def prepare(self, argv):
        self.help_message = self.help_message % self.command_name
        BaseCommand.prepare(self, argv)
        interpreter_id = self.vars.get('interpreter', None)
        if interpreter_id is None:
            raise Usage(self.help_message)
        self.interpreter_id = self.build_available_interpreter_id(interpreter_id)

    def build_available_interpreter_id(self, interpreter_id):
        """
        if given interpreter_id is name of interpreter, convert it.
        """
        interpreters = self.list_interpreter()
        if interpreter_id in [v['id'] for v in interpreters]:
            return interpreter_id
        elif interpreter_id.lower() in [v['name'].lower() for v in interpreters]:
            candidates = [v for v in interpreters if v['name'].lower() == interpreter_id.lower()]
            if len(candidates) != 1:
                raise Exception('Interpreter name %s duplicated, please check it.' % interpreter_id)
            else:
                return candidates[0]['id']
        else:
            raise Exception('Unavailable interpreter id:%s' % interpreter_id)

    def list_interpreter(self):
        r = self.requests_get("%s/api/interpreter/setting" % self.api_url)
        ret, status_code, json_context = self.build_api_result(r)
        if ret:
            return [ {'id':v['id'], 'name':v['name']} for v in json_context['body']]
        else:
            raise Exception('status_code:%s' % status_code)


@invoker.mapping("interpreter", "list")
class ListInterpreterCommand(InterpreterCommand):
    def __init__(self):
        BaseCommand.__init__(self)
        self.longopts = self.longopts + ["list"]
        self.help_message = """zdari notebook %s"""

    def prepare(self, argv):
        pass

    def do_execute(self):
        interpreters = self.list_interpreter()
        for interpreter_name in interpreters:
            print "id:[%s], name:[%s]" % (interpreter_name['id'], interpreter_name['name'])


@invoker.mapping("interpreter", "restart")
class RestartCommand(InterpreterCommand):
    def do_execute(self):
        r = self.requests_put("%s/api/interpreter/setting/restart/%s" % (self.api_url, self.interpreter_id))
        ret, status_code, json_context = self.build_api_result(r)
        if not ret:
            raise Exception('status_code:%s' % status_code)