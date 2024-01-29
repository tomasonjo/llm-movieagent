from typing import Optional, Type

from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.embeddings import OpenAIEmbeddings
from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool

from neo4j_semantic_layer.utils import graph

retrieval_query = """
CALL db.index.vector.queryNodes($index, $k, $embedding) YIELD node, score
WITH node AS m, score
MATCH (m)-[r:ACTED_IN|DIRECTED|HAS_GENRE]-(t)
WITH m, score, type(r) as type, collect(coalesce(t.name, t.title)) as names
WITH m, score, type+": "+reduce(s="", n IN names | s + n + ", ") as types
WITH m, score, collect(types) as contexts
WITH m, score, "\nplot:" + m.plot + "\nurl:" + m.url + "\nreleased:" + m.released + 
       "\ntitle: "+ coalesce(m.title, m.name) + "\nyear: "+coalesce(m.released,"") +"\n" +
       reduce(s="", c in contexts | s + substring(c, 0, size(c)-2) +"\n") as context
RETURN context
"""

embedding = OpenAIEmbeddings()


def plot_search(description: str, k: int = 3) -> str:
    embed_description = embedding.embed_query(description)
    data = graph.query(
        retrieval_query,
        {"index": "moviePlotsEmbedding", "k": k, "embedding": embed_description},
    )
    return "\n#Movie".join([el["context"] for el in data])


class PlotSearchInput(BaseModel):
    movie_description: str = Field(description="Description or a plot of a movie")


class PlotSearchTool(BaseTool):
    name = "PlotSearch"
    description = "useful for when a user is searching for a movie based on the plot or description"
    args_schema: Type[BaseModel] = PlotSearchInput

    def _run(
        self,
        movie_description: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        return plot_search(movie_description)

    async def _arun(
        self,
        movie_description: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        return plot_search(movie_description)
