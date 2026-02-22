"""
PM Agent Intent Classifier

Identifies user intent from natural language input using a hybrid approach:
1. Rule-based pattern matching (fast, deterministic)
2. LLM fallback (handles complex expressions)
"""

import re
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from .models import Intent, IntentType, ConversationContext
from .config import IntentClassifierConfig
from .exceptions import IntentClassificationError

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Intent Classifier - Single responsibility component

    Identifies user intent from natural language input using:
    1. Rule-based pattern matching (high priority patterns)
    2. LLM semantic understanding (fallback for unmatched patterns)
    """

    def __init__(
        self,
        config: IntentClassifierConfig,
        llm_executor=None,
        default_department: Optional[str] = None
    ):
        """
        Initialize Intent Classifier

        Args:
            config: Intent classifier configuration
            llm_executor: Optional LLM executor for fallback
            default_department: Default department for config lookup
        """
        self.config = config
        self.llm = llm_executor
        self.default_department = default_department

        # Compile regex patterns for performance
        self._compiled_patterns: Dict[str, List[tuple]] = {}
        self._compile_patterns()

        # Metrics
        self._rule_match_count = 0
        self._llm_fallback_count = 0
        self._total_classifications = 0

    def _compile_patterns(self):
        """Pre-compile regex patterns for better performance"""
        intents = self.config.get_all_intents(self.default_department)

        for intent_id, intent_config in intents.items():
            compiled_list = []
            for pattern in intent_config.patterns:
                try:
                    flags = 0 if pattern.case_sensitive else re.IGNORECASE
                    compiled_regex = re.compile(pattern.regex, flags)
                    compiled_list.append((compiled_regex, pattern.priority, pattern))
                except re.error as e:
                    logger.warning(f"Failed to compile pattern for intent {intent_id}: {e}")

            if compiled_list:
                self._compiled_patterns[intent_id] = compiled_list

    async def classify(
        self,
        user_input: str,
        context: Optional[ConversationContext] = None
    ) -> Intent:
        """
        Classify user intent from input text

        Args:
            user_input: User's natural language input
            context: Optional conversation context

        Returns:
            Classified Intent with confidence and reasoning

        Raises:
            IntentClassificationError: If classification fails
        """
        self._total_classifications += 1
        user_input_stripped = (user_input or "").strip()

        # Fast-fail on empty/noisy input to avoid unnecessary LLM calls.
        if not user_input_stripped:
            return Intent(
                type=IntentType.UNKNOWN,
                confidence=0.0,
                reasoning="Empty input"
            )
        if not re.search(r'[\w\u4e00-\u9fff]', user_input_stripped):
            return Intent(
                type=IntentType.UNKNOWN,
                confidence=0.0,
                reasoning="No meaningful tokens in input"
            )

        # Phase 1: Rule-based pattern matching
        intent = await self._rule_based_classification(user_input, context)
        if intent.type != IntentType.UNKNOWN:
            self._rule_match_count += 1
            logger.info(f"Rule-based classification: {intent.type.value} (confidence: {intent.confidence})")
            return intent

        # Phase 2: LLM fallback (if available)
        if self.llm:
            try:
                intent = await self._llm_classification(user_input, context)
                if intent.type != IntentType.UNKNOWN:
                    self._llm_fallback_count += 1
                    logger.info(f"LLM fallback classification: {intent.type.value} (confidence: {intent.confidence})")
                    return intent
            except Exception as e:
                logger.error(f"LLM classification failed: {e}")

        # Return UNKNOWN if both phases fail
        return Intent(
            type=IntentType.UNKNOWN,
            confidence=0.0,
            reasoning="No matching pattern found and LLM unavailable or failed"
        )

    async def _rule_based_classification(
        self,
        user_input: str,
        context: Optional[ConversationContext] = None
    ) -> Intent:
        """
        Rule-based intent classification using pattern matching

        Returns highest priority match across all intents
        """
        user_input_stripped = user_input.strip()

        # Collect all matches with their priorities
        matches = []

        for intent_id, compiled_patterns in self._compiled_patterns.items():
            for compiled_regex, priority, pattern_config in compiled_patterns:
                if compiled_regex.search(user_input_stripped):
                    intent_config = self.config.get_intent_config(intent_id, self.default_department)
                    if intent_config:
                        matches.append({
                            'intent_type': intent_config.type,
                            'priority': priority,
                            'confidence': 0.9,  # High confidence for rule matches
                            'pattern': pattern_config.regex,
                            'reasoning': f"Matched pattern: {pattern_config.description or pattern_config.regex}"
                        })

        if not matches:
            return Intent(
                type=IntentType.UNKNOWN,
                confidence=0.0,
                reasoning="No pattern matched"
            )

        # Sort by priority (lower number = higher priority)
        matches.sort(key=lambda x: x['priority'])

        # Return highest priority match
        best_match = matches[0]
        return Intent(
            type=best_match['intent_type'],
            confidence=best_match['confidence'],
            reasoning=best_match['reasoning'],
            matched_pattern=best_match['pattern']
        )

    async def _llm_classification(
        self,
        user_input: str,
        context: Optional[ConversationContext] = None
    ) -> Intent:
        """
        LLM-based intent classification for complex expressions

        Used as fallback when rule-based matching fails
        """
        # Build available intents description
        intents = self.config.get_all_intents(self.default_department)
        intents_description = self._build_intents_description(intents)

        # Build context information
        context_info = ""
        if context:
            recent_history = context.get_recent_history(3)
            if recent_history:
                context_info = "\nRecent conversation:\n" + "\n".join([
                    f"- User: {turn.get('user_input', '')}"
                    for turn in recent_history
                ])

        system_prompt = f"""You are an intent classifier for the LEE workflow system.

