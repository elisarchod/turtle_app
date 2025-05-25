# create data set for evaludation
import logging
from typing import List, Dict, Any
from langsmith import Client

from ..config import PROCESSED_DATA_DIR
from ..eval_data.data_qa import QA_EXAMPLES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EvaluationDatasetCreator:
    def __init__(self, dataset_name: str):
        self.dataset_name = dataset_name
        self.client = Client()

    def create_dataset(self) -> str:
        try:
            logger.info(f"Creating dataset: {self.dataset_name}")
            dataset = self.client.create_dataset(self.dataset_name)
            return dataset.id
        except Exception as e:
            logger.error(f"Error creating dataset: {str(e)}")
            raise

    def create_examples(self, dataset_id: str, inputs: List[Dict[str, Any]], outputs: List[Dict[str, Any]]) -> None:
        try:
            logger.info(f"Creating examples for dataset: {dataset_id}")
            self.client.create_examples(
                inputs=inputs,
                outputs=outputs,
                dataset_id=dataset_id
            )
            logger.info("Examples created successfully")
        except Exception as e:
            logger.error(f"Error creating examples: {str(e)}")
            raise

    def read_dataset(self, dataset_id: str) -> Dict[str, Any]:
        try:
            logger.info(f"Reading dataset: {dataset_id}")
            return self.client.read_dataset(dataset_id=dataset_id)
        except Exception as e:
            logger.error(f"Error reading dataset: {str(e)}")
            raise

def main():
    try:
        creator = EvaluationDatasetCreator("home_assistant_recommendations")
        dataset_id = creator.create_dataset()
        
        inputs = [example['input'] for example in QA_EXAMPLES]
        outputs = [example['output'] for example in QA_EXAMPLES]
        
        creator.create_examples(dataset_id, inputs, outputs)
        dataset = creator.read_dataset(dataset_id)
        logger.info(f"Dataset created and populated successfully: {dataset}")
        return 0
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())