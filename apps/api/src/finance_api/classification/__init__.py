"""Evidence-driven transaction classification.

Separates messy/agentic *evidence gathering* from a deterministic *evidence
policy*. Gatherers emit typed :class:`Evidence`; the policy maps evidence to a
categorization as a pure, deterministic function.
"""
