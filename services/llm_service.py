import importlib
import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import anthropic
from openai import AsyncOpenAI

from functions.function_manifest import tools
from logger_config import get_logger
from services.call_context import CallContext
from services.event_emmiter import EventEmitter

logger = get_logger("LLMService")

class AbstractLLMService(EventEmitter, ABC):
    def __init__(self, context: CallContext):
        super().__init__()
        self.system_message = context.system_message
        self.initial_message = context.initial_message
        self.context = context
        self.user_context = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": self.initial_message}
        ]
        self.partial_response_index = 0
        self.available_functions = {}
        for tool in tools:
            function_name = tool['function']['name']
            module = importlib.import_module(f'functions.{function_name}')
            self.available_functions[function_name] = getattr(module, function_name)
        self.sentence_buffer = ""
        context.user_context = self.user_context

    def set_call_context(self, context: CallContext):
        self.context = context
        self.user_context = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": context.initial_message}
        ]
        context.user_context = self.user_context
        self.system_message = context.system_message
        self.initial_message = context.initial_message


    @abstractmethod
    async def completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user'):
        pass

    def reset(self):
        self.partial_response_index = 0

    def validate_function_args(self, args):
        try:
            return json.loads(args)
        except json.JSONDecodeError:
            logger.info('Warning: Invalid function arguments returned by LLM:', args)
            return {}

    @staticmethod
    def convert_openai_tools_to_anthropic(openai_tools):
        anthropic_tools = []
        for tool in openai_tools:
            if tool['type'] == 'function':
                function = tool['function']
                anthropic_tool = {
                    "name": function['name'],
                    "description": function.get('description', ''),
                    "input_schema": {
                        "type": "object",
                        "properties": function.get('parameters', {}).get('properties', {}),
                        "required": function.get('parameters', {}).get('required', [])
                    }
                }
                
                # Remove 'description' from individual properties if present
                for prop in anthropic_tool['input_schema']['properties'].values():
                    prop.pop('description', None)
                
                # If there are no properties, set an empty dict
                if not anthropic_tool['input_schema']['properties']:
                    anthropic_tool['input_schema']['properties'] = {}
                
                anthropic_tools.append(anthropic_tool)
        
        return anthropic_tools

    def split_into_sentences(self, text):
        # Split the text into sentences, keeping the separators
        sentences = re.split(r'([.!?])', text)
        # Pair the sentences with their separators
        sentences = [''.join(sentences[i:i+2]) for i in range(0, len(sentences), 2)]
        return sentences

    async def emit_complete_sentences(self, text, interaction_count):
        self.sentence_buffer += text
        sentences = self.split_into_sentences(self.sentence_buffer)
        
        # Emit all complete sentences
        for sentence in sentences[:-1]:
            await self.emit('llmreply', {
                "partialResponseIndex": self.partial_response_index,
                "partialResponse": sentence.strip()
            }, interaction_count)
            self.partial_response_index += 1
        
        # Keep the last (potentially incomplete) sentence in the buffer
        self.sentence_buffer = sentences[-1] if sentences else ""

class OpenAIService(AbstractLLMService):
    def __init__(self, context: CallContext):
        super().__init__(context)
        self.openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user'):
        try:
            self.user_context.append({"role": role, "content": text, "name": name})
            messages = [{"role": "system", "content": self.system_message}] + self.user_context
        
            stream = await self.openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=tools,
                stream=True,
            )

            complete_response = ""
            function_name = ""
            function_args = ""

            async for chunk in stream:
                delta = chunk.choices[0].delta
                content = delta.content or ""
                tool_calls = delta.tool_calls

                if tool_calls:
                    for tool_call in tool_calls:
                        if tool_call.function and tool_call.function.name:
                            logger.info(f"Function call detected: {tool_call.function.name}")
                            function_name = tool_call.function.name
                            function_args += tool_call.function.arguments or ""
                else:
                    complete_response += content
                    await self.emit_complete_sentences(content, interaction_count)

                if chunk.choices[0].finish_reason == "tool_calls":
                    logger.info(f"Function call detected: {function_name}")
                    function_to_call = self.available_functions[function_name]
                    function_args = self.validate_function_args(function_args)
                    
                    tool_data = next((tool for tool in tools if tool['function']['name'] == function_name), None)
                    say = tool_data['function']['say']

                    await self.emit('llmreply', {
                        "partialResponseIndex": None,
                        "partialResponse": say
                    }, interaction_count)

                    self.user_context.append({"role": "assistant", "content": say})
                    
                    function_response = await function_to_call(self.context, function_args)
                                        
                    logger.info(f"Function {function_name} called with args: {function_args}")

                    if function_name != "end_call":
                        await self.completion(function_response, interaction_count, 'function', function_name)

            # Emit any remaining content in the buffer
            if self.sentence_buffer.strip():
                await self.emit('llmreply', {
                    "partialResponseIndex": self.partial_response_index,
                    "partialResponse": self.sentence_buffer.strip()
                }, interaction_count)
                self.sentence_buffer = ""

            self.user_context.append({"role": "assistant", "content": complete_response})

        except Exception as e:
            logger.error(f"Error in OpenAIService completion: {str(e)}")


class AnthropicService(AbstractLLMService):
    def __init__(self, context: CallContext):
        super().__init__(context)
        self.client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        # Add a dummy user message to ensure the first message is from the user
        self.user_context = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": self.initial_message}
        ]

    async def completion(self, text: str, interaction_count: int, role: str = 'user', name: str = 'user'):
        try:
            self.user_context.append({"role": role, "content": text})
            
            messages = [{"role": msg["role"], "content": msg["content"]} for msg in self.user_context]
            
            async with self.client.messages.stream(
                model="claude-3-opus-20240229",
                max_tokens=300,
                system=self.system_message,
                messages=messages,
                tools=self.convert_openai_tools_to_anthropic(tools),
            ) as stream:
                complete_response = ""
                async for event in stream:
                    if event.type == "text":
                        content = event.text
                        complete_response += content
                        await self.emit_complete_sentences(content, interaction_count)
                    elif event.type == "tool_call":
                        function_name = event.tool_call.function.name
                        function_args = event.tool_call.function.arguments
                        logger.info(f"Function call detected: {function_name}")
                        function_to_call = self.available_functions[function_name]
                        function_args = self.validate_function_args(function_args)
                        
                        tool_data = next((tool for tool in tools if tool['function']['name'] == function_name), None)
                        say = tool_data['function']['say']

                        await self.emit('llmreply', {
                            "partialResponseIndex": None,
                            "partialResponse": say
                        }, interaction_count)

                        function_response = await function_to_call(function_args)
                                            
                        logger.info(f"Function {function_name} called with args: {function_args}")

                        if function_name != "end_call":
                            await self.completion(function_response, interaction_count, 'function', function_name)

                # Emit any remaining content in the buffer
                if self.sentence_buffer.strip():
                    await self.emit('llmreply', {
                        "partialResponseIndex": self.partial_response_index,
                        "partialResponse": self.sentence_buffer.strip()
                    }, interaction_count)
                    self.sentence_buffer = ""

                final_message = await stream.get_final_message()
                self.user_context.append({"role": "assistant", "content": final_message.content[0].text})

        except Exception as e:
            logger.error(f"Error in AnthropicService completion: {str(e)}")

class LLMFactory:
    @staticmethod
    def get_llm_service(service_name: str, context: CallContext) -> AbstractLLMService:
        if service_name.lower() == "openai":
            return OpenAIService(context)
        elif service_name.lower() == "anthropic":
            return AnthropicService(context)
        else:
            raise ValueError(f"Unsupported LLM service: {service_name}")