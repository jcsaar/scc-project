from abc import ABC, abstractmethod

from app.domain.disclosures import DisclosureProposal
from app.domain.private import PrivateContext
from app.domain.providers import CloudRecommendation
from app.domain.workflow import VerificationResult


class LocalModelProvider(ABC):
    @abstractmethod
    def analyse(self, prompt: str, context: PrivateContext) -> DisclosureProposal:
        raise NotImplementedError

    @abstractmethod
    def verify(
        self, recommendation: CloudRecommendation, context: PrivateContext
    ) -> VerificationResult:
        raise NotImplementedError
