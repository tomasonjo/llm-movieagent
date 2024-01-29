from typing import Any, Dict, List, Optional, Type

from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.chains.graph_qa.cypher_utils import CypherQueryCorrector, Schema
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool
from langchain_community.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import RunnablePassthrough

from neo4j_semantic_layer.utils import get_candidates, graph

# Cypher validation tool for relationship directions
corrector_schema = [
    Schema(el["start"], el["type"], el["end"])
    for el in graph.structured_schema.get("relationships")
]
cypher_validation = CypherQueryCorrector(corrector_schema)

# LLMs
cypher_llm = ChatOpenAI(model_name="gpt-4", temperature=0.0)

# Generate Cypher statement based on natural language input
cypher_template = """Based on the Neo4j graph schema below, write a Cypher query that would answer the user's question:
{schema}
Entities in the question map to the following database values:
{entities_list}
Question: {question}

* Use Cypher syntax that is compatible with Neo4j 5
* Do not use GROUP BY, this is not SQL
* The size((r)--()) clause to count the number of relationships has been deprecated, you should use count{{(r)--()}} instead

Cypher query:"""  # noqa: E501

cypher_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Given an input question, convert it to a Cypher query. No pre-amble.",
        ),
        ("human", cypher_template),
    ]
)

cypher_response = (
    RunnablePassthrough.assign(
        entities_list=lambda x: x["entities_list"],
        schema=lambda _: graph.get_schema,
    )
    | cypher_prompt
    | cypher_llm.bind(stop=["\nCypherResult:"])
    | StrOutputParser()
)


def aggregation_tool(
    question: str, entities: Optional[List[Dict[str, Any]]] = None
) -> str:
    entities_list = ""
    if entities:
        for e in entities:
            candidates = get_candidates(e.name, e.type)
            # Todo add some sort of advanced disambiguation logic
            # At the moment we take the first result
            entities_list += f"{e.name} maps to {candidates[0]['candidate']}\n"
    # Get Cypher statement
    cypher_statement = cypher_response.invoke(
        {"question": question, "entities_list": entities_list}
    )
    # Validate Cypher statement
    validated_cypher = cypher_validation(cypher_statement)
    if not validated_cypher:
        return "I'm sorry, but there was some sort of error"  # Cypher statement doesn't fit the graph schema
    print(f"Generated Cypher: {validated_cypher}")
    data = graph.query(validated_cypher)
    return data


class Entity(BaseModel):
    name: str = Field(description="The name of a person or title of a movie")
    type: str = Field(
        description="Type of entity. Available options are: 'movie', 'person'"
    )


class AggregationInput(BaseModel):
    question: str = Field(
        description="The complete question the user is asking with full context"
    )
    entities: Optional[List[Entity]] = Field(
        description="List of movies or people in the question"
    )


class AggregationTool(BaseTool):
    name = "AggregationTool"
    description = "useful for when a user is searching any statistics like median, average, max about movies or actors"
    args_schema: Type[BaseModel] = AggregationInput

    def _run(
        self,
        question: str,
        entities: Optional[List[Dict[str, Any]]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        return aggregation_tool(question, entities)

    async def _arun(
        self,
        question: str,
        entities: Optional[List[Dict[str, Any]]] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        return aggregation_tool(question, entities)
