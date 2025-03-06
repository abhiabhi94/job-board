class BasePortal:
    url: str
    region_mapping: dict[str, set[str]]

    def messages_to_notify() -> list[str]:
        raise NotImplementedError
