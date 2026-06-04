from __future__ import annotations

import json
import logging
import re
import ollama
from .channel_maps import ChannelMapper, CHANNELS, ChannelMappingResult, PROPAGATION_LAG

logger = logging.getLogger(__name__)

class OllamaChannelMapper(ChannelMapper):
    """
    Extends ChannelMapper to perform dynamic channel mapping using Ollama
    when pure rule-based matching yields no channels.
    """

    def map_dynamic(
        self,
        event_class: str,
        subtypes: list[str],
        title: str,
        description: str,
        model_name: str = "gemma3:4b"
    ) -> ChannelMappingResult:
        """
        Attempt to map event class and subtypes using rule-based lookup.
        If no transmission channels are resolved, query Ollama to dynamically
        select channels from the official 14 channels list.
        """
        # 1. Try standard rule-based mapping first
        result = self.map(event_class, subtypes)
        if result.channels:
            return result

        # 2. Dynamic Ollama-based mapping if rules yielded nothing
        channels_str = "\n".join([
            f"- {cid}: {ch.channel_name} (Indicators: {', '.join(ch.macro_indicators)}). Description: {ch.description}"
            for cid, ch in CHANNELS.items()
        ])

        prompt = f"""
You are a senior financial analyst. We need to map an economic news event to its transmission channels into the Indian economy.

ARTICLE DETAILS:
Title: {title}
Description: {description}
Classified Event Class: {event_class}
Classified Subtypes: {', '.join(subtypes)}

OFFICIAL CHANNELS LIST:
{channels_str}

INSTRUCTIONS:
1. Select 1 to 3 channels from the official list that best describe how this news event transmits impact to India's macro economy.
2. Return ONLY a valid JSON list of strings containing the exact channel_ids (e.g. ["trade_competitiveness", "current_account"]) that apply.
3. If none apply, return an empty list [].
4. Do not output any explanation, markdown blocks (like ```json), or other text. Return ONLY the raw JSON array.
"""
        try:
            response = ollama.chat(
                model=model_name,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.0}
            )
            content = response['message']['content'].strip()
            
            json_match = re.search(r'\[.*?\]', content, re.DOTALL)
            if json_match:
                selected_ids = json.loads(json_match.group())
                # Filter only valid channel IDs
                valid_ids = [cid for cid in selected_ids if cid in CHANNELS]
                
                if valid_ids:
                    channels = [CHANNELS[cid].to_dict() for cid in valid_ids]
                    macro_indicators = set()
                    cis_dimensions = set()
                    for cid in valid_ids:
                        macro_indicators.update(CHANNELS[cid].macro_indicators)
                        cis_dimensions.update(CHANNELS[cid].cis_dimensions)
                        
                    return ChannelMappingResult(
                        channels=channels,
                        macro_indicators=sorted(macro_indicators),
                        cis_dimensions=sorted(cis_dimensions),
                        propagation_lag=PROPAGATION_LAG.get(event_class, "unknown"),
                        unmapped_subtypes=[]
                    )
        except Exception as e:
            logger.error("Dynamic Ollama channel mapping failed: %s", e)

        return result
