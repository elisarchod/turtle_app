from random import random
from typing import List, Tuple
from langchain_core.tools import BaseTool
from turtleapp.src.utils.log_handler import logger

class GenerateRandomFloats(BaseTool):
    name: str = "generate_random_floats_tool"
    description: str = ("Generates array_size random floats with the following input:"
                        "Args: min_number: float, max_number: float, array_size: int")
    ndigits: int = 2
    response_format: str = "content_and_artifact"

    def _run(self, min_number: float, max_number: float, array_size: int) -> Tuple[List[float], str]:
        range_ = max_number - min_number
        array = [round(min_number + (range_ * random()), ndigits=self.ndigits) for _ in range(array_size)]
        content = f"Generated {array_size} floats in [{min_number}, {max_number}], rounded to {self.ndigits} decimals, first number {array[0]}."
        logger.info(f"Generated random numbers: {array}")
        return array, content


rand_gen = GenerateRandomFloats(ndigits=2)

if __name__ == "__main__":
    rand_gen.invoke({
       #  "name": "generate_random_floats",
        "args": {"min_number": 0.1, "max_number": 3.3333, "array_size": 3},
        "id":   "123",  # required
        "type": "tool_call",  # required
        })
    # pp