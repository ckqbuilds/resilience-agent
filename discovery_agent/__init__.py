"""Resource Discovery Agent module.

Specializes in discovering and analyzing AWS resources within accounts,
using AWS Resource Explorer and Config to map infrastructure and relationships.
"""

from .resource_discovery_agent import discovery_agent

__all__ = ["discovery_agent"]
