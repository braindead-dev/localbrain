"""
Answer Synthesizer for LocalBrain

Takes search results and conversation history, generates natural language answers.
Supports multi-turn conversations with context awareness.
"""

from typing import List, Dict, Optional
from utils.llm_client import LLMClient


class AnswerSynthesizer:
    """
    Synthesizes natural language answers from search contexts.
    Supports multi-turn conversations with history.
    """

    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        """Initialize synthesizer with LLM client."""
        self.llm = LLMClient(model=model)

    def synthesize(
        self,
        query: str,
        contexts: List[Dict],
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate a conversational answer from search contexts.

        Args:
            query: User's question
            contexts: List of context dicts with 'text' and 'file' fields
            conversation_history: Optional list of previous messages [{"role": "user/assistant", "content": "..."}]

        Returns:
            Natural language answer as string
        """

        # Handle case with no contexts
        if not contexts:
            return "I couldn't find any relevant information in your vault to answer that question."

        # Build context string from search results
        context_str = self._format_contexts(contexts)

        # Build conversation context if history exists
        conversation_context = ""
        if conversation_history and len(conversation_history) > 0:
            # Take last 6 messages (3 exchanges) for context
            recent_history = conversation_history[-6:]
            conversation_context = "\n\nPrevious conversation:\n"
            for msg in recent_history:
                role_label = "User" if msg["role"] == "user" else "Assistant"
                conversation_context += f"{role_label}: {msg['content']}\n"
            conversation_context += "\n"

        # Create prompt for answer synthesis
        prompt = f"""Based on the following information from the user's vault, provide a clear and concise answer to their question.

{conversation_context}Current Question: {query}

Information from vault:
{context_str}

Instructions:
- Answer the question directly and conversationally
- Use information from the provided contexts
- If the question is a follow-up (based on conversation history), reference previous context appropriately
- Be concise but complete
- If the contexts don't fully answer the question, acknowledge what you can and cannot answer
- Do not make up information not present in the contexts

Answer:"""

        # System prompt for answer synthesis
        system_prompt = """You are a helpful assistant that answers questions based on information from the user's personal knowledge vault.

Your role:
- Synthesize information from provided contexts into clear, conversational answers
- Maintain conversation context across multiple turns
- Be direct and concise
- Only use information present in the contexts
- Acknowledge limitations if contexts don't contain the answer"""

        # Generate answer
        try:
            answer = self.llm.call(
                prompt=prompt,
                system=system_prompt,
                max_tokens=1024,
                temperature=0.3  # Slightly higher for more natural responses
            )
            return answer.strip()
        except Exception as e:
            # Fallback to simple context listing if synthesis fails
            return f"Found relevant information but failed to synthesize answer: {str(e)}\n\nRaw contexts:\n{context_str}"

    def _format_contexts(self, contexts: List[Dict]) -> str:
        """Format contexts into a readable string for the LLM."""
        formatted = []

        for idx, ctx in enumerate(contexts, 1):
            file = ctx.get('file', 'Unknown file')
            text = ctx.get('text') or ctx.get('content', '')

            # Truncate very long contexts (keep first 1000 chars)
            if len(text) > 1000:
                text = text[:1000] + "..."

            formatted.append(f"[Source {idx}: {file}]\n{text}")

        return "\n\n---\n\n".join(formatted)
