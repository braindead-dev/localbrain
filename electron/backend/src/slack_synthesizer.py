"""
Slack Answer Synthesizer for LocalBrain

Specialized synthesizer that allows a Slack bot to pose as the user,
answering questions using the user's knowledge base with context-appropriate tone.
"""

from typing import List, Dict, Optional
from utils.llm_client import LLMClient


class SlackAnswerSynthesizer:
    """
    Synthesizes answers for Slack bot that poses as the user.
    Adapts tone based on Slack context and protects user reputation.
    """

    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        """Initialize synthesizer with LLM client."""
        self.llm = LLMClient(model=model)

    def synthesize(
        self,
        question: str,
        contexts: List[Dict],
        slack_context: Dict,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate a Slack response that poses as the user.

        Args:
            question: The question being asked
            contexts: List of context dicts with 'text' and 'file' fields
            slack_context: Dict with 'server_name', 'channel_name', 'asker_name', 'thread_id'
            conversation_history: Optional list of previous messages

        Returns:
            Natural language answer as string (no citations)
        """

        # Handle case with no contexts
        if not contexts:
            return "I'm not sure - I don't have information about that in my notes."

        # Build context string from search results
        context_str = self._format_contexts(contexts)

        # Build conversation context if history exists
        conversation_context = ""
        if conversation_history and len(conversation_history) > 0:
            # Take last 6 messages (3 exchanges) for context
            recent_history = conversation_history[-6:]
            conversation_context = "\n\nRecent conversation history:\n"
            for msg in recent_history:
                role_label = "Question" if msg["role"] == "user" else "Your answer"
                conversation_context += f"{role_label}: {msg['content']}\n"
            conversation_context += "\n"

        # Extract Slack context
        server_name = slack_context.get('server_name', 'Unknown workspace')
        channel_name = slack_context.get('channel_name', 'Unknown channel')
        asker_name = slack_context.get('asker_name', 'Someone')

        # Create prompt for answer synthesis
        prompt = f"""You are responding to a question in Slack AS the user (you are posing as them).

{conversation_context}Current Question from {asker_name}: {question}

Slack Context:
- Workspace: {server_name}
- Channel: {channel_name}
- Asker: {asker_name}

Information from your knowledge vault:
{context_str}

Instructions:
- Answer AS the user, using first-person ("I", "my", etc.)
- Analyze the Slack context (workspace name, channel name, asker's name) to determine appropriate tone:
  * If workspace/channel contains "work", company names, or formal indicators → use professional tone
  * If workspace/channel is casual/personal → use friendly, conversational tone
  * If unsure, default to friendly-professional hybrid
- Be natural and conversational - respond as the user would in Slack
- Use information from the provided contexts from your vault
- If the question is a follow-up (based on conversation history), reference previous context appropriately
- Be concise but complete (Slack messages should be brief)
- DO NOT include source citations or file references
- DO NOT say anything that would harm the user's reputation or credibility
- If contexts don't fully answer the question, acknowledge what you know and what you don't
- Never make up information not present in the contexts

Answer:"""

        # System prompt emphasizing user impersonation
        system_prompt = f"""You are a Slack bot that answers questions by posing as the user.

Your role:
- You ARE the user - respond in first person using their knowledge vault
- Adapt your tone based on the Slack workspace/channel context (professional vs casual)
- Protect the user's reputation - never say anything harmful, offensive, or unprofessional
- Be helpful and conversational, just like the user would be in Slack
- Only use information from the user's knowledge vault
- Acknowledge limitations gracefully if you don't have the answer
- Keep responses concise and Slack-appropriate (brief, scannable)

Critical guardrails:
- NO offensive, discriminatory, or inappropriate content
- NO confidential information unless clearly appropriate for the channel
- NO claims about things not in the knowledge vault
- If in doubt about appropriateness, err on the side of caution"""

        # Generate answer
        try:
            answer = self.llm.call(
                prompt=prompt,
                system=system_prompt,
                max_tokens=1024,
                temperature=0.5  # Slightly higher for natural, varied responses
            )
            return answer.strip()
        except Exception as e:
            # Fallback to safe error message
            return f"Sorry, I'm having trouble accessing my notes right now. Could you ask again in a moment?"

    def _format_contexts(self, contexts: List[Dict]) -> str:
        """Format contexts into a readable string for the LLM."""
        formatted = []

        for idx, ctx in enumerate(contexts, 1):
            file = ctx.get('file', 'Unknown file')
            text = ctx.get('text') or ctx.get('content', '')

            # Truncate very long contexts (keep first 1000 chars)
            if len(text) > 1000:
                text = text[:1000] + "..."

            formatted.append(f"[Source {idx}: {file}]\\n{text}")

        return "\\n\\n---\\n\\n".join(formatted)
