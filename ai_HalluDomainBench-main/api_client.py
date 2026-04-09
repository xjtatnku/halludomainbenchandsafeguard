"""Legacy compatibility wrapper for the formal HalluDomainBench provider layer."""

from halludomainbench.providers import BaseLLMClient, LLMFactory, SiliconFlowClient

__all__ = ["BaseLLMClient", "LLMFactory", "SiliconFlowClient"]
