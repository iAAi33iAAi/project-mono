class GrappleColony:
    def __init__(self, human_id: str):
        self.human_id = human_id

    def handle_task(self, task: str):
        print(f"[Colony] human={self.human_id} executing task={task}")
        # mini: no real work yet
