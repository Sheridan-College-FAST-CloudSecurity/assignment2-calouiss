"""LangGraph course scheduling agent."""
import os
from typing import Annotated, TypedDict

import boto3
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.tools import ALL_TOOLS, check_schedule_conflicts


class SchedulerState(TypedDict):
    messages: Annotated[list, add_messages]
    completed_courses: list
    current_plan: dict
    current_term: str
    approval: str


SYSTEM_PROMPT = """You are a course scheduling advisor.
1. Use tools to check prerequisites and availability before proposing anything.
2. When ready to propose, output exactly one line in this format:
   SCHEDULE: COURSE1, COURSE2, COURSE3
3. Maximum 5 courses per term."""


def _sanitize_message(m):
    if isinstance(m, AIMessage) and getattr(m, 'tool_calls', None):
        return AIMessage(content='', tool_calls=m.tool_calls,
                         id=getattr(m, 'id', None),
                         response_metadata=getattr(m, 'response_metadata', {}))
    return m


def _build_messages(state):
    context = (
        f"Student completed: {', '.join(state['completed_courses']) if state['completed_courses'] else 'None'}\n"
        f"Planning term: {state['current_term']}"
    )
    full_prompt = SYSTEM_PROMPT + "\n\n" + context
    history = [
        _sanitize_message(m)
        for m in state['messages']
        if not isinstance(m, SystemMessage)
    ]
    if history and isinstance(history[-1], AIMessage) and not getattr(history[-1], 'tool_calls', None):
        history = history + [HumanMessage(content="Please continue planning.")]
    if history and isinstance(history[0], HumanMessage):
        history[0] = HumanMessage(content=full_prompt + "\n\n" + history[0].content)
        return history
    return [SystemMessage(content=full_prompt)] + history


def build_agent(model_id: str = 'mistral.mistral-large-2402-v1:0'):
    """Build and compile the scheduling advisor agent."""
    session = boto3.Session(
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        aws_session_token=os.environ.get('AWS_SESSION_TOKEN'),
        region_name=os.environ.get('AWS_DEFAULT_REGION', 'ca-central-1'),
    )
    llm = ChatBedrockConverse(
        model_id=model_id,
        client=session.client('bedrock-runtime'),
        additional_model_request_fields={},
    )
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    def agent_node(state):
        messages = _build_messages(state)
        response = llm_with_tools.invoke(messages)
        return {'messages': [response]}

    tool_node = ToolNode(ALL_TOOLS)

    def validation_node(state):
        last_msg = state['messages'][-1]
        content = last_msg.content if isinstance(last_msg.content, str) else ''
        if 'SCHEDULE:' in content:
            line = next(l for l in content.split('\n') if 'SCHEDULE:' in l)
            courses_str = line.split('SCHEDULE:')[1].strip()
            result = check_schedule_conflicts.invoke({
                'proposed_courses': courses_str,
                'term': state['current_term'],
                'completed_courses': ','.join(state['completed_courses'])
            })
            if 'Valid' in result:
                return {'messages': [AIMessage(content=f"SCHEDULE: {courses_str}\n✓ {result}")]}
            return {'messages': [AIMessage(content=f"✗ {result}. Please revise.")]}
        return {}

    def hitl_node(state):
        return {}

    def finalize_node(state):
        schedule_msg = next(
            (m for m in reversed(state['messages'])
             if isinstance(m, AIMessage) and 'SCHEDULE:' in (m.content or '')),
            None
        )
        if schedule_msg:
            line = next(l for l in schedule_msg.content.split('\n') if 'SCHEDULE:' in l)
            courses = [c.strip() for c in line.split('SCHEDULE:')[1].split(',')]
            new_plan = state['current_plan'].copy()
            new_plan[state['current_term']] = courses
            return {
                'current_plan': new_plan,
                'completed_courses': state['completed_courses'] + courses,
                'messages': [AIMessage(content=f"✓ {state['current_term']} finalized: {', '.join(courses)}")]
            }
        return {}

    def revision_node(state):
        return {'messages': [HumanMessage(content="The plan was rejected. Please create a revised schedule.")]}

    def route_agent(state):
        last_msg = state['messages'][-1]
        if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
            return 'tool_node'
        content = last_msg.content if isinstance(last_msg.content, str) else ''
        if 'SCHEDULE:' in content:
            return 'validation_node'
        return END

    def route_validation(state):
        return 'hitl_node' if '✓' in (state['messages'][-1].content or '') else 'agent_node'

    def route_hitl(state):
        approval = state.get('approval', '')
        if approval == 'approved':
            return 'finalize_node'
        elif approval == 'rejected':
            return 'revision_node'
        return 'hitl_node'

    graph = StateGraph(SchedulerState)
    graph.add_node('agent_node',      agent_node)
    graph.add_node('tool_node',       tool_node)
    graph.add_node('validation_node', validation_node)
    graph.add_node('hitl_node',       hitl_node)
    graph.add_node('finalize_node',   finalize_node)
    graph.add_node('revision_node',   revision_node)

    graph.set_entry_point('agent_node')
    graph.add_conditional_edges('agent_node',      route_agent)
    graph.add_edge(              'tool_node',       'agent_node')
    graph.add_conditional_edges('validation_node', route_validation)
    graph.add_conditional_edges('hitl_node',       route_hitl)
    graph.add_edge(              'finalize_node',   END)
    graph.add_edge(              'revision_node',   'agent_node')

    return graph.compile(checkpointer=MemorySaver(), interrupt_before=['hitl_node'])
