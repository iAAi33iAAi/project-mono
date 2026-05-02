from humans.human_001.open_claw.runtime.openclaw_runtime import OpenClawRuntime
from humans.human_001.grapple_colony.nodes.colony_runtime import GrappleColony


class PassiveDigitwin:
    def __init__(self, human_id: str):
        self.human_id = human_id
        self.openclaw = OpenClawRuntime(human_id)
        self.colony = GrappleColony(human_id)

    def handle_request(self, request: str):
        print(f"[Digitwin:passive] human={self.human_id} request={request}")
        self.openclaw.dispatch_to_colony(self.colony, request)
