# Archived LLM Modules

This directory contains archived modules from the original complex multi-LLM system that was simplified for the MVP.

## Archived Files

- **llm_mixin.py** - Original LLM integration mixin for BaseAgent
- **intelligent_router.py** - Advanced provider routing and selection logic  
- **cost_optimizer.py** - Real-time cost tracking and optimization

## Purpose

These files are preserved for future reference when you want to add back advanced features like:
- Intelligent provider routing based on content and context
- Real-time cost optimization and budgeting
- Advanced retry and failover strategies
- Performance-based provider selection

## Migration Notes

The current system uses simplified LLM integration:
- Direct provider calls through `infra.runtimes.client.LLMClient`
- YAML-based configuration
- Simple retry logic
- Basic provider routing

When you're ready to scale beyond MVP, these archived modules provide the foundation for advanced multi-LLM features.