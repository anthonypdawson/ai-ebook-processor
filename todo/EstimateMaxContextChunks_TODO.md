# TODO: Estimate Max Context Chunks for LLM

## Purpose
Implement a utility to estimate the maximum number of context chunks that can be sent to the LLM (e.g., llama3.4) based on:
- Model's max token limit (e.g., 8192 for llama3.4)
- Average token count per chunk (estimated via word count or tokenizer)
- Reserved tokens for prompt, instructions, and user question

## Steps
1. Query or hardcode the model's max token limit based on config (rag.embedding_model).
2. Estimate average token count per chunk (simple ratio or tokenizer).
3. Reserve a fixed number of tokens for prompt and question (e.g., 500).
4. Calculate: max_chunks = floor((max_tokens - reserved_tokens) / avg_tokens_per_chunk)
5. Optionally, expose this as a method or config option for dynamic chunk count adjustment.

## Notes
- Consider using a tokenizer library for more accurate token estimation.
- Document typical max token limits for supported models (llama2, llama3, mistral, phi, etc.).
- Add warnings or auto-adjust if context_chunks in config exceeds model limit.

## References
- Ollama model documentation: https://ollama.com/library
- Llama3 model card: https://ollama.com/library/llama3
- Tokenizer libraries: tiktoken, llama-cpp-python

---
This doc tracks the plan for future implementation. Not yet started.
