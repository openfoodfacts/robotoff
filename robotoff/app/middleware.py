from robotoff.models import db
from robotoff.utils.cache import function_cache_register


class DBConnectionMiddleware:
    def process_resource(self, req, resp, resource, params):
        db.connect(reuse_if_open=True)

    def process_response(self, req, resp, resource, req_succeeded):
        if not db.is_closed():
            db.close()


class CacheClearMiddleware:
    def process_response(self, req, resp, resource, req_succeeded):
        function_cache_register.clear_all()
