from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class NLQueryBurstThrottle(UserRateThrottle):
    scope = "nl_query_burst"


class NLQueryDailyThrottle(UserRateThrottle):
    scope = "nl_query_daily"


class NLQueryGlobalThrottle(SimpleRateThrottle):
    """One shared counter for all users: protects the shared LLM quota."""
    scope = "nl_query_global"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": "all"}