"""Makim class for containers"""
from copy import deepcopy
import sys
from pathlib import Path
import warnings
import yaml

try:
    from sh import sh as shell_sh
except Exception:
    shell_sh = None

try:
    from sh import bash as shell_bash
except Exception:
    shell_bash = None

try:
    from sh import zsh as shell_zsh
except Exception:
    shell_zsh = None


class Makim:
    args: object | None = None
    config_file: str = ''
    config_data: dict = {}
    shell_app: object | None = None
    shell_args: list = []
    group_name: str = 'default'
    group_data: dict = {}
    target_name: str = ''
    target_data: dict = {}

    def _call_shell_app(self, *args):
        return self.shell_app(
            *self.shell_args,
            *args,
            _out=sys.stdout,
            _err=sys.stderr,
        )

    def _check_config_file(self):
        return Path(self.config_file).exists()

    def _verify_target_conditional(self, conditional):
        breakpoint()

    def _verify_args(self):
        if not self._check_config_file():
            raise Exception('[config] Config file .makim.yaml not found.')

    def _verify_config(self):
        if not len(self.config_data['groups']):
            raise Exception('No target groups found.')

    def _load_config_data(self):
        with open(self.config_file, 'r') as f:
            self.config_data = yaml.safe_load(f)

    def _load_group_target_name(self):
        if '.' in self.args['target']:
            self.group_name, self.target_name = self.args['target'].split('.')
            return
        self.group_name = 'default'
        self.target_name = self.args['target']

    def _load_target_data(self):
        self.target_data = self.group_data['targets'][self.target_name]

    def _load_shell_app(self):
        if self.config_data['shell'] == 'bash':
            self.shell_app = shell_bash
        elif self.config_data['shell'] == 'sh':
            self.shell_app = shell_sh
        elif self.config_data['shell'] == 'zsh':
            self.shell_app = zsh
        else:
            raise Exception(
                f'"{self.config_data["shell"]}" not supported yet.'
            )

        if self.shell_app is None:
            raise Exception(f'"{self.config_data["shell"]}" not found.')

    def _filter_group_data(self):
        groups = self.config_data['groups']

        if self.group_name == 'default' and len(groups) == 1:
            self.group_data = groups[0]
            self.group_name = groups[0]['name']
            return

        for g in groups:
            if g['name'] == self.group_name:
                self.group_data = g
                return

        raise Exception(
            f'The given group target "{self.group_name}" was not found in the '
            'configuration file.'
        )

    def _load_shell_args(self):
        self._filter_group_data()

        # if hasattr(self.config_data, 'env-file'):
        #     self.shell_args.extend(['--env-file', self.group_data['env-file']])
        self.shell_args.extend(['-c'])

    # run commands

    def _run_dependencies(self, args: dict):
        if (
            'dependencies' not in self.target_data
            or not self.target_data['dependencies']
        ):
            return

        makin_dep = deepcopy(self)
        args_dep = deepcopy(args)

        for dep_data in self.target_data['dependencies']:
            args_dep['target'] = dep_data['target']
            makin_dep.run(args_dep)

    def _run_command(self):
        cmd = self.target_data['run'].strip().replace('\n', ' && ')
        self._call_shell_app(cmd, [])

    # public methods

    def load(self, config_file: str):
        self.config_file = config_file
        self._load_config_data()
        self._verify_config()
        self._load_shell_app()

    def run(self, args: dict):
        self.args = args

        # setup
        self._verify_args()
        self._load_group_target_name()
        self._load_shell_args()
        self._load_target_data()

        # commands
        if 'if' in self.target_data and not self._verify_target_conditional(
            self.target_data['if']
        ):
            return warnings.warn(
                f'{args["target"]} not executed. '
                'Condition (if) not satisfied.'
            )

        self._run_dependencies(args)
        self._run_command()