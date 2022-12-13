import enum


class WorkerQueue(enum.Enum):
    robotoff_high = "robotoff-high"
    robotoff_low = "robotoff-low"


class ObjectDetectionModel(enum.Enum):
    nutriscore = "nutriscore"
    universal_logo_detector = "universal-logo-detector"
    nutrition_table = "nutrition-table"
