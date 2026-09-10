from fastapi import APIRouter

from app.domain.policies import Policy


class PolicyStore:
    def __init__(self, policy: Policy) -> None:
        self._policy = policy

    @property
    def current(self) -> Policy:
        return self._policy

    def replace(self, policy: Policy) -> Policy:
        self._policy = policy
        return policy


def create_policy_router(store: PolicyStore) -> APIRouter:
    router = APIRouter(prefix="/api/policy", tags=["policy"])

    @router.get("", response_model=Policy)
    def get_policy() -> Policy:
        return store.current

    @router.put("", response_model=Policy)
    def put_policy(policy: Policy) -> Policy:
        return store.replace(policy)

    return router
