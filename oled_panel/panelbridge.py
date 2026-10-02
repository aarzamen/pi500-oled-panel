"""Optional local PanelBridge control; no root, GPIO, SSH or remote credentials.

Use the enrolled desktop user's existing session bus. A stopped desktop/service
is unavailable, never an implicit request to start a second desktop session.
"""
from __future__ import annotations

import ast
import json
import math
import os
import subprocess

BUS_NAME = 'org.panelbridge.Session1'
OBJECT = '/org/panelbridge/Session1'
ACTIONS = {
    'monitor-start': 'start',
    'monitor-stop': 'stop',
    'monitor-keep': 'confirm_profile',
    'monitor-revert': 'revert_profile',
}


def _profile(value):
    if not isinstance(value, dict):
        return {}
    result = {}
    for name in ('source_width', 'source_height', 'content_fps',
                 'wire_width', 'wire_height', 'wire_fps', 'bitrate_kbps'):
        number = value.get(name)
        if type(number) is int and 0 < number <= 8192:
            result[name] = number
    if type(value.get('rotation')) is int and value['rotation'] in (0, 90, 180, 270):
        result['rotation'] = value['rotation']
    scale = value.get('scale')
    if type(scale) in (int, float) and math.isfinite(scale) and 0.5 <= scale <= 8:
        result['scale'] = scale
    return result


def _trial(value):
    if not isinstance(value, dict) or value.get('kind') != 'profile':
        return None
    seconds = value.get('seconds_remaining')
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 <= seconds <= 3600:
        return None
    return {'kind': 'profile', 'seconds_remaining': seconds,
            'message': str(value.get('message') or '')[:400]}


class PanelBridgeClient:
    def __init__(self, runner=subprocess.run, uid=None):
        self.runner = runner
        self.uid = os.getuid() if uid is None else uid
        if type(self.uid) is not int or self.uid <= 0:
            raise ValueError('PanelBridge control requires the normal desktop user')

    def _call(self, method, *arguments):
        result = self.runner([
            '/usr/bin/gdbus', 'call', '--address', f'unix:path=/run/user/{self.uid}/bus',
            '--dest', BUS_NAME, '--object-path', OBJECT,
            '--method', BUS_NAME + '.' + method, *arguments,
        ], capture_output=True, text=True, timeout=3, check=False)
        if result.returncode:
            raise RuntimeError('Monitor controller unavailable. Start Desktop, then retry.')
        if len(result.stdout) > 131072:
            raise ValueError('Monitor status exceeds size limit')
        try:
            outer = ast.literal_eval(result.stdout)
            if not isinstance(outer, tuple) or len(outer) != 1 or not isinstance(outer[0], str):
                raise ValueError
            payload = json.loads(outer[0])
            if not isinstance(payload, dict):
                raise ValueError
            return payload
        except (ValueError, SyntaxError, TypeError, RecursionError) as error:
            raise ValueError('Monitor controller returned invalid data') from error

    def status(self):
        try:
            value = self._call('GetState')
            if type(value.get('api_version')) is not int or value['api_version'] != 1:
                raise ValueError('Unsupported monitor controller version')
            state = value.get('status')
            if not isinstance(state, str) or state not in {'stopped', 'discovering', 'connecting', 'streaming', 'retrying', 'error'}:
                raise ValueError('Unknown monitor state')
            features = value.get('features')
            if not isinstance(features, list) or any(not isinstance(x, str) for x in features):
                raise ValueError('Invalid monitor capabilities')
            return {'available': True, 'state': state,
                    'message': str(value.get('message') or '')[:400],
                    'profile': _profile(value.get('profile')),
                    'receiver': {'name': str(value['receiver'].get('name') or '')[:120]}
                    if isinstance(value.get('receiver'), dict) else {},
                    'trial': _trial(value.get('trial')),
                    'actions': [action for action, verb in ACTIONS.items() if verb in features]}
        except (OSError, subprocess.SubprocessError, ValueError, RuntimeError):
            return {'available': False, 'state': 'unavailable',
                    'message': 'Start Desktop; wait for PanelBridge.',
                    'profile': {}, 'receiver': {}, 'trial': None, 'actions': []}

    def command(self, action):
        if action not in ACTIONS:
            raise ValueError('Unsupported monitor action')
        result = self._call('Command', ACTIONS[action], '{}')
        if type(result.get('api_version')) is not int or result['api_version'] != 1:
            raise ValueError('Unsupported monitor controller response')
        if result.get('ok') is not True:
            raise RuntimeError(str(result.get('error') or 'Monitor action was rejected')[:240])
        accepted = result.get('result')
        if not isinstance(accepted, dict) or accepted.get('accepted') is not True:
            raise ValueError('Monitor command was not acknowledged')
        return result
