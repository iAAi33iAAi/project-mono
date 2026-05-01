from humans.human_001.digitwin.modes.passive.passive_digitwin import PassiveDigitwin


def main():
    human_id = "human_001"
    dt = PassiveDigitwin(human_id)
    dt.handle_request("summarize_node_status")
    dt.handle_request("plan_daily_routine")


if __name__ == "__main__":
    main()
