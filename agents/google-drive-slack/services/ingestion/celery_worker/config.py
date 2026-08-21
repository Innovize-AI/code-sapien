import os
from functools import lru_cache
from kombu import Queue


def route_task(name, args, kwargs, options, task=None, **kw):
    if ":" in name:
        queue, _ = name.split(":")
        return {"queue": queue}
    return {"queue": "celery"}


class BaseConfig:
    CELERY_BROKER_URL: str = os.environ.get("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
    result_backend: str = os.environ.get("CELERY_RESULT_BACKEND", "redis://")

    CELERY_TASK_QUEUES: list = (
        # default queu
        Queue("celery"),
        # custom queue
        Queue("load_doc"),
        Queue("embed_ingest"),
    )

    CELERY_TASK_ROUTES = (route_task,)
    CELERY_TASK_RESULT_EXPIRES = 18000 # 5 hours
    task_track_started=True
    task_ignore_result=False




class DevelopmentConfig(BaseConfig):
    pass


@lru_cache()
def get_settings():
    config_cls_dict = {
        "development": DevelopmentConfig,
    }
    config_name = os.environ.get("CELERY_CONFIG", "development")
    config_cls = config_cls_dict[config_name]
    return config_cls()


settings = get_settings()
print(settings.result_backend)