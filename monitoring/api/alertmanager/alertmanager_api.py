import os

from appservicecore.api_service import app
from dataclasses import dataclass
from fastapi import Request
import json
from ansible import context
from ansible.cli import CLI
from ansible.module_utils.common.collections import ImmutableDict
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager
from ansible.vars.manager import VariableManager


@dataclass
class Alert:
    status: str
    labels: dict
    annotations: str
    startsAt: str
    endsAt: str
    generatorURL: str
    fingerprint: str

    def remediation_required(self):
        return True if self.status == 'firing' else False

    def fetch_service_name(self):
        """Service name same as the one provided in prometheus.yml labels for each job."""
        return self.labels['service']

    def fetch_alert_type(self):
        return self.labels['alertname']

    def fetch_playbook_tag(self):
        """Make sure this tag is set in play book.
        Example: if alert is ServiceUnresponsive in rules.yml and service label in prometheus.yml is APP_SERVICE tag then playbook must contain the tag ServiceUnresponsiveAPP_SERVICE"""
        return f'{self.fetch_alert_type()}{self.fetch_service_name()}'


@app.post("/playbook")
async def execute_playbook_task(request: Request):
    body = await request.body()
    alerts = json.loads(body)['alerts']
    for a in alerts:
        alert = Alert(**a)
        if alert.remediation_required():
            tag = alert.fetch_playbook_tag()
            print(f'Executing ---- {tag}')
            loader = DataLoader()
            context.CLIARGS = ImmutableDict(tags=[tag], listtags=False, listtasks=False, listhosts=False, syntax=False,
                                            connection='ssh', module_path=None, become=None, become_method=None,
                                            become_user=None, verbosity=True, check=False, start_at_task=None)
            inventory_path = os.path.join(os.environ['CODEBASE_DIR'], '/configs/monitoring/ansible/inventory.yml')
            inventory = InventoryManager(loader=loader, sources=(inventory_path,))
            variable_manager = VariableManager(loader=loader, inventory=inventory,
                                               version_info=CLI.version_info(gitinfo=False))
            playbook_path = inventory_path = os.path.join(os.environ['CODEBASE_DIR'],
                                                          '/configs/monitoring/ansible/playbook.yml')
            pbook = PlaybookExecutor(playbooks=[playbook_path], inventory=inventory, variable_manager=variable_manager,
                                     passwords={})
            pbook.run()
