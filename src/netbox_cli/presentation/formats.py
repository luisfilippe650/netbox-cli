from enum import Enum


class DetailOutputFormat(str, Enum):
    human = "human"
    json = "json"


class InventoryOutputFormat(str, Enum):
    human = "human"
    json = "json"
    csv = "csv"