Your task is to analyze user input and identify their intent from the available options.

Available intents:
{intents_description}

Respond with a JSON object in the following format:
{{
  "intent_type": "one_of_the_available_intents",
  "confidence": 0.0_to_1.0,
  "reasoning": "brief_explanation_of_why_this_intent_matches"
}}

Rules:
1. Only return intents from the available list
2. If unsure, set confidence < 0.5
3. If no intent matches well, use "unknown"
4. Keep reasoning brief and factual
5. Return ONLY the JSON, no other text"""

        try:
            result = await self.llm.execute({
                "prompt": f"User input: {user_input}{context_info}",
                "system_message": system_prompt,
                "temperature": 0.3,
                "max_tokens": 200
            })

            if result.get("status") != "completed":
                return Intent(
                    type=IntentType.UNKNOWN,
                    confidence=0.0,
                    reasoning=f"LLM execution failed: {result.get('error', 'Unknown error')}"
                )

            response_text = result.get("generated_text", "")

            # Extract JSON from response
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if not json_match:
                return Intent(
                    type=IntentType.UNKNOWN,
                    confidence=0.0,
                    reasoning="No valid JSON in LLM response"
                )

            intent_data = json.loads(json_match.group())

            # Validate intent type
            intent_type_str = intent_data.get("intent_type", "unknown")
            try:
                intent_type = IntentType(intent_type_str)
            except ValueError:
                intent_type = IntentType.UNKNOWN

            return Intent(
                type=intent_type,
                confidence=float(intent_data.get("confidence", 0.5)),
                reasoning=intent_data.get("reasoning", "LLM classification"),
                metadata={"llm_generated": True}
            )

        except Exception as e:
            logger.error(f"LLM classification error: {e}")
            return Intent(
                type=IntentType.UNKNOWN,
                confidence=0.0,
                reasoning=f"LLM classification failed: {e}"
            )

    def _build_intents_description(self, intents: Dict[str, Any]) -> str:
        """Build human-readable description of available intents"""
        lines = []
        for intent_id, intent_config in intents.items():
            lines.append(f"- {intent_id}: {intent_config.description}")

            if intent_config.patterns:
                pattern_examples = [p.description or p.regex for p in intent_config.patterns[:2]]
                lines.append(f"  Examples: {', '.join(pattern_examples)}")

        return "\n".join(lines)

    def get_metrics(self) -> Dict[str, Any]:
        """Get classification metrics"""
        return {
            "total_classifications": self._total_classifications,
            "rule_match_count": self._rule_match_count,
            "llm_fallback_count": self._llm_fallback_count,
            "rule_match_rate": (
                self._rule_match_count / self._total_classifications
                if self._total_classifications > 0 else 0
            ),
            "llm_fallback_rate": (
                self._llm_fallback_count / self._total_classifications
                if self._total_classifications > 0 else 0
            ),
        }

    def reset_metrics(self):
        """Reset classification metrics"""
        self._rule_match_count = 0
        self._llm_fallback_count = 0
        self._total_classifications = 0
