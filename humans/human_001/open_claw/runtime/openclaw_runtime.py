from humans.human_001.codex.rules.base_rules import RULES


class OpenClawRuntime:
        def __init__(self, human_id: str):
                    self.human_id = human_id
                    self.rules = RULES

        def check_allowed(self, action: str) -> bool:
                    print(f"[OpenClaw] human={self.human_id} action={action} rules={self.rules}")
                    return True

        def dispatch_to_colony(self, colony, task: str):
                    if not self.check_allowed(task):
                                    print(f"[OpenClaw] BLOCKED task={task}")
                                    return
                                colony.handle_task(task)
            
